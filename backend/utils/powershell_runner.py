import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_TIMEOUT = 20


def run_powershell(
    script: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[bool, str, str]:
    """
    Execute PowerShell and return (success, stdout, stderr).
    Never raises — callers handle failures gracefully.
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        return result.returncode == 0, stdout, stderr
    except subprocess.TimeoutExpired:
        logger.warning("PowerShell timed out after %ss", timeout)
        return False, "", "timeout"
    except OSError as exc:
        logger.warning("PowerShell execution failed: %s", exc)
        return False, "", str(exc)


def run_powershell_json(
    script: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any | None:
    """Run PowerShell expecting JSON on stdout."""
    ok, stdout, stderr = run_powershell(script, timeout=timeout)
    if not stdout:
        if stderr:
            logger.debug("PowerShell stderr: %s", stderr)
        return None
    try:
        data = json.loads(stdout)
        if isinstance(data, list) and len(data) == 1:
            return data[0]
        return data
    except json.JSONDecodeError:
        logger.warning("Failed to parse PowerShell JSON: %s", stdout[:200])
        return None


def run_powershell_bool(script: str, *, timeout: int = DEFAULT_TIMEOUT) -> bool | None:
    ok, stdout, _ = run_powershell(script, timeout=timeout)
    if not ok or not stdout:
        return None
    value = stdout.strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    return None
