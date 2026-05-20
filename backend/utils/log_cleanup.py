"""Production log retention and safe cleanup."""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = BACKEND_ROOT / "logs"


def cleanup_old_logs(retention_days: int = 30) -> int:
    """Remove rotated log backups older than retention_days."""
    if retention_days < 1:
        return 0
    if not LOGS_DIR.exists():
        return 0

    cutoff = time.time() - (retention_days * 86400)
    removed = 0
    for path in LOGS_DIR.glob("*.log.*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError as exc:
            logger.debug("Could not remove %s: %s", path, exc)
    return removed


def flush_log_handlers() -> None:
    """Flush all logging handlers on graceful shutdown."""
    for handler in logging.root.handlers:
        try:
            handler.flush()
        except Exception:
            pass
    for name in logging.Logger.manager.loggerDict:
        log = logging.getLogger(name) if isinstance(name, str) else None
        if not isinstance(log, logging.Logger):
            continue
        for handler in log.handlers:
            try:
                handler.flush()
            except Exception:
                pass
