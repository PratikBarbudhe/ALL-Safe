"""Centralized application startup, background mode, and shutdown orchestration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from config import settings
from models.app_models import AppActionResponse, AppStatusResponse, PerformanceMetrics
from services.background_service_manager import background_service_manager
from services.performance_monitor_service import performance_monitor_service
from utils.log_cleanup import cleanup_old_logs, flush_log_handlers

logger = logging.getLogger(__name__)


class AppLifecycleService:
    _instance: AppLifecycleService | None = None

    def __init__(self) -> None:
        self._started_at = time.monotonic()
        self._warmup_complete = False
        self._background_mode = False
        self._window_visible = True
        self._shutting_down = False

    @classmethod
    def get_instance(cls) -> AppLifecycleService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def startup(self) -> None:
        """Ordered startup initialization."""
        from services.settings_service import settings_service
        from utils.logging_config import setup_logging

        app_settings = settings_service.settings
        log_level = (
            logging.DEBUG
            if app_settings.logging.verbose_logging or settings.debug
            else logging.INFO
        )
        setup_logging(log_level)
        logger.info("AllSafe lifecycle startup | v%s", settings.app_version)

        removed = cleanup_old_logs(app_settings.logging.log_retention_days)
        if removed:
            logger.info("Cleaned %d old log rotations", removed)

        try:
            from utils.windows_startup import enable_startup, is_startup_enabled

            if app_settings.system.auto_start_with_windows:
                if not is_startup_enabled():
                    enable_startup()
            else:
                from utils.windows_startup import disable_startup

                disable_startup()
        except Exception:
            logger.debug("Windows startup sync skipped", exc_info=True)

        try:
            settings_service.initialize_modules()
        except Exception as exc:
            logger.error("Module initialization failed: %s", exc)

        from services.notification_health_monitor import notification_health_monitor

        notification_health_monitor.start()
        background_service_manager.start_watchdog()
        performance_monitor_service.start()

        self._run_warmup()
        self._warmup_complete = True
        self._started_at = time.monotonic()
        logger.info("AllSafe lifecycle startup complete")

    def _run_warmup(self) -> None:
        """Lightweight warmup to prime caches without blocking startup."""
        try:
            from services.threat_log_service import threat_log_service

            threat_log_service.get_stats()
        except Exception:
            pass
        try:
            from services.settings_service import settings_service

            settings_service.get_settings()
        except Exception:
            pass

    def shutdown(self, *, keep_background: bool = False) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("AllSafe lifecycle shutdown (background=%s)", keep_background)

        if not keep_background and not self._background_mode:
            from services.notification_health_monitor import notification_health_monitor
            from services.ransomware_service import ransomware_service
            from services.threat_log_service import threat_log_service
            from services.usb_service import usb_service
            from services.ai_analysis_service import ai_analysis_service

            notification_health_monitor.stop()
            background_service_manager.stop_watchdog()
            performance_monitor_service.stop()
            ransomware_service.stop_monitoring()
            threat_log_service.stop_background_monitor()
            usb_service.stop_background_monitor()
            try:
                ai_analysis_service._stop_auto_analysis()
            except Exception:
                pass

        flush_log_handlers()
        logger.info("AllSafe shutdown complete")

    def set_background_mode(self, enabled: bool) -> None:
        self._background_mode = enabled
        logger.info("Background mode: %s", enabled)

    def set_window_visible(self, visible: bool) -> None:
        self._window_visible = visible

    def get_status(self) -> AppStatusResponse:
        monitors = background_service_manager.get_monitor_status()
        healthy_count = sum(1 for m in monitors if m.healthy)
        if healthy_count == len(monitors):
            status = "healthy"
        elif healthy_count > 0:
            status = "degraded"
        else:
            status = "critical"

        if self._background_mode and not self._window_visible:
            status_label = "background"
        else:
            status_label = status

        return AppStatusResponse(
            status=status_label,
            version=settings.app_version,
            uptime_seconds=int(time.monotonic() - self._started_at),
            background_mode=self._background_mode,
            window_visible=self._window_visible,
            monitors=monitors,
            databases=background_service_manager.check_databases(),
            active_threads=background_service_manager.count_active_threads(),
            warmup_complete=self._warmup_complete,
            last_watchdog_check=background_service_manager.last_watchdog_check,
        )

    def get_performance(self) -> PerformanceMetrics:
        return performance_monitor_service.get_latest()

    def restart_monitors(self) -> AppActionResponse:
        restarted = background_service_manager.restart_all_monitors()
        return AppActionResponse(
            status="ok",
            message=f"Restarted monitors: {', '.join(restarted)}",
        )

    def request_shutdown(self) -> AppActionResponse:
        self.shutdown(keep_background=False)
        return AppActionResponse(
            status="ok",
            message="Shutdown sequence completed",
        )

    async def get_status_async(self) -> AppStatusResponse:
        return await asyncio.to_thread(self.get_status)

    async def get_performance_async(self) -> PerformanceMetrics:
        return await asyncio.to_thread(self.get_performance)

    async def restart_monitors_async(self) -> AppActionResponse:
        return await asyncio.to_thread(self.restart_monitors)

    async def shutdown_async(self) -> AppActionResponse:
        return await asyncio.to_thread(self.request_shutdown)


app_lifecycle_service = AppLifecycleService.get_instance()
