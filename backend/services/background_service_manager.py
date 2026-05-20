"""Watchdog and health recovery for background monitoring threads."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from models.app_models import DatabaseStatus, MonitorStatus

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WATCHDOG_INTERVAL_SECONDS = 30


class BackgroundServiceManager:
    _instance: BackgroundServiceManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_check = ""
        self._restart_counts: dict[str, int] = {}

    @classmethod
    def get_instance(cls) -> BackgroundServiceManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_watchdog(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watchdog_loop,
            name="allsafe-monitor-watchdog",
            daemon=True,
        )
        self._thread.start()
        logger.info("Monitor watchdog started")

    def stop_watchdog(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitor watchdog stopped")

    def _watchdog_loop(self) -> None:
        while not self._stop_event.wait(WATCHDOG_INTERVAL_SECONDS):
            try:
                self._last_check = datetime.now(timezone.utc).isoformat()
                unhealthy = [m for m in self.get_monitor_status() if not m.healthy]
                for monitor in unhealthy:
                    self._attempt_recovery(monitor.name)
            except Exception:
                logger.exception("Watchdog check failed")

    def _attempt_recovery(self, name: str) -> None:
        count = self._restart_counts.get(name, 0)
        if count >= 5:
            logger.error("Monitor %s exceeded recovery attempts", name)
            return
        self._restart_counts[name] = count + 1
        logger.warning("Recovering monitor: %s (attempt %d)", name, count + 1)
        try:
            if name == "threat_log":
                from services.threat_log_service import threat_log_service

                threat_log_service.stop_background_monitor()
                threat_log_service.start_background_monitor()
            elif name == "usb":
                from services.usb_service import usb_service

                usb_service.stop_background_monitor()
                usb_service.start_background_monitor()
            elif name == "ransomware":
                from services.ransomware_service import ransomware_service

                ransomware_service.bootstrap_if_enabled()
            elif name == "notification_health":
                from services.notification_health_monitor import (
                    notification_health_monitor,
                )

                notification_health_monitor.stop()
                notification_health_monitor.start()
        except Exception:
            logger.exception("Recovery failed for %s", name)

    def restart_all_monitors(self) -> list[str]:
        restarted: list[str] = []
        for name in ("threat_log", "usb", "ransomware", "notification_health"):
            self._restart_counts[name] = 0
            self._attempt_recovery(name)
            restarted.append(name)
        return restarted

    def get_monitor_status(self) -> list[MonitorStatus]:
        statuses: list[MonitorStatus] = []
        try:
            from services.threat_log_service import threat_log_service

            running = threat_log_service.monitoring_active
            statuses.append(
                MonitorStatus(
                    name="threat_log",
                    running=running,
                    healthy=running,
                    detail="Filesystem observer",
                )
            )
        except Exception as exc:
            statuses.append(
                MonitorStatus(
                    name="threat_log",
                    running=False,
                    healthy=False,
                    detail=str(exc),
                )
            )

        try:
            from services.usb_service import usb_service

            running = usb_service._thread is not None and usb_service._thread.is_alive()
            enabled = usb_service._monitoring_enabled
            healthy = (not enabled) or running
            statuses.append(
                MonitorStatus(
                    name="usb",
                    running=running and enabled,
                    healthy=healthy,
                    detail="USB poll thread",
                )
            )
        except Exception as exc:
            statuses.append(
                MonitorStatus(name="usb", running=False, healthy=False, detail=str(exc))
            )

        try:
            from services.ransomware_service import ransomware_service

            running = ransomware_service._monitor.is_running
            enabled = ransomware_service._settings.monitoring_enabled
            healthy = (not enabled) or running
            statuses.append(
                MonitorStatus(
                    name="ransomware",
                    running=running and enabled,
                    healthy=healthy,
                    detail="Heuristic monitor",
                )
            )
        except Exception as exc:
            statuses.append(
                MonitorStatus(
                    name="ransomware", running=False, healthy=False, detail=str(exc)
                )
            )

        try:
            from services.notification_health_monitor import notification_health_monitor

            running = (
                notification_health_monitor._thread is not None
                and notification_health_monitor._thread.is_alive()
            )
            statuses.append(
                MonitorStatus(
                    name="notification_health",
                    running=running,
                    healthy=running,
                    detail="Security health poll",
                )
            )
        except Exception as exc:
            statuses.append(
                MonitorStatus(
                    name="notification_health",
                    running=False,
                    healthy=False,
                    detail=str(exc),
                )
            )

        return statuses

    @staticmethod
    def check_databases() -> DatabaseStatus:
        def ok(path: Path) -> bool:
            if not path.exists():
                return False
            try:
                conn = sqlite3.connect(path, timeout=2)
                conn.execute("SELECT 1")
                conn.close()
                return True
            except Exception:
                return False

        return DatabaseStatus(
            threat_logs=ok(DATA_DIR / "threat_logs.db"),
            quarantine=ok(DATA_DIR / "quarantine.db"),
            ransomware=ok(DATA_DIR / "ransomware.db"),
            notifications=ok(DATA_DIR / "notifications.db"),
            ai_analysis=ok(DATA_DIR / "ai_analysis.db"),
            settings=ok(DATA_DIR / "settings.json") or (DATA_DIR / "settings.json.bak").exists(),
        )

    @property
    def last_watchdog_check(self) -> str:
        return self._last_check

    def count_active_threads(self) -> int:
        import threading as th

        return th.active_count()


background_service_manager = BackgroundServiceManager.get_instance()
