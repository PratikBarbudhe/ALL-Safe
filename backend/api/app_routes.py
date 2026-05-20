import logging

from fastapi import APIRouter, Depends, Request

from models.app_models import AppActionResponse, AppStatusResponse, PerformanceMetrics
from services.app_lifecycle_service import AppLifecycleService, app_lifecycle_service
from services.performance_monitor_service import performance_monitor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/app", tags=["Application"])


def get_lifecycle_service() -> AppLifecycleService:
    return app_lifecycle_service


@router.get(
    "/status",
    response_model=AppStatusResponse,
    summary="Application health and monitor diagnostics",
)
async def get_app_status(
    service: AppLifecycleService = Depends(get_lifecycle_service),
) -> AppStatusResponse:
    return await service.get_status_async()


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    summary="AllSafe process performance metrics",
)
async def get_app_performance() -> PerformanceMetrics:
    performance_monitor_service.record_api_poll()
    return performance_monitor_service.get_latest()


@router.post(
    "/restart-monitors",
    response_model=AppActionResponse,
    summary="Restart all background monitoring services",
)
async def restart_monitors(
    service: AppLifecycleService = Depends(get_lifecycle_service),
) -> AppActionResponse:
    return await service.restart_monitors_async()


@router.post(
    "/shutdown",
    response_model=AppActionResponse,
    summary="Graceful application shutdown",
)
async def shutdown_app(
    service: AppLifecycleService = Depends(get_lifecycle_service),
) -> AppActionResponse:
    return await service.shutdown_async()


@router.post(
    "/background-mode",
    response_model=AppActionResponse,
    summary="Set background monitoring mode flag",
)
async def set_background_mode(
    enabled: bool = True,
    service: AppLifecycleService = Depends(get_lifecycle_service),
) -> AppActionResponse:
    service.set_background_mode(enabled)
    return AppActionResponse(
        status="ok",
        message=f"Background mode {'enabled' if enabled else 'disabled'}",
    )


@router.post(
    "/window-visibility",
    response_model=AppActionResponse,
    summary="Track main window visibility for diagnostics",
)
async def set_window_visibility(
    visible: bool = True,
    service: AppLifecycleService = Depends(get_lifecycle_service),
) -> AppActionResponse:
    service.set_window_visible(visible)
    return AppActionResponse(
        status="ok",
        message=f"Window visible={visible}",
    )
