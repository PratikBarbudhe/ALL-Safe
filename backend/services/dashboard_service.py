import asyncio
import logging
from datetime import datetime, timezone

from models.dashboard_models import (
    DashboardOverviewResponse,
    NetworkActivity,
    ProtectionStatus,
)
from monitoring.process_monitor import ProcessMonitor
from monitoring.system_monitor import SystemMonitor
from services.threat_counters import threat_counter_store
from services.threat_log_service import threat_log_service
from utils.exceptions import DashboardServiceError
from services.windows_defender_service import windows_defender_service
from utils.windows_security import get_network_connection_count, get_usb_device_count

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregates live system, security, and threat data for the dashboard."""

    def __init__(
        self,
        system_monitor: SystemMonitor | None = None,
        process_monitor: ProcessMonitor | None = None,
    ) -> None:
        self._system_monitor = system_monitor or SystemMonitor()
        self._process_monitor = process_monitor or ProcessMonitor()

    async def get_overview(self) -> DashboardOverviewResponse:
        return await asyncio.to_thread(self._build_overview)

    def _build_overview(self) -> DashboardOverviewResponse:
        try:
            system_stats = self._system_monitor._collect_system_stats()
            process_list = self._process_monitor._collect_processes()

            win_sec = windows_defender_service.get_full_status()
            usb_count = get_usb_device_count()
            network_connections = get_network_connection_count()

            protection = ProtectionStatus(
                realtime_protection=win_sec.defender.realtime_protection,
                firewall=win_sec.firewall.enabled,
                windows_defender=(
                    win_sec.defender.antivirus_enabled
                    and win_sec.defender.service_running
                ),
            )

            threat_log_service.sync_dashboard_counters()
            try:
                from services.quarantine_service import quarantine_service

                threat_counter_store.quarantined_files = (
                    quarantine_service.get_stats().active_count
                )
            except Exception:
                pass
            counters = threat_counter_store
            active_threats = counters.active_threats

            security_score = self._calculate_security_score(
                cpu_usage=system_stats.cpu_usage,
                ram_usage=system_stats.ram_usage,
                disk_usage=system_stats.disk_usage,
                active_threats=active_threats,
                protection=protection,
            )
            security_score = windows_defender_service.calculate_security_score_adjustment(
                security_score, win_sec
            )

            system_health = self._resolve_system_health(
                security_score=security_score,
                active_threats=active_threats,
                protection=protection,
            )

            return DashboardOverviewResponse(
                system_health=system_health,
                cpu_usage=system_stats.cpu_usage,
                ram_usage=system_stats.ram_usage,
                disk_usage=system_stats.disk_usage,
                network_activity=NetworkActivity(
                    sent=system_stats.network_sent,
                    received=system_stats.network_received,
                ),
                running_processes=process_list.total_processes,
                uptime=system_stats.uptime,
                active_threats=active_threats,
                blocked_threats=counters.blocked_threats,
                quarantined_files=counters.quarantined_files,
                usb_devices_connected=usb_count,
                last_scan_time=(
                    win_sec.defender.last_quick_scan
                    or self._format_scan_time(counters.last_scan_time)
                ),
                protection_status=protection,
                security_score=security_score,
                network_connections=network_connections,
            )
        except Exception as exc:
            logger.exception("Failed to build dashboard overview")
            raise DashboardServiceError(
                "Unable to assemble dashboard overview"
            ) from exc

    @staticmethod
    def _calculate_security_score(
        cpu_usage: float,
        ram_usage: float,
        disk_usage: float,
        active_threats: int,
        protection: ProtectionStatus,
    ) -> int:
        score = 100.0
        score -= min(cpu_usage * 0.25, 25)
        score -= min(ram_usage * 0.2, 20)
        score -= min(disk_usage * 0.1, 10)
        score -= active_threats * 12

        if not protection.realtime_protection:
            score -= 15
        if not protection.firewall:
            score -= 15
        if not protection.windows_defender:
            score -= 10

        return max(0, min(100, int(round(score))))

    @staticmethod
    def _resolve_system_health(
        security_score: int,
        active_threats: int,
        protection: ProtectionStatus,
    ) -> str:
        if active_threats > 0 or security_score < 50:
            return "At Risk"
        if (
            security_score < 80
            or not protection.firewall
            or not protection.realtime_protection
        ):
            return "Warning"
        return "Secure"

    @staticmethod
    def _format_scan_time(scan_time: datetime) -> str:
        if scan_time.tzinfo is None:
            scan_time = scan_time.replace(tzinfo=timezone.utc)
        return scan_time.astimezone(timezone.utc).isoformat()
