import asyncio
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from models.threat_models import (
    ThreatClearResponse,
    ThreatLogEntry,
    ThreatLogListResponse,
    ThreatSeverity,
    ThreatStatsResponse,
)
from monitoring.file_monitor import FileMonitor
from services.threat_counters import threat_counter_store
from utils.exceptions import ThreatLogServiceError

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "threat_logs.db"
THREAT_LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "threat_events.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
ACTIVE_THREAT_HOURS = 24


class ThreatLogService:
    """Persistent threat logging with real-time filesystem monitoring."""

    _instance: "ThreatLogService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._db_lock = threading.Lock()
        self._file_monitor = FileMonitor(self._on_filesystem_event)
        self._threat_logger = self._configure_threat_logger()
        self._init_database()

    @classmethod
    def get_instance(cls) -> "ThreatLogService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_threat_logger(self) -> logging.Logger:
        THREAT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        threat_logger = logging.getLogger("allsafe.threats")
        if not threat_logger.handlers:
            handler = RotatingFileHandler(
                THREAT_LOG_FILE,
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
            threat_logger.addHandler(handler)
            threat_logger.setLevel(logging.INFO)
            threat_logger.propagate = False
        return threat_logger

    def _init_database(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS threat_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        category TEXT NOT NULL,
                        process_name TEXT DEFAULT '',
                        status TEXT NOT NULL,
                        description TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_threat_timestamp ON threat_logs(timestamp)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_threat_severity ON threat_logs(severity)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_threat_category ON threat_logs(category)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def start_background_monitor(self) -> None:
        try:
            paths = self._file_monitor.start()
            self._threat_logger.info(
                "File system monitor started | paths=%s", ", ".join(paths)
            )
            logger.info("File system monitor started on %d paths", len(paths))
            self._sync_dashboard_counters()
        except Exception as exc:
            logger.exception("Failed to start file monitor")
            self._threat_logger.error("File monitor start failed: %s", exc)
            raise ThreatLogServiceError(
                "Unable to start filesystem monitoring"
            ) from exc

    def stop_background_monitor(self) -> None:
        self._file_monitor.stop()
        self._threat_logger.info("File system monitor stopped")
        logger.info("File system monitor stopped")

    @property
    def monitoring_active(self) -> bool:
        return self._file_monitor.is_running

    @property
    def watched_paths(self) -> list[str]:
        return self._file_monitor.watched_paths

    def _on_filesystem_event(
        self,
        file_path: str,
        event_type: str,
        severity: str,
        category: str,
        process_name: str,
        status: str,
        description: str,
    ) -> None:
        try:
            self._insert_event(
                file_path=file_path,
                event_type=event_type,
                severity=severity,
                category=category,
                process_name=process_name,
                status=status,
                description=description,
            )
        except Exception:
            logger.exception("Failed to record threat event for %s", file_path)

    def _insert_event(
        self,
        *,
        file_path: str,
        event_type: str,
        severity: str,
        category: str,
        process_name: str,
        status: str,
        description: str,
    ) -> ThreatLogEntry:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._db_lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO threat_logs (
                        timestamp, file_path, event_type, severity, category,
                        process_name, status, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        file_path,
                        event_type,
                        severity,
                        category,
                        process_name or "",
                        status,
                        description,
                    ),
                )
                conn.commit()
                row_id = cursor.lastrowid or 0
            finally:
                conn.close()

        self._threat_logger.info(
            "%s | %s | %s | %s | %s | %s",
            severity.upper(),
            category,
            event_type,
            status,
            file_path,
            description,
        )
        self._sync_dashboard_counters()
        return ThreatLogEntry(
            id=row_id,
            timestamp=timestamp,
            file_path=file_path,
            event_type=event_type,
            severity=severity,
            category=category,
            process_name=process_name or "",
            status=status,
            description=description,
        )

    def log_security_event(
        self,
        *,
        file_path: str,
        event_type: str,
        severity: str,
        category: str,
        status: str,
        description: str,
        process_name: str = "",
    ) -> ThreatLogEntry:
        """Record an audit event from quarantine or other security modules."""
        return self._insert_event(
            file_path=file_path,
            event_type=event_type,
            severity=severity,
            category=category,
            process_name=process_name,
            status=status,
            description=description,
        )

    def sync_dashboard_counters(self) -> None:
        """Refresh in-memory dashboard threat counters from persisted logs."""
        self._sync_dashboard_counters()

    def _sync_dashboard_counters(self) -> None:
        stats = self._compute_stats()
        threat_counter_store.set_active_threats(stats.active_threats)
        threat_counter_store.blocked_threats = stats.blocked_threats
        try:
            from services.quarantine_service import quarantine_service

            threat_counter_store.quarantined_files = (
                quarantine_service.get_stats().active_count
            )
        except Exception:
            pass
        threat_counter_store.mark_scan_complete()

    def _compute_stats(self) -> ThreatStatsResponse:
        now = datetime.now(timezone.utc)
        active_cutoff = (now - timedelta(hours=ACTIVE_THREAT_HOURS)).isoformat()
        day_cutoff = (now - timedelta(hours=24)).isoformat()

        with self._db_lock:
            conn = self._connect()
            try:
                total = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs"
                ).fetchone()[0]
                critical = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs WHERE severity = ?",
                    (ThreatSeverity.CRITICAL.value,),
                ).fetchone()[0]
                high = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs WHERE severity = ?",
                    (ThreatSeverity.HIGH.value,),
                ).fetchone()[0]
                medium = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs WHERE severity = ?",
                    (ThreatSeverity.MEDIUM.value,),
                ).fetchone()[0]
                low = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs WHERE severity = ?",
                    (ThreatSeverity.LOW.value,),
                ).fetchone()[0]
                active = conn.execute(
                    """
                    SELECT COUNT(*) FROM threat_logs
                    WHERE severity IN (?, ?) AND timestamp >= ?
                    """,
                    (
                        ThreatSeverity.CRITICAL.value,
                        ThreatSeverity.HIGH.value,
                        active_cutoff,
                    ),
                ).fetchone()[0]
                blocked = conn.execute(
                    """
                    SELECT COUNT(*) FROM threat_logs
                    WHERE status IN ('Blocked', 'Quarantined')
                    """
                ).fetchone()[0]
                last_24h = conn.execute(
                    "SELECT COUNT(*) FROM threat_logs WHERE timestamp >= ?",
                    (day_cutoff,),
                ).fetchone()[0]
                monitored = conn.execute(
                    """
                    SELECT COUNT(*) FROM threat_logs
                    WHERE severity IN (?, ?, ?)
                    """,
                    (
                        ThreatSeverity.CRITICAL.value,
                        ThreatSeverity.HIGH.value,
                        ThreatSeverity.MEDIUM.value,
                    ),
                ).fetchone()[0]
            finally:
                conn.close()

        if total > 0:
            detection_rate = min(100.0, round((monitored / total) * 100, 1))
        else:
            detection_rate = 100.0

        return ThreatStatsResponse(
            total_threats=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            active_threats=active,
            blocked_threats=blocked,
            events_last_24h=last_24h,
            detection_rate_percent=detection_rate,
            monitoring_active=self.monitoring_active,
            watched_paths=self.watched_paths,
        )

    def get_stats(self) -> ThreatStatsResponse:
        return self._compute_stats()

    def get_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        severity: str | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> ThreatLogListResponse:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        conditions: list[str] = []
        params: list[str] = []

        if severity and severity.lower() != "all":
            conditions.append("severity = ?")
            params.append(severity.lower())

        if category and category.lower() != "all":
            conditions.append("category = ?")
            params.append(category)

        if search:
            term = f"%{search.strip()}%"
            conditions.append(
                "(description LIKE ? OR file_path LIKE ? OR category LIKE ? OR process_name LIKE ?)"
            )
            params.extend([term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._db_lock:
            conn = self._connect()
            try:
                total = conn.execute(
                    f"SELECT COUNT(*) FROM threat_logs {where_clause}",
                    params,
                ).fetchone()[0]
                rows = conn.execute(
                    f"""
                    SELECT * FROM threat_logs {where_clause}
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ? OFFSET ?
                    """,
                    [*params, page_size, offset],
                ).fetchall()
            finally:
                conn.close()

        logs = [
            ThreatLogEntry(
                id=row["id"],
                timestamp=self._format_timestamp(row["timestamp"]),
                file_path=row["file_path"],
                event_type=row["event_type"],
                severity=row["severity"],
                category=row["category"],
                process_name=row["process_name"] or "",
                status=row["status"],
                description=row["description"],
            )
            for row in rows
        ]
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0

        return ThreatLogListResponse(
            logs=logs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages if total else 0,
        )

    def clear_logs(self) -> ThreatClearResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                count = conn.execute("SELECT COUNT(*) FROM threat_logs").fetchone()[0]
                conn.execute("DELETE FROM threat_logs")
                conn.commit()
            finally:
                conn.close()

        self._threat_logger.info("Threat logs cleared (%d entries)", count)
        self._sync_dashboard_counters()
        return ThreatClearResponse(cleared=count)

    async def get_logs_async(self, **kwargs) -> ThreatLogListResponse:
        return await asyncio.to_thread(lambda: self.get_logs(**kwargs))

    async def get_stats_async(self) -> ThreatStatsResponse:
        return await asyncio.to_thread(self.get_stats)

    async def clear_logs_async(self) -> ThreatClearResponse:
        return await asyncio.to_thread(self.clear_logs)

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return iso_timestamp


threat_log_service = ThreatLogService.get_instance()
