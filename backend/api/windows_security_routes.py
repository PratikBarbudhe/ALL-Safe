import logging

from fastapi import APIRouter, Depends, Query

from models.windows_security_models import (
    DefenderStatusResponse,
    FirewallStatusResponse,
    SystemProtectionResponse,
    WindowsSecurityActionResponse,
    WindowsSecurityStatusResponse,
)
from services.windows_defender_service import (
    WindowsDefenderService,
    windows_defender_service,
)
from utils.exceptions import WindowsSecurityServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/windows-security", tags=["Windows Security"])


def get_windows_security_service() -> WindowsDefenderService:
    return windows_defender_service


def _http_error(exc: WindowsSecurityServiceError):
    from fastapi import HTTPException

    return HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/status",
    response_model=WindowsSecurityStatusResponse,
    summary="Full Windows security status",
)
async def get_windows_security_status(
    refresh: bool = Query(False),
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> WindowsSecurityStatusResponse:
    return await service.get_full_status_async(force_refresh=refresh)


@router.get(
    "/defender",
    response_model=DefenderStatusResponse,
    summary="Windows Defender status",
)
async def get_defender_status(
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> DefenderStatusResponse:
    return await service.get_defender_async()


@router.get(
    "/firewall",
    response_model=FirewallStatusResponse,
    summary="Windows Firewall status",
)
async def get_firewall_status(
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> FirewallStatusResponse:
    return await service.get_firewall_async()


@router.get(
    "/system-protection",
    response_model=SystemProtectionResponse,
    summary="System protection features (UAC, Secure Boot, TPM)",
)
async def get_system_protection_status(
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> SystemProtectionResponse:
    return await service.get_system_protection_async()


@router.post(
    "/quick-scan",
    response_model=WindowsSecurityActionResponse,
    summary="Start Windows Defender quick scan",
)
async def start_quick_scan(
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> WindowsSecurityActionResponse:
    try:
        return await service.trigger_quick_scan_async()
    except WindowsSecurityServiceError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/update-signatures",
    response_model=WindowsSecurityActionResponse,
    summary="Update Windows Defender signatures",
)
async def update_defender_signatures(
    service: WindowsDefenderService = Depends(get_windows_security_service),
) -> WindowsSecurityActionResponse:
    try:
        return await service.update_signatures_async()
    except WindowsSecurityServiceError as exc:
        raise _http_error(exc) from exc
