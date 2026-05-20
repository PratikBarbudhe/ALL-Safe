import asyncio
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from models.quarantine_models import QuarantineAddRequest
from models.ransomware_models import (
    RansomwareActionResponse,
    RansomwareEvent,
    RansomwareEventListResponse,
    RansomwareSettings,
    RansomwareSettingsUpdate,
    RansomwareStatusResponse,
)
from monitoring.ransomware_monitor import RansomwareDetection, RansomwareMonitor
from services.threat_counters import threat_counter_store
from utils.exceptions import QuarantineServiceError, RansomwareServiceError

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "ransomware_settings.json"
DB_PATH = DATA_DIR / "ransomware.db"
LOG_FILE = BACKEND_ROOT / "logs" / "ransomware_events.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

STATUS_DETECTED = "Threat Detected"
STATUS_SUSPICIOUS = "Suspicious Activity"
STATUS_MONITORING = "Monitoring"
STATUS_PROTECTED = "Protected"

PROTECTED_COUNT_CAP = 250_000


class RansomwareService:
    """Ransomware heuristic detection, response, and persistence."""

    _instance: "RansomwareService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._db_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._monitor = RansomwareMonitor(self._on_detection)
        self._settings = self._load_settings()
        self._event_logger = self._configure_logger()
        self._init_database()
        self._protected_files_cache = 0
        self._protected_files_cached_at = 0.0
        self._recent_critical = False

    @classmethod
    def get_instance(cls) -> "RansomwareService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        rw_logger = logging.getLogger("allsafe.ransomware")
        if not rw_logger.handlers:
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
            rw_logger.addHandler(handler)
            rw_logger.setLevel(logging.INFO)
            rw_logger.propagate = False
        return rw_logger

    def _load_settings(self) -> RansomwareSettings:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return RansomwareSettings(**data)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Invalid ransomware settings, using defaults: %s", exc)
        folders = [str(p) for p in RansomwareMonitor.resolve_default_folders()]
        settings = RansomwareSettings(protected_folders=folders)
        self._save_settings(settings)
        return settings

    def _save_settings(self, settings: RansomwareSettings) -> None:
        SETTINGS_FILE.write_text(
            settings.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _init_database(self) -> None:
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ransomware_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        threat_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_action TEXT NOT NULL,
                        quarantined INTEGER NOT NULL DEFAULT 0,
                        folder_path TEXT NOT NULL,
                        heuristic_type TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ransomware_ts ON ransomware_events(timestamp)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ransomware_severity ON ransomware_events(severity)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @property
    def monitoring_active(self) -> bool:
        return self._monitor.is_running

    def start_monitoring(self) -> RansomwareActionResponse:
        with self._state_lock:
            if self._monitor.is_running:
                return RansomwareActionResponse(
                    message="Ransomware protection is already active",
                    monitoring_active=True,
                )
            try:
                paths = self._monitor.start(
                    protected_folders=self._settings.protected_folders,
                    sensitivity=self._settings.sensitivity,
                )
            except Exception as exc:
                logger.exception("Failed to start ransomware monitor")
                raise RansomwareServiceError(
                    "Unable to start ransomware monitoring"
                ) from exc

            self._settings.monitoring_enabled = True
            self._save_settings(self._settings)
            self._event_logger.info(
                "Ransomware monitoring started | folders=%s", ", ".join(paths)
            )
            self._schedule_file_count_refresh()
            return RansomwareActionResponse(
                message=f"Ransomware protection enabled ({len(paths)} folders)",
                monitoring_active=True,
            )

    def stop_monitoring(self) -> RansomwareActionResponse:
        with self._state_lock:
            self._monitor.stop()
            self._settings.monitoring_enabled = False
            self._save_settings(self._settings)
            self._recent_critical = False
            self._event_logger.info("Ransomware monitoring stopped")
            return RansomwareActionResponse(
                message="Ransomware protection stopped",
                monitoring_active=False,
            )

    def apply_settings(self, update: RansomwareSettingsUpdate) -> RansomwareSettings:
        data = self._settings.model_dump()
        patch = update.model_dump(exclude_unset=True)
        data.update(patch)
        if "sensitivity" in patch and patch["sensitivity"] not in (
            "low",
            "medium",
            "high",
        ):
            raise RansomwareServiceError("Sensitivity must be low, medium, or high")
        self._settings = RansomwareSettings(**data)
        self._save_settings(self._settings)

        if self._monitor.is_running:
            self._monitor.stop()
            if self._settings.monitoring_enabled:
                self._monitor.start(
                    protected_folders=self._settings.protected_folders,
                    sensitivity=self._settings.sensitivity,
                )

        return self._settings

    def get_settings(self) -> RansomwareSettings:
        return self._settings

    def _on_detection(self, detection: RansomwareDetection) -> None:
        try:
            self._handle_detection(detection)
        except Exception:
            logger.exception(
                "Failed to handle ransomware detection for %s",
                detection.file_path,
            )

    def _handle_detection(self, detection: RansomwareDetection) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        response_action = "logged"
        quarantined = False
        status = STATUS_SUSPICIOUS
        if detection.severity in ("high", "critical"):
            status = STATUS_DETECTED
            with self._state_lock:
                self._recent_critical = True

        if (
            self._settings.auto_quarantine
            and detection.severity in ("high", "critical")
            and Path(detection.file_path).is_file()
        ):
            try:
                from services.quarantine_service import quarantine_service

                quarantine_service.add_file(
                    QuarantineAddRequest(
                        file_path=detection.file_path,
                        reason=f"Ransomware heuristic: {detection.heuristic_type}",
                        severity=detection.severity,
                        category="Rapid Modification",
                    )
                )
                quarantined = True
                response_action = "quarantined"
                threat_counter_store.record_blocked()
            except QuarantineServiceError as exc:
                response_action = f"quarantine_failed: {exc}"
                self._event_logger.warning(
                    "Auto-quarantine failed for %s: %s",
                    detection.file_path,
                    exc,
                )
            except Exception:
                response_action = "quarantine_failed"
                logger.exception("Auto-quarantine error")

        if response_action == "logged" and detection.severity in ("high", "critical"):
            threat_counter_store.record_blocked()

        with self._db_lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO ransomware_events (
                        timestamp, file_path, event_type, severity, threat_name,
                        description, status, response_action, quarantined,
                        folder_path, heuristic_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        detection.file_path,
                        detection.event_type,
                        detection.severity,
                        detection.threat_name,
                        detection.description,
                        status,
                        response_action,
                        1 if quarantined else 0,
                        detection.folder_path,
                        detection.heuristic_type,
                    ),
                )
                conn.commit()
                event_id = cursor.lastrowid or 0
            finally:
                conn.close()

        self._event_logger.info(
            "%s | %s | %s | %s | %s",
            detection.severity.upper(),
            detection.threat_name,
            response_action,
            detection.file_path,
            detection.description,
        )

        from services.threat_log_service import threat_log_service

        threat_log_service.log_security_event(
            file_path=detection.file_path,
            event_type=detection.event_type,
            severity=detection.severity,
            category="Rapid Modification",
            status="Quarantined" if quarantined else "Blocked",
            description=f"[Ransomware] {detection.description}",
        )
        threat_log_service.sync_dashboard_counters()

    def get_events(self, limit: int = 50) -> RansomwareEventListResponse:
        limit = max(1, min(limit, 200))
        with self._db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM ransomware_events
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                total = conn.execute(
                    "SELECT COUNT(*) FROM ransomware_events"
                ).fetchone()[0]
            finally:
                conn.close()

        events = [self._row_to_event(row) for row in rows]
        return RansomwareEventListResponse(events=events, total=total)

    def get_status(self) -> RansomwareStatusResponse:
        self._schedule_file_count_refresh()
        stats = self._compute_stats()
        protection_status = self._resolve_protection_status(stats)
        layers = [
            {
                "name": "File System Monitor",
                "status": "active" if self.monitoring_active else "inactive",
            },
            {
                "name": "Behavior Detection",
                "status": "active" if self.monitoring_active else "inactive",
            },
            {
                "name": "Backup Protection",
                "status": "standby",
            },
            {
                "name": "Network Isolation",
                "status": "standby",
            },
        ]
        return RansomwareStatusResponse(
            protection_status=protection_status,
            monitoring_active=self.monitoring_active,
            monitoring_enabled=self._settings.monitoring_enabled,
            auto_quarantine=self._settings.auto_quarantine,
            sensitivity=self._settings.sensitivity,
            protected_folders=self._settings.protected_folders,
            attempts_blocked=stats["blocked"],
            protected_files_count=self._count_protected_files(),
            success_rate_percent=stats["success_rate"],
            events_last_24h=stats["events_24h"],
            critical_events_24h=stats["critical_24h"],
            layers=layers,
        )

    def _resolve_protection_status(self, stats: dict) -> str:
        if not self.monitoring_active:
            if self._settings.monitoring_enabled:
                return STATUS_MONITORING
            return STATUS_MONITORING
        if stats["critical_24h"] > 0 or self._recent_critical:
            return STATUS_DETECTED
        if stats["events_24h"] > 0:
            return STATUS_SUSPICIOUS
        return STATUS_PROTECTED

    def _compute_stats(self) -> dict:
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(hours=24)).isoformat()
        with self._db_lock:
            conn = self._connect()
            try:
                blocked = conn.execute(
                    """
                    SELECT COUNT(*) FROM ransomware_events
                    WHERE response_action IN ('quarantined', 'logged')
                    AND severity IN ('high', 'critical')
                    """
                ).fetchone()[0]
                events_24h = conn.execute(
                    "SELECT COUNT(*) FROM ransomware_events WHERE timestamp >= ?",
                    (cutoff,),
                ).fetchone()[0]
                critical_24h = conn.execute(
                    """
                    SELECT COUNT(*) FROM ransomware_events
                    WHERE timestamp >= ? AND severity = 'critical'
                    """,
                    (cutoff,),
                ).fetchone()[0]
                responded = conn.execute(
                    """
                    SELECT COUNT(*) FROM ransomware_events
                    WHERE response_action IN ('quarantined', 'logged')
                    """
                ).fetchone()[0]
                total = conn.execute(
                    "SELECT COUNT(*) FROM ransomware_events"
                ).fetchone()[0]
            finally:
                conn.close()

        success_rate = 100.0
        if total > 0:
            success_rate = min(100.0, round((responded / total) * 100, 1))

        return {
            "blocked": blocked,
            "events_24h": events_24h,
            "critical_24h": critical_24h,
            "success_rate": success_rate,
        }

    def _count_protected_files(self) -> int:
        """Return cached protected file count (refreshed asynchronously)."""
        return self._protected_files_cache

    def _refresh_protected_file_count_async(self) -> None:
        import time

        def worker() -> None:
            count = 0
            for folder in self._settings.protected_folders:
                root = Path(folder)
                if not root.exists():
                    continue
                try:
                    for _dirpath, _dirnames, filenames in os.walk(root):
                        count += len(filenames)
                        if count >= PROTECTED_COUNT_CAP:
                            break
                except OSError:
                    continue
                if count >= PROTECTED_COUNT_CAP:
                    break
            self._protected_files_cache = count
            self._protected_files_cached_at = time.monotonic()

        threading.Thread(target=worker, name="ransomware-file-count", daemon=True).start()

    def _schedule_file_count_refresh(self) -> None:
        import time

        if time.monotonic() - self._protected_files_cached_at < 300:
            return
        self._refresh_protected_file_count_async()

    def _row_to_event(self, row: sqlite3.Row) -> RansomwareEvent:
        return RansomwareEvent(
            id=row["id"],
            timestamp=self._format_timestamp(row["timestamp"]),
            file_path=row["file_path"],
            event_type=row["event_type"],
            severity=row["severity"],
            threat_name=row["threat_name"],
            description=row["description"],
            status=row["status"],
            response_action=row["response_action"],
            quarantined=bool(row["quarantined"]),
            folder_path=row["folder_path"],
            heuristic_type=row["heuristic_type"],
        )

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return iso_timestamp

    def bootstrap_if_enabled(self) -> None:
        self._schedule_file_count_refresh()
        if self._settings.monitoring_enabled:
            try:
                self.start_monitoring()
            except RansomwareServiceError as exc:
                logger.error("Ransomware auto-start failed: %s", exc)

    async def get_status_async(self) -> RansomwareStatusResponse:
        return await asyncio.to_thread(self.get_status)

    async def get_events_async(self, limit: int = 50) -> RansomwareEventListResponse:
        return await asyncio.to_thread(lambda: self.get_events(limit=limit))

    async def start_monitoring_async(self) -> RansomwareActionResponse:
        return await asyncio.to_thread(self.start_monitoring)

    async def stop_monitoring_async(self) -> RansomwareActionResponse:
        return await asyncio.to_thread(self.stop_monitoring)

    async def apply_settings_async(
        self, update: RansomwareSettingsUpdate
    ) -> RansomwareSettings:
        return await asyncio.to_thread(self.apply_settings, update)


ransomware_service = RansomwareService.get_instance()
