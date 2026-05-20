import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

if sys.platform != "win32":
    logger.warning("USB monitoring is only supported on Windows")


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text if text.lower() not in {"none", "n/a", "unknown"} else ""


def _format_capacity(size_bytes: int | None) -> int:
    try:
        return max(0, int(size_bytes or 0))
    except (TypeError, ValueError):
        return 0


class UsbMonitor:
    """Enumerates USB storage devices via WMI (Windows Management Instrumentation)."""

    def enumerate_devices(self) -> list[dict[str, Any]]:
        if sys.platform != "win32":
            return []

        try:
            import pythoncom
            import wmi
        except ImportError as exc:
            logger.error("WMI dependencies missing: %s", exc)
            raise

        pythoncom.CoInitialize()
        try:
            client = wmi.WMI()
            devices: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for disk in client.Win32_DiskDrive():
                interface = _normalize(getattr(disk, "InterfaceType", ""))
                pnp_id = _normalize(getattr(disk, "PNPDeviceID", ""))
                if interface != "USB" and "USB" not in pnp_id.upper():
                    continue

                device_id = pnp_id or f"disk-{getattr(disk, 'Index', len(devices))}"
                if device_id in seen_ids:
                    continue
                seen_ids.add(device_id)

                drive_letters = self._resolve_drive_letters(client, disk)
                capacity = _format_capacity(getattr(disk, "Size", 0))

                for letter in drive_letters or [""]:
                    logical = self._get_logical_disk(client, letter)
                    volume_name = _normalize(getattr(logical, "VolumeName", "")) if logical else ""
                    logical_size = (
                        _format_capacity(getattr(logical, "Size", 0)) if logical else capacity
                    )

                    devices.append(
                        {
                            "device_id": device_id if not letter else f"{device_id}:{letter}",
                            "name": volume_name
                            or _normalize(getattr(disk, "Model", ""))
                            or _normalize(getattr(disk, "Caption", ""))
                            or "USB Storage Device",
                            "manufacturer": _normalize(getattr(disk, "Manufacturer", ""))
                            or "Unknown",
                            "serial_number": self._clean_serial(
                                getattr(disk, "SerialNumber", "")
                            ),
                            "device_type": "Removable Storage",
                            "drive_letter": letter,
                            "capacity_bytes": logical_size or capacity,
                            "pnp_device_id": device_id,
                        }
                    )

            if not devices:
                devices.extend(self._enumerate_removable_logical_disks(client))

            return devices
        finally:
            pythoncom.CoUninitialize()

    def _enumerate_removable_logical_disks(self, client: Any) -> list[dict[str, Any]]:
        """Fallback for removable volumes when disk drive enumeration is sparse."""
        results: list[dict[str, Any]] = []
        for logical in client.Win32_LogicalDisk(DriveType=2):
            letter = _normalize(getattr(logical, "DeviceID", ""))
            if not letter:
                continue
            results.append(
                {
                    "device_id": f"removable-{letter}",
                    "name": _normalize(getattr(logical, "VolumeName", ""))
                    or f"Removable Disk ({letter})",
                    "manufacturer": "Unknown",
                    "serial_number": "",
                    "device_type": "Removable Storage",
                    "drive_letter": letter,
                    "capacity_bytes": _format_capacity(getattr(logical, "Size", 0)),
                    "pnp_device_id": f"removable-{letter}",
                }
            )
        return results

    def _resolve_drive_letters(self, client: Any, disk: Any) -> list[str]:
        letters: list[str] = []
        try:
            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical in partition.associators("Win32_LogicalDiskToPartition"):
                    letter = _normalize(getattr(logical, "DeviceID", ""))
                    if letter and letter not in letters:
                        letters.append(letter)
        except Exception:
            logger.debug("Failed to resolve drive letters via WMI associations", exc_info=True)
        return letters

    def _get_logical_disk(self, client: Any, letter: str) -> Any | None:
        if not letter:
            return None
        disks = client.Win32_LogicalDisk(DeviceID=letter)
        return disks[0] if disks else None

    @staticmethod
    def _clean_serial(serial: Any) -> str:
        text = _normalize(serial)
        if not text:
            return ""
        return re.sub(r"\s+", "", text)

    @staticmethod
    def scan_drive_threats(drive_letter: str) -> list[str]:
        """Lightweight heuristic scan for suspicious files on removable media."""
        if not drive_letter or sys.platform != "win32":
            return []

        root = drive_letter if drive_letter.endswith("\\") else f"{drive_letter}\\"
        threats: list[str] = []
        suspicious_names = {"autorun.inf", "desktop.ini.lnk", "setup.exe", "install.exe"}

        try:
            from pathlib import Path

            root_path = Path(root)
            if not root_path.exists():
                return threats

            for pattern in suspicious_names:
                if (root_path / pattern).exists():
                    threats.append(f"Suspicious file detected: {pattern}")

            for item in root_path.iterdir():
                if item.suffix.lower() in {".exe", ".bat", ".cmd", ".ps1", ".vbs"}:
                    threats.append(f"Executable on removable media: {item.name}")
                    if len(threats) >= 3:
                        break
        except OSError as exc:
            logger.debug("Drive scan skipped for %s: %s", drive_letter, exc)

        return threats[:5]
