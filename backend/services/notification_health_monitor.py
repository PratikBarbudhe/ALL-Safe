"""Background health monitoring that emits system protection notifications."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from models.notification_models import NotificationCategory, NotificationSeverity
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
CPU_SPIKE_THRESHOLD = 90.0
SUSPICIOUS_ACTIVITY_WINDOW_MINUTES = 5
SUSPICIOUS_ACTIVITY_THRESHOLD = 8

THREAT_DB = Path(__file__).resolve().parent.parent / "data" / "threat_logs.db"


class NotificationHealthMonitor:
    """Polls Windows security and system metrics; emits deduplicated alerts."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_defender_ok = True
        self._last_firewall_ok = True
        self._last_cpu_spike = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="allsafe-notification-health",
            daemon=True,
        )
        self._thread.start()
        logger.info("Notification health monitor started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Notification health monitor stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL_SECONDS):
            try:
                self._check_cycle()
            except Exception:
                logger.exception("Notification health check failed")

    def _check_cycle(self) -> None:
        self._check_windows_security()
        self._check_ransomware_activity()
        self._check_cpu_spike()
        self._check_repeated_suspicious_activity()

    def _check_windows_security(self) -> None:
        try:
            from services.windows_defender_service import windows_defender_service

            status = windows_defender_service.get_full_status()
        except Exception as exc:
            logger.debug("Windows security check skipped: %s", exc)
            return

        defender = status.defender
        firewall = status.firewall

        defender_ok = (
            defender.available
            and defender.realtime_protection
            and defender.antivirus_enabled
        )
        firewall_ok = firewall.available and firewall.enabled

        if not defender_ok and self._last_defender_ok:
            notification_service.emit(
                title="Windows Defender Disabled",
                message="Real-time protection or antivirus is turned off. Enable Defender immediately.",
                severity=NotificationSeverity.CRITICAL.value,
                category=NotificationCategory.WINDOWS_SECURITY.value,
                source_module="windows_security",
                action_required=True,
                dedupe_key="health:defender_disabled",
            )
        elif defender_ok and not self._last_defender_ok:
            notification_service.emit(
                title="Windows Defender Restored",
                message="Real-time protection is active again.",
                severity=NotificationSeverity.INFO.value,
                category=NotificationCategory.WINDOWS_SECURITY.value,
                source_module="windows_security",
                show_toast=False,
                dedupe_key="health:defender_restored",
            )
        self._last_defender_ok = defender_ok

        if not firewall_ok and self._last_firewall_ok:
            notification_service.emit(
                title="Windows Firewall Disabled",
                message="Host firewall is off. Network exposure risk is elevated.",
                severity=NotificationSeverity.HIGH.value,
                category=NotificationCategory.WINDOWS_SECURITY.value,
                source_module="windows_security",
                action_required=True,
                dedupe_key="health:firewall_disabled",
            )
        elif firewall_ok and not self._last_firewall_ok:
            notification_service.emit(
                title="Windows Firewall Restored",
                message="Firewall protection is enabled.",
                severity=NotificationSeverity.INFO.value,
                category=NotificationCategory.WINDOWS_SECURITY.value,
                source_module="windows_security",
                show_toast=False,
                dedupe_key="health:firewall_restored",
            )
        self._last_firewall_ok = firewall_ok

    def _check_ransomware_activity(self) -> None:
        try:
            from services.ransomware_service import ransomware_service

            if ransomware_service.has_recent_critical_activity():
                notification_service.emit(
                    title="Ransomware Activity Detected",
                    message="Critical ransomware heuristics triggered in the last monitoring cycle.",
                    severity=NotificationSeverity.CRITICAL.value,
                    category=NotificationCategory.RANSOMWARE.value,
                    source_module="ransomware",
                    action_required=True,
                    dedupe_key="health:ransomware_critical",
                )
        except Exception as exc:
            logger.debug("Ransomware health check skipped: %s", exc)

    def _check_cpu_spike(self) -> None:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.5)
        except Exception:
            return

        if cpu >= CPU_SPIKE_THRESHOLD and not self._last_cpu_spike:
            notification_service.emit(
                title="High CPU Usage",
                message=f"System CPU at {cpu:.0f}%. Investigate suspicious processes.",
                severity=NotificationSeverity.WARNING.value,
                category=NotificationCategory.SYSTEM_HEALTH.value,
                source_module="system_health",
                metadata={"cpu_percent": cpu},
                dedupe_key="health:cpu_spike",
            )
            self._last_cpu_spike = True
        elif cpu < CPU_SPIKE_THRESHOLD - 10:
            self._last_cpu_spike = False

    def _check_repeated_suspicious_activity(self) -> None:
        if not THREAT_DB.exists():
            return
        cutoff = (
            datetime.now(timezone.utc) - timedelta(minutes=SUSPICIOUS_ACTIVITY_WINDOW_MINUTES)
        ).isoformat()
        try:
            conn = sqlite3.connect(THREAT_DB, check_same_thread=False)
            try:
                count = conn.execute(
                    """
                    SELECT COUNT(*) FROM threat_logs
                    WHERE timestamp >= ?
                    AND severity IN ('high', 'critical', 'medium')
                    """,
                    (cutoff,),
                ).fetchone()[0]
            finally:
                conn.close()
        except Exception:
            return

        if count >= SUSPICIOUS_ACTIVITY_THRESHOLD:
            notification_service.emit(
                title="Repeated Suspicious Activity",
                message=f"{count} medium+ security events in the last {SUSPICIOUS_ACTIVITY_WINDOW_MINUTES} minutes.",
                severity=NotificationSeverity.HIGH.value,
                category=NotificationCategory.THREAT_DETECTION.value,
                source_module="threat_monitor",
                action_required=True,
                dedupe_key="health:suspicious_burst",
            )


notification_health_monitor = NotificationHealthMonitor()
