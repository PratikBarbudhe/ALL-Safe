"""AllSafe process performance and anomaly monitoring."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psutil

from models.app_models import PerformanceMetrics

logger = logging.getLogger(__name__)

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "performance.log"
LOG_MAX_BYTES = 3 * 1024 * 1024
LOG_BACKUP_COUNT = 3

CPU_WARN_THRESHOLD = 35.0
MEMORY_WARN_MB = 512.0
POLL_BURST_THRESHOLD = 120


class PerformanceMonitorService:
    _instance: PerformanceMonitorService | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._process = psutil.Process()
        self._poll_counts: deque[float] = deque(maxlen=60)
        self._throttle_active = False
        self._last_metrics: PerformanceMetrics | None = None
        self._perf_logger = self._configure_logger()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @classmethod
    def get_instance(cls) -> PerformanceMonitorService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        perf_logger = logging.getLogger("allsafe.performance")
        if not perf_logger.handlers:
            handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            perf_logger.addHandler(handler)
            perf_logger.setLevel(logging.INFO)
            perf_logger.propagate = False
        return perf_logger

    def start(self, interval_seconds: float = 30.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            args=(interval_seconds,),
            name="allsafe-performance-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self, interval: float) -> None:
        while not self._stop_event.wait(interval):
            try:
                metrics = self.collect_metrics()
                if metrics.anomalies:
                    self._perf_logger.warning(
                        "Performance anomaly | cpu=%.1f%% mem=%.0fMB | %s",
                        metrics.process_cpu_percent,
                        metrics.process_memory_mb,
                        "; ".join(metrics.anomalies),
                    )
            except Exception:
                logger.exception("Performance sample failed")

    def record_api_poll(self) -> None:
        """Track API poll frequency for runaway detection."""
        now = time.monotonic()
        with self._state_lock:
            self._poll_counts.append(now)
            while self._poll_counts and now - self._poll_counts[0] > 60:
                self._poll_counts.popleft()
            burst = len(self._poll_counts)
            self._throttle_active = burst >= POLL_BURST_THRESHOLD

    def should_throttle_expensive_work(self) -> bool:
        with self._state_lock:
            return self._throttle_active

    def collect_metrics(self) -> PerformanceMetrics:
        try:
            cpu = self._process.cpu_percent(interval=0.1)
            mem = self._process.memory_info().rss / (1024 * 1024)
            threads = self._process.num_threads()
        except (psutil.Error, OSError):
            cpu, mem, threads = 0.0, 0.0, 0

        anomalies: list[str] = []
        if cpu >= CPU_WARN_THRESHOLD:
            anomalies.append(f"High AllSafe CPU usage ({cpu:.1f}%)")
        if mem >= MEMORY_WARN_MB:
            anomalies.append(f"High AllSafe memory usage ({mem:.0f} MB)")
        with self._state_lock:
            if self._throttle_active:
                anomalies.append("API polling burst detected — throttling active")

        status = "healthy"
        if anomalies:
            status = "degraded" if cpu < CPU_WARN_THRESHOLD * 1.5 else "critical"

        metrics = PerformanceMetrics(
            process_cpu_percent=round(cpu, 2),
            process_memory_mb=round(mem, 1),
            process_threads=threads,
            status=status,
            anomalies=anomalies,
            poll_throttle_active=self._throttle_active,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._state_lock:
            self._last_metrics = metrics
        return metrics

    def get_latest(self) -> PerformanceMetrics:
        with self._state_lock:
            if self._last_metrics:
                return self._last_metrics
        return self.collect_metrics()


performance_monitor_service = PerformanceMonitorService.get_instance()
