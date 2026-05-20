from fastapi import APIRouter

from api.dashboard_routes import router as dashboard_router
from api.process_routes import router as process_router
from api.system_routes import router as system_router
from api.quarantine_routes import router as quarantine_router
from api.ransomware_routes import router as ransomware_router
from api.windows_security_routes import router as windows_security_router
from api.threat_routes import router as threat_router
from api.usb_routes import router as usb_router
from api.notification_routes import router as notification_router
from api.ai_analysis_routes import router as ai_analysis_router
from api.settings_routes import router as settings_router
from api.app_routes import router as app_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(process_router)
api_router.include_router(dashboard_router)
api_router.include_router(usb_router)
api_router.include_router(threat_router)
api_router.include_router(quarantine_router)
api_router.include_router(ransomware_router)
api_router.include_router(windows_security_router)
api_router.include_router(notification_router)
api_router.include_router(ai_analysis_router)
api_router.include_router(settings_router)
api_router.include_router(app_router)

__all__ = ["api_router"]
