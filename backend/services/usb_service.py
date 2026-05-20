import asyncio
import json
import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.usb_models import (
    UsbDevice,
    UsbDeviceListResponse,
    UsbEvent,
    UsbHistoryResponse,
)
from monitoring.usb_monitor import UsbMonitor
from utils.exceptions import UsbMonitorError

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRUSTED_FILE = DATA_DIR / "trusted_usb_devices.json"
BLOCKED_FILE = DATA_DIR / "blocked_usb_devices.json"
USB_LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "usb_events.log"

RECENTLY_CONNECTED_SECONDS = 60
HISTORY_LIMIT = 200
POLL_INTERVAL_SECONDS = 1.0


class UsbService:
    """Real-time USB monitoring with in-memory state and event history."""

    _instance: "UsbService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._monitoring_enabled = True
        self._trusted_devices_only = False
        self._alert_unknown_devices = True
        self._auto_scan_on_connect = True
        self._monitor = UsbMonitor()
        self._connected: dict[str, UsbDevice] = {}
        self._first_seen: dict[str, datetime] = {}
        self._history: deque[UsbEvent] = deque(maxlen=HISTORY_LIMIT)
        self._serial_registry: dict[str, str] = {}
        self._trusted_ids: set[str] = set()
        self._trusted_serials: set[str] = set()
        self._blocked_ids: set[str] = set()
        self._blocked_serials: set[str] = set()
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._usb_logger = self._configure_usb_logger()
        self._load_policy_files()

    @classmethod
    def get_instance(cls) -> "UsbService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_usb_logger(self) -> logging.Logger:
        USB_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        usb_logger = logging.getLogger("allsafe.usb")
        if not usb_logger.handlers:
            handler = logging.FileHandler(USB_LOG_FILE, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            usb_logger.addHandler(handler)
            usb_logger.setLevel(logging.INFO)
        return usb_logger

    def _load_policy_files(self) -> None:
        self._trusted_ids, self._trusted_serials = self._read_trusted_policy(TRUSTED_FILE)
        self._blocked_ids, self._blocked_serials = self._read_blocked_policy(BLOCKED_FILE)

    @staticmethod
    def _read_trusted_policy(path: Path) -> tuple[set[str], set[str]]:
        if not path.exists():
            return set(), set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return set(data.get("trusted_device_ids", [])), set(
                data.get("trusted_serial_numbers", [])
            )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load trusted USB policy %s: %s", path, exc)
            return set(), set()

    @staticmethod
    def _read_blocked_policy(path: Path) -> tuple[set[str], set[str]]:
        if not path.exists():
            return set(), set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return set(data.get("blocked_device_ids", [])), set(
                data.get("blocked_serial_numbers", [])
            )
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load blocked USB policy %s: %s", path, exc)
            return set(), set()

    def apply_preferences(self, prefs: Any) -> None:
        self._monitoring_enabled = prefs.monitoring_enabled
        self._trusted_devices_only = prefs.trusted_devices_only
        self._alert_unknown_devices = prefs.alert_unknown_devices
        self._auto_scan_on_connect = prefs.auto_scan_on_connect

    def start_background_monitor(self) -> None:
        if not self._monitoring_enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="usb-monitor",
            daemon=True,
        )
        self._thread.start()
        self._usb_logger.info("USB background monitor started")
        logger.info("USB background monitor started")

    def stop_background_monitor(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._usb_logger.info("USB background monitor stopped")

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_devices()
            except Exception:
                logger.exception("USB monitor poll failed")
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def _poll_devices(self) -> None:
        raw_devices = self._monitor.enumerate_devices()
        now = datetime.now(timezone.utc)
        current_ids: set[str] = set()

        enriched: list[UsbDevice] = []
        for raw in raw_devices:
            device = self._enrich_device(raw, now)
            current_ids.add(device.device_id)
            enriched.append(device)

        with self._state_lock:
            previous_ids = set(self._connected.keys())

            for device in enriched:
                if device.device_id not in previous_ids:
                    self._register_event(device, "inserted", now)
                self._connected[device.device_id] = device

            for removed_id in previous_ids - current_ids:
                removed = self._connected.pop(removed_id, None)
                self._first_seen.pop(removed_id, None)
                if removed:
                    self._register_event(removed, "removed", now)

    def _enrich_device(self, raw: dict, now: datetime) -> UsbDevice:
        device_id = raw["device_id"]
        if device_id not in self._first_seen:
            self._first_seen[device_id] = now

        connected_time = self._first_seen[device_id]
        serial = raw.get("serial_number", "")
        protection_status, threat_reasons, is_duplicate, is_unauthorized = (
            self._evaluate_protection(raw, serial)
        )

        drive_threats = self._monitor.scan_drive_threats(raw.get("drive_letter", ""))
        combined_threats = list(dict.fromkeys(threat_reasons + drive_threats))

        if combined_threats and protection_status not in {"blocked"}:
            protection_status = "suspicious"

        return UsbDevice(
            device_id=device_id,
            name=raw.get("name", "USB Device"),
            manufacturer=raw.get("manufacturer", "Unknown"),
            serial_number=serial,
            connected_time=connected_time.isoformat(),
            device_type=raw.get("device_type", "Removable Storage"),
            status="connected",
            drive_letter=raw.get("drive_letter", ""),
            capacity_bytes=raw.get("capacity_bytes", 0),
            protection_status=protection_status,
            threat_count=len(combined_threats),
            threat_reasons=combined_threats,
            is_duplicate=is_duplicate,
            is_unauthorized=is_unauthorized,
            last_scan_time=now.isoformat(),
        )

    def _evaluate_protection(
        self, raw: dict, serial: str
    ) -> tuple[str, list[str], bool, bool]:
        device_id = raw["device_id"]
        name = raw.get("name", "").lower()
        manufacturer = raw.get("manufacturer", "").lower()
        reasons: list[str] = []
        is_duplicate = False
        is_unauthorized = False

        if device_id in self._blocked_ids or serial in self._blocked_serials:
            return "blocked", ["Device is on the block list (monitor-only)"], False, True

        if device_id in self._trusted_ids or serial in self._trusted_serials:
            return "trusted", [], False, False

        if self._trusted_devices_only:
            return "suspicious", ["Device not on trusted list"], False, True

        if serial:
            if serial in self._serial_registry and self._serial_registry[serial] != device_id:
                is_duplicate = True
                reasons.append("Duplicate serial number detected across devices")
            self._serial_registry[serial] = device_id

        if not serial:
            reasons.append("Missing serial number")
        if "unknown" in name or manufacturer in {"", "unknown", "standard disk drives"}:
            reasons.append("Unknown or generic device signature")
        if name in {"usb device", "removable disk", ""}:
            reasons.append("Unrecognized device name")

        connected_at = self._first_seen.get(device_id)
        if connected_at:
            age = (datetime.now(timezone.utc) - connected_at).total_seconds()
            if age <= RECENTLY_CONNECTED_SECONDS and not reasons:
                return "recently_connected", [], is_duplicate, False

        if reasons:
            is_unauthorized = True
            return "suspicious", reasons, is_duplicate, is_unauthorized

        return "unknown", [], is_duplicate, False

    def _register_event(self, device: UsbDevice, event_type: str, now: datetime) -> None:
        event = UsbEvent(
            event_id=str(uuid.uuid4()),
            device_id=device.device_id,
            device_name=device.name,
            event_type=event_type,
            timestamp=now.isoformat(),
            drive_letter=device.drive_letter,
            protection_status=device.protection_status,
        )
        self._history.appendleft(event)
        self._usb_logger.info(
            "USB %s | %s | %s | drive=%s | status=%s",
            event_type,
            device.name,
            device.device_id,
            device.drive_letter or "N/A",
            device.protection_status,
        )
        if self._alert_unknown_devices or device.protection_status != "unknown":
            self._emit_usb_notification(device, event_type)

    def _emit_usb_notification(self, device: UsbDevice, event_type: str) -> None:
        try:
            from models.notification_models import NotificationCategory, NotificationSeverity
            from services.notification_service import notification_service

            status = device.protection_status
            if event_type == "removed":
                severity = NotificationSeverity.INFO.value
                title = "USB Device Removed"
            elif status in ("suspicious", "blocked") or device.is_unauthorized:
                severity = NotificationSeverity.HIGH.value
                title = "Suspicious USB Device"
            elif status == "recently_connected":
                severity = NotificationSeverity.WARNING.value
                title = "USB Device Connected"
            else:
                severity = NotificationSeverity.INFO.value
                title = "USB Device Connected"

            drive = device.drive_letter or "N/A"
            message = f"{device.name} ({drive}) — {event_type}, status: {status}"
            notification_service.emit(
                title=title,
                message=message,
                severity=severity,
                category=NotificationCategory.USB_SECURITY.value,
                source_module="usb_monitor",
                action_required=severity == NotificationSeverity.HIGH.value,
                metadata={
                    "device_id": device.device_id,
                    "event_type": event_type,
                    "protection_status": status,
                },
                show_toast=severity != NotificationSeverity.INFO.value,
                dedupe_key=f"usb:{device.device_id}:{event_type}:{status}",
            )
        except Exception:
            logger.exception("Failed to emit USB notification")

    async def get_devices(self) -> UsbDeviceListResponse:
        return await asyncio.to_thread(self._build_device_response)

    async def get_history(self) -> UsbHistoryResponse:
        return await asyncio.to_thread(self._build_history_response)

    def _build_device_response(self) -> UsbDeviceListResponse:
        with self._state_lock:
            devices = list(self._connected.values())

        safe_count = 0
        threat_count = 0
        scanning_count = 0

        for device in devices:
            ui = self._map_ui_status(device)
            if ui == "safe":
                safe_count += 1
            elif ui == "threat":
                threat_count += 1
            else:
                scanning_count += 1

        return UsbDeviceListResponse(
            devices=devices,
            total_connected=len(devices),
            safe_count=safe_count,
            threat_count=threat_count,
            scanning_count=scanning_count,
        )

    def _build_history_response(self) -> UsbHistoryResponse:
        with self._state_lock:
            events = list(self._history)
        return UsbHistoryResponse(events=events, total_events=len(events))

    @staticmethod
    def _map_ui_status(device: UsbDevice) -> str:
        if device.protection_status in {"suspicious", "blocked"} or device.is_unauthorized:
            return "threat"
        if device.protection_status in {"unknown", "recently_connected"}:
            return "scanning"
        return "safe"

    def force_rescan(self) -> None:
        """Trigger immediate USB poll (used by Scan All Devices)."""
        try:
            self._poll_devices()
        except Exception as exc:
            raise UsbMonitorError("USB rescan failed") from exc


usb_service = UsbService.get_instance()
