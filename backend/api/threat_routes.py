import logging

from fastapi import APIRouter, Depends, Query

from models.threat_models import (
    ThreatClearResponse,
    ThreatLogListResponse,
    ThreatStatsResponse,
)
from services.threat_log_service import ThreatLogService, threat_log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/threats", tags=["Threats"])


def get_threat_service() -> ThreatLogService:
    return threat_log_service


@router.get(
    "/logs",
    response_model=ThreatLogListResponse,
    summary="Paginated threat and activity logs",
)
async def get_threat_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    severity: str | None = Query(None, description="Filter by severity: low, medium, high, critical"),
    category: str | None = Query(None, description="Filter by threat category"),
    search: str | None = Query(None, description="Search description, path, or category"),
    service: ThreatLogService = Depends(get_threat_service),
) -> ThreatLogListResponse:
    return await service.get_logs_async(
        page=page,
        page_size=page_size,
        severity=severity,
        category=category,
        search=search,
    )


@router.get(
    "/stats",
    response_model=ThreatStatsResponse,
    summary="Threat statistics for dashboard and threat logs",
)
async def get_threat_stats(
    service: ThreatLogService = Depends(get_threat_service),
) -> ThreatStatsResponse:
    return await service.get_stats_async()


@router.post(
    "/clear",
    response_model=ThreatClearResponse,
    summary="Clear all threat logs",
)
async def clear_threat_logs(
    service: ThreatLogService = Depends(get_threat_service),
) -> ThreatClearResponse:
    return await service.clear_logs_async()
