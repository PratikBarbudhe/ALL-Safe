import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from models.usb_models import UsbDeviceListResponse, UsbHistoryResponse
from services.usb_service import UsbService, usb_service
from utils.exceptions import UsbMonitorError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usb", tags=["USB"])


def get_usb_service() -> UsbService:
    return usb_service


@router.get(
    "/devices",
    response_model=UsbDeviceListResponse,
    summary="List connected USB devices",
)
async def list_usb_devices(
    service: UsbService = Depends(get_usb_service),
) -> UsbDeviceListResponse:
    return await service.get_devices()


@router.get(
    "/history",
    response_model=UsbHistoryResponse,
    summary="USB connect and disconnect history",
)
async def get_usb_history(
    service: UsbService = Depends(get_usb_service),
) -> UsbHistoryResponse:
    return await service.get_history()


@router.post("/scan", summary="Force immediate USB rescan")
async def scan_usb_devices(
    service: UsbService = Depends(get_usb_service),
) -> dict[str, str]:
    try:
        await asyncio.to_thread(service.force_rescan)
    except UsbMonitorError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "message": "USB scan completed"}
