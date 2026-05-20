import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import api_router
from config import settings
from models.system_models import SystemStatsResponse
from monitoring.system_monitor import SystemMonitor
from services.app_lifecycle_service import app_lifecycle_service
from services.performance_monitor_service import performance_monitor_service
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
    NotificationServiceError,
    AiAnalysisServiceError,
    SettingsServiceError,
    WindowsSecurityServiceError,
    UsbMonitorError,
)
logger = logging.getLogger(__name__)


def get_system_monitor() -> SystemMonitor:
    return SystemMonitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_lifecycle_service.startup()
    yield
    app_lifecycle_service.shutdown(keep_background=False)


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


@app.middleware("http")
async def performance_tracking_middleware(request: Request, call_next):
    if request.url.path.startswith(("/api", "/dashboard", "/threats", "/app")) or (
        request.url.path.count("/") <= 2 and request.method == "GET"
    ):
        performance_monitor_service.record_api_poll()
    return await call_next(request)


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


@app.exception_handler(SettingsServiceError)
async def settings_service_error_handler(
    _request: Request, exc: SettingsServiceError
) -> JSONResponse:
    logger.error("Settings service error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error": "settings_error"},
    )


@app.exception_handler(AiAnalysisServiceError)
async def ai_analysis_service_error_handler(
    _request: Request, exc: AiAnalysisServiceError
) -> JSONResponse:
    logger.error("AI analysis service error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "ai_analysis_unavailable"},
    )


@app.exception_handler(NotificationServiceError)
async def notification_service_error_handler(
    _request: Request, exc: NotificationServiceError
) -> JSONResponse:
    logger.error("Notification service error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "error": "notification_unavailable"},
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
