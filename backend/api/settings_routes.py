import logging

from fastapi import APIRouter, Depends, HTTPException

from models.settings_models import (
    SettingsActionResponse,
    SettingsExportResponse,
    SettingsGroupResponse,
    SettingsImportRequest,
    SettingsResponse,
    SettingsUpdateRequest,
)
from services.settings_service import SettingsService, settings_service
from utils.exceptions import SettingsServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_settings_service() -> SettingsService:
    return settings_service


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get all application settings",
)
async def get_settings(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return await service.get_settings_async()


@router.get(
    "/{group}",
    response_model=SettingsGroupResponse,
    summary="Get a single settings group",
)
async def get_settings_group(
    group: str,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsGroupResponse:
    try:
        return await service.get_group_async(group)
    except SettingsServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/update",
    response_model=SettingsResponse,
    summary="Update settings (partial merge, auto-save)",
)
async def update_settings(
    request: SettingsUpdateRequest,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return await service.update_async(request)
    except SettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/reset",
    response_model=SettingsActionResponse,
    summary="Reset all settings to defaults",
)
async def reset_settings(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsActionResponse:
    return await service.reset_async()


@router.post(
    "/export",
    response_model=SettingsExportResponse,
    summary="Export configuration for backup",
)
async def export_settings(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsExportResponse:
    return await service.export_async()


@router.post(
    "/import",
    response_model=SettingsActionResponse,
    summary="Import configuration from JSON",
)
async def import_settings(
    request: SettingsImportRequest,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsActionResponse:
    try:
        return await service.import_async(request.settings)
    except SettingsServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
