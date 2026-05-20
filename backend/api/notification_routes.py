import logging

from fastapi import APIRouter, Depends, Query

from models.notification_models import (
    ClearNotificationsResponse,
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from services.notification_service import NotificationService, notification_service
from utils.exceptions import NotificationServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service() -> NotificationService:
    return notification_service


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List security notifications (newest first)",
)
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return await service.list_notifications_async(
        limit=limit,
        unread_only=unread_only,
        category=category,
        severity=severity,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Unread notification count for header badge",
)
async def get_unread_count(
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    return await service.get_unread_count_async()


@router.post(
    "/mark-read/{notification_id}",
    response_model=MarkReadResponse,
    summary="Mark a single notification as read",
)
async def mark_notification_read(
    notification_id: int,
    service: NotificationService = Depends(get_notification_service),
) -> MarkReadResponse:
    try:
        return await service.mark_read_async(notification_id)
    except NotificationServiceError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/mark-all-read",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    service: NotificationService = Depends(get_notification_service),
) -> MarkAllReadResponse:
    return await service.mark_all_read_async()


@router.delete(
    "/clear",
    response_model=ClearNotificationsResponse,
    summary="Clear all notifications",
)
async def clear_notifications(
    service: NotificationService = Depends(get_notification_service),
) -> ClearNotificationsResponse:
    return await service.clear_all_async()
