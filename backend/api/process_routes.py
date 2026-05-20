import logging

from fastapi import APIRouter, Depends

from models.process_models import ProcessListResponse
from monitoring.process_monitor import ProcessMonitor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Processes"])


def get_process_monitor() -> ProcessMonitor:
    return ProcessMonitor()


@router.get(
    "/processes",
    response_model=ProcessListResponse,
    summary="Get top running processes",
    response_description="Top processes sorted by CPU usage (descending)",
)
async def get_processes(
    monitor: ProcessMonitor = Depends(get_process_monitor),
) -> ProcessListResponse:
    return await monitor.get_processes()
