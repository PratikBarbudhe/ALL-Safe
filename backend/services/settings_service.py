"""Centralized persistent configuration for all AllSafe modules."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from models.ransomware_models import RansomwareSettingsUpdate
from models.settings_models import (
    CURRENT_SETTINGS_VERSION,
    AllSafeSettings,
    SettingsActionResponse,
    SettingsExportResponse,
    SettingsGroupResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)
from utils.exceptions import SettingsServiceError

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
SETTINGS_BACKUP = DATA_DIR / "settings.json.bak"
SETTINGS_CORRUPT = DATA_DIR / "settings.json.corrupt"
LEGACY_RANSOMWARE_FILE = DATA_DIR / "ransomware_settings.json"
DEFAULT_TEMPLATE = DATA_DIR / "settings.json"
LOG_FILE = BACKEND_ROOT / "logs" / "settings_events.log"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3

GROUP_NAMES = (
    "system",
    "notifications",
    "ransomware",
    "usb",
    "ai_analysis",
    "dashboard",
    "quarantine",
    "logging",
    "scan",
    "update",
    "ui",
    "advanced",
)


class SettingsService:
    """Thread-safe JSON settings store with validation, backup, and module sync."""

    _instance: SettingsService | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._file_lock = threading.Lock()
        self._settings: AllSafeSettings = AllSafeSettings()
        self._last_saved_at: str = ""
        self._modified: bool = False
        self._event_logger = self._configure_logger()
        self.load()

    @classmethod
    def get_instance(cls) -> SettingsService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        settings_logger = logging.getLogger("allsafe.settings")
        if not settings_logger.handlers:
            handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            settings_logger.addHandler(handler)
            settings_logger.setLevel(logging.INFO)
            settings_logger.propagate = False
        return settings_logger

    def _log_event(self, message: str, level: int = logging.INFO) -> None:
        self._event_logger.log(level, message)

    def load(self) -> AllSafeSettings:
        """Load settings from disk with corruption recovery."""
        with self._file_lock:
            self._settings = self._load_from_disk()
            self._last_saved_at = datetime.now(timezone.utc).isoformat()
            self._modified = False
        self._log_event("Settings loaded from disk")
        return self._settings

    def _load_from_disk(self) -> AllSafeSettings:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_FILE.exists():
            migrated = self._migrate_legacy_ransomware()
            if migrated:
                self._write_file(migrated)
                return migrated
            defaults = self._default_settings()
            self._write_file(defaults)
            return defaults

        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return self._validate_and_migrate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Settings file corrupt, attempting recovery: %s", exc)
            self._log_event(f"Settings corrupt: {exc}", logging.WARNING)
            return self._recover_settings(exc)

    def _recover_settings(self, exc: Exception) -> AllSafeSettings:
        try:
            shutil.copy2(SETTINGS_FILE, SETTINGS_CORRUPT)
        except OSError:
            pass
        if SETTINGS_BACKUP.exists():
            try:
                raw = json.loads(SETTINGS_BACKUP.read_text(encoding="utf-8"))
                settings = self._validate_and_migrate(raw)
                self._write_file(settings)
                self._log_event("Recovered settings from backup")
                return settings
            except Exception:
                pass
        migrated = self._migrate_legacy_ransomware()
        if migrated:
            self._write_file(migrated)
            return migrated
        defaults = self._default_settings()
        self._write_file(defaults)
        self._log_event(f"Reset to defaults after corruption: {exc}", logging.ERROR)
        return defaults

    def _default_settings(self) -> AllSafeSettings:
        settings = AllSafeSettings()
        try:
            from monitoring.ransomware_monitor import RansomwareMonitor

            settings.ransomware.protected_folders = [
                str(p) for p in RansomwareMonitor.resolve_default_folders()
            ]
        except Exception:
            pass
        return settings

    def _migrate_legacy_ransomware(self) -> AllSafeSettings | None:
        if not LEGACY_RANSOMWARE_FILE.exists():
            return None
        try:
            legacy = json.loads(LEGACY_RANSOMWARE_FILE.read_text(encoding="utf-8"))
            settings = self._default_settings()
            settings.ransomware.monitoring_enabled = legacy.get(
                "monitoring_enabled", True
            )
            settings.ransomware.auto_quarantine = legacy.get("auto_quarantine", True)
            sens = legacy.get("sensitivity", legacy.get("sensitivity_level", "medium"))
            if sens in ("low", "medium", "high"):
                settings.ransomware.sensitivity_level = sens
            folders = legacy.get("protected_folders")
            if isinstance(folders, list):
                settings.ransomware.protected_folders = folders
            self._log_event("Migrated legacy ransomware_settings.json")
            return settings
        except Exception as exc:
            logger.warning("Legacy ransomware settings migration failed: %s", exc)
            return None

    def _validate_and_migrate(self, raw: dict[str, Any]) -> AllSafeSettings:
        version = raw.get("version", 0)
        if version < CURRENT_SETTINGS_VERSION:
            raw["version"] = CURRENT_SETTINGS_VERSION
        settings = AllSafeSettings.model_validate(raw)
        return settings

    def _write_file(self, settings: AllSafeSettings) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            try:
                shutil.copy2(SETTINGS_FILE, SETTINGS_BACKUP)
            except OSError:
                pass
        SETTINGS_FILE.write_text(
            settings.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_settings(self) -> SettingsResponse:
        with self._file_lock:
            return SettingsResponse(
                settings=self._settings.model_copy(deep=True),
                modified=self._modified,
                last_saved_at=self._last_saved_at or datetime.now(timezone.utc).isoformat(),
            )

    def get_group(self, group: str) -> SettingsGroupResponse:
        if group not in GROUP_NAMES:
            raise SettingsServiceError(f"Unknown settings group: {group}")
        with self._file_lock:
            data = getattr(self._settings, group).model_dump()
        return SettingsGroupResponse(group=group, data=data)

    def update(self, request: SettingsUpdateRequest) -> SettingsResponse:
        with self._file_lock:
            current = self._settings.model_dump()
            patch = request.model_dump(exclude_unset=True)
            for group_name, group_patch in patch.items():
                if group_patch is None or group_name not in GROUP_NAMES:
                    continue
                if not isinstance(group_patch, dict):
                    continue
                group_data = current.get(group_name, {})
                if isinstance(group_data, dict):
                    group_data.update(group_patch)
                    current[group_name] = group_data
            try:
                self._settings = AllSafeSettings.model_validate(current)
            except ValueError as exc:
                raise SettingsServiceError(f"Invalid settings: {exc}") from exc
            self._write_file(self._settings)
            self._last_saved_at = datetime.now(timezone.utc).isoformat()
            self._modified = False
            saved = self._settings.model_copy(deep=True)

        self._log_event("Settings updated and saved")
        self.apply_to_modules()
        return SettingsResponse(
            settings=saved,
            modified=False,
            last_saved_at=self._last_saved_at,
        )

    def reset(self) -> SettingsActionResponse:
        with self._file_lock:
            self._settings = self._default_settings()
            self._write_file(self._settings)
            self._last_saved_at = datetime.now(timezone.utc).isoformat()
            self._modified = False
            saved = self._settings.model_copy(deep=True)
        self._log_event("Settings reset to defaults")
        self.apply_to_modules()
        return SettingsActionResponse(
            status="ok",
            message="All settings restored to defaults",
            settings=saved,
        )

    def export_settings(self) -> SettingsExportResponse:
        with self._file_lock:
            return SettingsExportResponse(
                exported_at=datetime.now(timezone.utc).isoformat(),
                settings=self._settings.model_copy(deep=True),
            )

    def import_settings(self, raw: dict[str, Any]) -> SettingsActionResponse:
        try:
            settings = self._validate_and_migrate(raw)
        except ValueError as exc:
            raise SettingsServiceError(f"Import validation failed: {exc}") from exc
        with self._file_lock:
            self._settings = settings
            self._write_file(self._settings)
            self._last_saved_at = datetime.now(timezone.utc).isoformat()
            self._modified = False
            saved = self._settings.model_copy(deep=True)
        self._log_event("Settings imported from configuration file")
        self.apply_to_modules()
        return SettingsActionResponse(
            status="ok",
            message="Configuration imported successfully",
            settings=saved,
        )

    @property
    def settings(self) -> AllSafeSettings:
        return self._settings

    def merge_group(self, group: str, patch: dict[str, Any]) -> None:
        """Persist a partial group update without re-applying to modules (avoids loops)."""
        if group not in GROUP_NAMES:
            raise SettingsServiceError(f"Unknown settings group: {group}")
        with self._file_lock:
            current = self._settings.model_dump()
            group_data = current.get(group, {})
            if isinstance(group_data, dict):
                group_data.update(patch)
                current[group] = group_data
            self._settings = AllSafeSettings.model_validate(current)
            self._write_file(self._settings)
            self._last_saved_at = datetime.now(timezone.utc).isoformat()

    def apply_to_modules(self) -> None:
        """Push current settings into running services."""
        s = self._settings
        self._apply_system(s)
        self._apply_notifications(s)
        self._apply_ransomware(s)
        self._apply_usb(s)
        self._apply_ai_analysis(s)
        self._apply_logging(s)
        self._apply_threat_monitoring(s)

    def _apply_system(self, s: AllSafeSettings) -> None:
        try:
            from utils.windows_startup import disable_startup, enable_startup

            if s.system.auto_start_with_windows:
                enable_startup()
            else:
                disable_startup()
        except Exception:
            logger.exception("Failed to apply system startup settings")

    def _apply_notifications(self, s: AllSafeSettings) -> None:
        try:
            from services.notification_service import notification_service

            notification_service.apply_preferences(s.notifications)
        except Exception:
            logger.exception("Failed to apply notification settings")

    def _apply_ransomware(self, s: AllSafeSettings) -> None:
        try:
            from services.ransomware_service import ransomware_service

            rw = s.ransomware
            folders = rw.protected_folders or []
            ransomware_service.apply_settings(
                RansomwareSettingsUpdate(
                    monitoring_enabled=rw.monitoring_enabled,
                    auto_quarantine=rw.auto_quarantine,
                    sensitivity=rw.sensitivity_level,
                    protected_folders=folders if folders else None,
                )
            )
            if rw.monitoring_enabled and s.system.background_monitoring:
                if not ransomware_service._monitor.is_running:
                    ransomware_service.bootstrap_if_enabled()
            elif not rw.monitoring_enabled:
                ransomware_service.stop_monitoring()
        except Exception:
            logger.exception("Failed to apply ransomware settings")

    def _apply_usb(self, s: AllSafeSettings) -> None:
        try:
            from services.usb_service import usb_service

            usb_service.apply_preferences(s.usb)
            if s.usb.monitoring_enabled and s.system.background_monitoring:
                usb_service.start_background_monitor()
            else:
                usb_service.stop_background_monitor()
        except Exception:
            logger.exception("Failed to apply USB settings")

    def _apply_ai_analysis(self, s: AllSafeSettings) -> None:
        try:
            from services.ai_analysis_service import ai_analysis_service

            ai_analysis_service.apply_preferences(s.ai_analysis)
        except Exception:
            logger.exception("Failed to apply AI analysis settings")

    def _apply_logging(self, s: AllSafeSettings) -> None:
        try:
            import logging as std_logging

            from utils.logging_config import setup_logging

            level = std_logging.DEBUG if s.logging.verbose_logging else std_logging.INFO
            setup_logging(level)
            self._log_event(
                f"Logging level set to {'DEBUG' if s.logging.verbose_logging else 'INFO'}"
            )
        except Exception:
            logger.exception("Failed to apply logging settings")

    def _apply_threat_monitoring(self, s: AllSafeSettings) -> None:
        try:
            from services.threat_log_service import threat_log_service

            if s.system.auto_start_monitoring and s.system.background_monitoring:
                if not threat_log_service.monitoring_active:
                    threat_log_service.start_background_monitor()
            else:
                threat_log_service.stop_background_monitor()
        except Exception:
            logger.exception("Failed to apply threat monitoring settings")

    def initialize_modules(self) -> None:
        """Called at application startup."""
        self.apply_to_modules()

    async def get_settings_async(self) -> SettingsResponse:
        return await asyncio.to_thread(self.get_settings)

    async def get_group_async(self, group: str) -> SettingsGroupResponse:
        return await asyncio.to_thread(self.get_group, group)

    async def update_async(self, request: SettingsUpdateRequest) -> SettingsResponse:
        return await asyncio.to_thread(self.update, request)

    async def reset_async(self) -> SettingsActionResponse:
        return await asyncio.to_thread(self.reset)

    async def export_async(self) -> SettingsExportResponse:
        return await asyncio.to_thread(self.export_settings)

    async def import_async(self, raw: dict[str, Any]) -> SettingsActionResponse:
        return await asyncio.to_thread(self.import_settings, raw)


settings_service = SettingsService.get_instance()
