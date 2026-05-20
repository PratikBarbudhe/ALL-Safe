import logging

from fastapi import APIRouter, Depends

from models.dashboard_models import DashboardOverviewResponse
from services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service() -> DashboardService:
    return DashboardService()


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="Get live dashboard overview",
)
async def get_dashboard_overview(
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardOverviewResponse:
    return await service.get_overview()
