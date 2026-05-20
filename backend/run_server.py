"""Production entry point for PyInstaller sidecar builds."""

import uvicorn

from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
