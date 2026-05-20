"""Legacy helpers — prefer services.windows_defender_service for full integration."""

import logging

logger = logging.getLogger(__name__)


def get_defender_status() -> dict[str, bool]:
    from services.windows_defender_service import windows_defender_service

    return windows_defender_service.get_protection_summary()


def get_firewall_enabled() -> bool:
    from services.windows_defender_service import windows_defender_service

    return windows_defender_service.get_protection_summary()["firewall"]


def get_usb_device_count() -> int:
    script = (
        "@(Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -eq 'USB' -and $_.Status -eq 'OK' }).Count"
    )
    output = _run_powershell(script)
    if not output:
        return 0
    try:
        return max(0, int(output))
    except ValueError:
        return 0


def get_network_connection_count() -> int:
    script = (
        "@(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue).Count"
    )
    output = _run_powershell(script)
    if not output:
        return 0
    try:
        return max(0, int(output))
    except ValueError:
        return 0
