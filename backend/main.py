import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import api_router
from config import settings
from models.system_models import SystemStatsResponse
from monitoring.system_monitor import SystemMonitor
from services.ransomware_service import ransomware_service
from services.threat_log_service import threat_log_service
from services.usb_service import usb_service
from utils.exceptions import (
    AllSafeError,
    DashboardServiceError,
    FileMonitorError,
    ProcessMonitorError,
    SystemMonitorError,
    QuarantineServiceError,
    RansomwareMonitorError,
    RansomwareServiceError,
    ThreatLogServiceError,
    WindowsSecurityServiceError,
    UsbMonitorError,
)
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def get_system_monitor() -> SystemMonitor:
    return SystemMonitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(logging.DEBUG if settings.debug else logging.INFO)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    usb_service.start_background_monitor()
    try:
        threat_log_service.start_background_monitor()
    except (FileMonitorError, ThreatLogServiceError) as exc:
        logger.error("Threat monitoring failed to start: %s", exc)
    try:
        ransomware_service.bootstrap_if_enabled()
    except (RansomwareMonitorError, RansomwareServiceError) as exc:
        logger.error("Ransomware protection failed to start: %s", exc)
    yield
    ransomware_service.stop_monitoring()
    threat_log_service.stop_background_monitor()
    usb_service.stop_background_monitor()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local AllSafe cybersecurity backend for Windows desktop",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get(
    "/system-stats",
    response_model=SystemStatsResponse,
    tags=["System"],
    summary="Get live system statistics (root path)",
)
async def get_system_stats_root(
    monitor: SystemMonitor = Depends(get_system_monitor),
) -> SystemStatsResponse:
    """Canonical endpoint path required by the AllSafe desktop integration."""
    return await monitor.get_system_stats()


@app.exception_handler(SystemMonitorError)
async def system_monitor_error_handler(
    _request: Request, exc: SystemMonitorError
) -> JSONResponse:
    logger.error("System monitor error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "system_monitor_unavailable"},
    )


@app.exception_handler(ProcessMonitorError)
async def process_monitor_error_handler(
    _request: Request, exc: ProcessMonitorError
) -> JSONResponse:
    logger.error("Process monitor error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "process_monitor_unavailable"},
    )


@app.exception_handler(DashboardServiceError)
async def dashboard_service_error_handler(
    _request: Request, exc: DashboardServiceError
) -> JSONResponse:
    logger.error("Dashboard service error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "dashboard_unavailable"},
    )


@app.exception_handler(UsbMonitorError)
async def usb_monitor_error_handler(
    _request: Request, exc: UsbMonitorError
) -> JSONResponse:
    logger.error("USB monitor error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "usb_monitor_unavailable"},
    )


@app.exception_handler(FileMonitorError)
async def file_monitor_error_handler(
    _request: Request, exc: FileMonitorError
) -> JSONResponse:
    logger.error("File monitor error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "file_monitor_unavailable"},
    )


@app.exception_handler(ThreatLogServiceError)
async def threat_log_service_error_handler(
    _request: Request, exc: ThreatLogServiceError
) -> JSONResponse:
    logger.error("Threat log service error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "threat_log_unavailable"},
    )


@app.exception_handler(QuarantineServiceError)
async def quarantine_service_error_handler(
    _request: Request, exc: QuarantineServiceError
) -> JSONResponse:
    logger.error("Quarantine service error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error": "quarantine_error"},
    )


@app.exception_handler(RansomwareMonitorError)
async def ransomware_monitor_error_handler(
    _request: Request, exc: RansomwareMonitorError
) -> JSONResponse:
    logger.error("Ransomware monitor error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "ransomware_monitor_unavailable"},
    )


@app.exception_handler(RansomwareServiceError)
async def ransomware_service_error_handler(
    _request: Request, exc: RansomwareServiceError
) -> JSONResponse:
    logger.error("Ransomware service error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error": "ransomware_error"},
    )


@app.exception_handler(WindowsSecurityServiceError)
async def windows_security_service_error_handler(
    _request: Request, exc: WindowsSecurityServiceError
) -> JSONResponse:
    logger.error("Windows security service error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error": "windows_security_error"},
    )


@app.exception_handler(AllSafeError)
async def allsafe_error_handler(_request: Request, exc: AllSafeError) -> JSONResponse:
    logger.error("AllSafe error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": "internal_error"},
    )


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
