"""Windows startup integration via Run registry key."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AllSafeSecurity"


def _resolve_executable() -> str | None:
    """Best-effort path to the AllSafe desktop executable."""
    import os

    env = os.getenv("ALLSAFE_EXE_PATH", "").strip()
    if env and Path(env).exists():
        return env

    candidates = [
        Path(sys.executable),
        Path.cwd() / "AllSafe.exe",
    ]
    for path in candidates:
        if path.exists() and path.suffix.lower() == ".exe":
            return str(path.resolve())
    return None


def is_startup_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def enable_startup(exe_path: str | None = None) -> bool:
    if sys.platform != "win32":
        logger.warning("Windows startup is only supported on Windows")
        return False
    target = exe_path or _resolve_executable()
    if not target:
        logger.warning("Could not resolve AllSafe executable for startup entry")
        return False
    command = f'"{target}" --background'
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command)
        logger.info("Windows startup entry enabled: %s", command)
        return True
    except OSError as exc:
        logger.error("Failed to enable Windows startup: %s", exc)
        return False


def disable_startup() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except OSError:
                pass
        logger.info("Windows startup entry removed")
        return True
    except OSError as exc:
        logger.error("Failed to disable Windows startup: %s", exc)
        return False
