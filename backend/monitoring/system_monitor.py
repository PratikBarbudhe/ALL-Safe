import asyncio
import logging
import os
import time
from datetime import timedelta

import psutil

from config import settings
from models.system_models import SystemStatsResponse
from utils.exceptions import SystemMonitorError

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Collects real system metrics from the host OS via psutil."""

    def __init__(self, cpu_sample_interval: float | None = None) -> None:
        self._cpu_sample_interval = (
            cpu_sample_interval
            if cpu_sample_interval is not None
            else settings.cpu_sample_interval
        )

    async def get_system_stats(self) -> SystemStatsResponse:
        """Async entry point; runs blocking psutil work in a thread pool."""
        return await asyncio.to_thread(self._collect_system_stats)

    def _collect_system_stats(self) -> SystemStatsResponse:
        try:
            cpu_usage = psutil.cpu_percent(interval=self._cpu_sample_interval)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(self._system_drive())
            network = psutil.net_io_counters()
            boot_time = psutil.boot_time()
        except (OSError, PermissionError) as exc:
            logger.exception("Failed to collect system metrics")
            raise SystemMonitorError(
                "Unable to read system metrics from the host"
            ) from exc

        if network is None:
            raise SystemMonitorError("Network I/O counters are unavailable")

        uptime_seconds = max(0, int(time.time() - boot_time))

        return SystemStatsResponse(
            cpu_usage=round(float(cpu_usage), 2),
            ram_usage=round(float(memory.percent), 2),
            disk_usage=round(float(disk.percent), 2),
            network_sent=int(network.bytes_sent),
            network_received=int(network.bytes_recv),
            running_processes=len(psutil.pids()),
            uptime=self._format_uptime(uptime_seconds),
        )

    @staticmethod
    def _system_drive() -> str:
        """Return the Windows system drive path (e.g. C:\\)."""
        drive = os.environ.get("SystemDrive", "C:")
        if not drive.endswith("\\"):
            drive = f"{drive}\\"
        return drive

    @staticmethod
    def _format_uptime(total_seconds: int) -> str:
        delta = timedelta(seconds=total_seconds)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts: list[str] = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
        return " ".join(parts)
