import logging

from fastapi import APIRouter, Depends

from models.system_models import SystemStatsResponse
from monitoring.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


def get_system_monitor() -> SystemMonitor:
    return SystemMonitor()


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Get live system statistics",
    response_description="Real-time CPU, memory, disk, network, and process metrics",
)
async def get_system_stats(
    monitor: SystemMonitor = Depends(get_system_monitor),
) -> SystemStatsResponse:
    """Same metrics as GET /system-stats, namespaced under /system."""
    return await monitor.get_system_stats()
