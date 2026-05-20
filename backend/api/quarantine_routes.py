import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from models.quarantine_models import (
    QuarantineActionResponse,
    QuarantineAddRequest,
    QuarantineClearResponse,
    QuarantineItem,
    QuarantineItemListResponse,
    QuarantineStatsResponse,
)
from services.quarantine_service import QuarantineService, quarantine_service
from utils.exceptions import QuarantineServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quarantine", tags=["Quarantine"])


def get_quarantine_service() -> QuarantineService:
    return quarantine_service


def _handle_quarantine_error(exc: QuarantineServiceError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/add",
    response_model=QuarantineActionResponse,
    summary="Quarantine a file by absolute path",
)
async def add_to_quarantine(
    request: QuarantineAddRequest,
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineActionResponse:
    try:
        return await service.add_file_async(request)
    except QuarantineServiceError as exc:
        raise _handle_quarantine_error(exc) from exc


@router.post(
    "/upload",
    response_model=QuarantineActionResponse,
    summary="Upload and quarantine a file (manual testing)",
)
async def upload_to_quarantine(
    file: UploadFile = File(...),
    reason: str = Query("Manual upload quarantine test"),
    severity: str = Query("medium"),
    category: str = Query("File Activity"),
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineActionResponse:
    suffix = Path(file.filename or "upload.bin").suffix
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        return await service.add_uploaded_file(
            upload_path=tmp_path,
            original_filename=file.filename or "upload.bin",
            reason=reason,
            severity=severity,
            category=category,
        )
    except QuarantineServiceError as exc:
        raise _handle_quarantine_error(exc) from exc


@router.get(
    "/items",
    response_model=QuarantineItemListResponse,
    summary="List quarantined files",
)
async def list_quarantine_items(
    status: str | None = Query("quarantined", description="quarantined | restored | deleted | all"),
    severity: str | None = Query(None),
    search: str | None = Query(None),
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineItemListResponse:
    return await service.list_items_async(
        status=status,
        severity=severity,
        search=search,
    )


@router.get(
    "/stats",
    response_model=QuarantineStatsResponse,
    summary="Quarantine statistics",
)
async def get_quarantine_stats(
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineStatsResponse:
    return await service.get_stats_async()


@router.get(
    "/items/{item_id}",
    response_model=QuarantineItem,
    summary="Get quarantine item details",
)
async def get_quarantine_item(
    item_id: int,
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineItem:
    try:
        return await service.get_item_async(item_id)
    except QuarantineServiceError as exc:
        raise _handle_quarantine_error(exc) from exc


@router.post(
    "/restore/{item_id}",
    response_model=QuarantineActionResponse,
    summary="Restore quarantined file to original location",
)
async def restore_quarantine_item(
    item_id: int,
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineActionResponse:
    try:
        return await service.restore_item_async(item_id)
    except QuarantineServiceError as exc:
        raise _handle_quarantine_error(exc) from exc


@router.delete(
    "/delete/{item_id}",
    response_model=QuarantineActionResponse,
    summary="Permanently delete a quarantined file",
)
async def delete_quarantine_item(
    item_id: int,
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineActionResponse:
    try:
        return await service.delete_item_async(item_id)
    except QuarantineServiceError as exc:
        raise _handle_quarantine_error(exc) from exc


@router.post(
    "/clear",
    response_model=QuarantineClearResponse,
    summary="Permanently delete all active quarantined files",
)
async def clear_quarantine(
    service: QuarantineService = Depends(get_quarantine_service),
) -> QuarantineClearResponse:
    return await service.clear_all_async()
