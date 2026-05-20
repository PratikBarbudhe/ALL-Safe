import logging

from fastapi import APIRouter, Depends, Query

from models.ransomware_models import (
    RansomwareActionResponse,
    RansomwareEventListResponse,
    RansomwareSettings,
    RansomwareSettingsUpdate,
    RansomwareStatusResponse,
)
from services.ransomware_service import RansomwareService, ransomware_service
from utils.exceptions import RansomwareServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ransomware", tags=["Ransomware"])


def get_ransomware_service() -> RansomwareService:
    return ransomware_service


@router.get(
    "/status",
    response_model=RansomwareStatusResponse,
    summary="Ransomware protection status and statistics",
)
async def get_ransomware_status(
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareStatusResponse:
    return await service.get_status_async()


@router.get(
    "/events",
    response_model=RansomwareEventListResponse,
    summary="Recent ransomware detection events",
)
async def get_ransomware_events(
    limit: int = Query(50, ge=1, le=200),
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareEventListResponse:
    return await service.get_events_async(limit=limit)


@router.post(
    "/start",
    response_model=RansomwareActionResponse,
    summary="Start ransomware monitoring",
)
async def start_ransomware_protection(
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareActionResponse:
    try:
        return await service.start_monitoring_async()
    except RansomwareServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/stop",
    response_model=RansomwareActionResponse,
    summary="Stop ransomware monitoring",
)
async def stop_ransomware_protection(
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareActionResponse:
    return await service.stop_monitoring_async()


@router.post(
    "/settings",
    response_model=RansomwareSettings,
    summary="Update ransomware protection settings",
)
async def update_ransomware_settings(
    update: RansomwareSettingsUpdate,
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareSettings:
    try:
        return await service.apply_settings_async(update)
    except RansomwareServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/settings",
    response_model=RansomwareSettings,
    summary="Get current ransomware settings",
)
async def get_ransomware_settings(
    service: RansomwareService = Depends(get_ransomware_service),
) -> RansomwareSettings:
    return service.get_settings()


def _http_error(exc: RansomwareServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=400, detail=str(exc))
