import asyncio
import logging
import time

import psutil

from config import settings
from models.process_models import ProcessInfo, ProcessListResponse
from utils.exceptions import ProcessMonitorError

logger = logging.getLogger(__name__)


class ProcessMonitor:
    """Collects real running process metrics via psutil (Windows 10/11)."""

    def __init__(
        self,
        limit: int | None = None,
        cpu_sample_interval: float | None = None,
    ) -> None:
        self._limit = limit if limit is not None else settings.process_limit
        self._cpu_sample_interval = (
            cpu_sample_interval
            if cpu_sample_interval is not None
            else settings.cpu_sample_interval
        )

    async def get_processes(self) -> ProcessListResponse:
        return await asyncio.to_thread(self._collect_processes)

    def _collect_processes(self) -> ProcessListResponse:
        try:
            total_memory = psutil.virtual_memory().total
            total_processes = len(psutil.pids())

            processes = list(psutil.process_iter())
            self._prime_cpu_counters(processes)
            if self._cpu_sample_interval > 0:
                time.sleep(self._cpu_sample_interval)

            collected: list[ProcessInfo] = []
            for proc in psutil.process_iter():
                info = self._read_process(proc)
                if info is not None:
                    collected.append(info)

            collected.sort(key=lambda item: item.cpu_percent, reverse=True)
            top_processes = collected[: self._limit]

            logger.debug(
                "Collected %d processes, returning top %d",
                len(collected),
                len(top_processes),
            )

            return ProcessListResponse(
                processes=top_processes,
                total_processes=total_processes,
                system_memory_total_bytes=int(total_memory),
            )
        except (OSError, PermissionError) as exc:
            logger.exception("Failed to collect process list")
            raise ProcessMonitorError(
                "Unable to read running processes from the host"
            ) from exc

    def _prime_cpu_counters(self, processes: list[psutil.Process]) -> None:
        for proc in processes:
            try:
                proc.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def _read_process(self, proc: psutil.Process) -> ProcessInfo | None:
        try:
            with proc.oneshot():
                cpu_percent = proc.cpu_percent(None)
                memory_percent = proc.memory_percent()
                status = proc.status()
                create_time = proc.create_time()
                process_name = proc.name()
                username = proc.username()
                executable_path = proc.exe() or ""
        except psutil.NoSuchProcess:
            return None
        except psutil.AccessDenied:
            try:
                cpu_percent = proc.cpu_percent(None)
                memory_percent = proc.memory_percent()
                status = proc.status()
                create_time = proc.create_time()
                process_name = proc.name()
                username = "N/A"
                executable_path = ""
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return None
        except psutil.ZombieProcess:
            return None

        normalized_cpu = min(max(float(cpu_percent or 0.0), 0.0), 100.0)

        return ProcessInfo(
            pid=int(proc.pid),
            process_name=str(process_name),
            cpu_percent=round(normalized_cpu, 2),
            memory_percent=round(max(float(memory_percent or 0.0), 0.0), 2),
            status=str(status),
            username=str(username),
            executable_path=str(executable_path),
            create_time=float(create_time),
        )
