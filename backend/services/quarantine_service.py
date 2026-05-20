import asyncio
import json
import logging
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from models.quarantine_models import (
    QuarantineActionResponse,
    QuarantineAddRequest,
    QuarantineClearResponse,
    QuarantineItem,
    QuarantineItemListResponse,
    QuarantineStatsResponse,
)
from services.threat_counters import threat_counter_store
from utils.exceptions import QuarantineServiceError
from utils.quarantine_files import (
    build_storage_filename,
    compute_sha256,
    format_size_human,
    verify_file_integrity,
)

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
QUARANTINE_ROOT = BACKEND_ROOT / "quarantine"
FILES_DIR = QUARANTINE_ROOT / "files"
METADATA_DIR = QUARANTINE_ROOT / "metadata"
DB_PATH = DATA_DIR / "quarantine.db"
QUARANTINE_LOG_FILE = BACKEND_ROOT / "logs" / "quarantine_events.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

STATUS_QUARANTINED = "quarantined"
STATUS_RESTORED = "restored"
STATUS_DELETED = "deleted"


class QuarantineService:
    """Isolates suspicious files on disk with SQLite tracking and audit logging."""

    _instance: "QuarantineService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._db_lock = threading.Lock()
        self._quarantine_logger = self._configure_logger()
        self._ensure_directories()
        self._init_database()

    @classmethod
    def get_instance(cls) -> "QuarantineService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        QUARANTINE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        q_logger = logging.getLogger("allsafe.quarantine")
        if not q_logger.handlers:
            handler = RotatingFileHandler(
                QUARANTINE_LOG_FILE,
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
            q_logger.addHandler(handler)
            q_logger.setLevel(logging.INFO)
            q_logger.propagate = False
        return q_logger

    def _ensure_directories(self) -> None:
        FILES_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS quarantine_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_path TEXT NOT NULL,
                        quarantined_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        severity TEXT NOT NULL,
                        category TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        detected_at TEXT NOT NULL,
                        restored_at TEXT DEFAULT '',
                        deleted_at TEXT DEFAULT '',
                        status TEXT NOT NULL,
                        source_event_id INTEGER
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine_items(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_quarantine_detected ON quarantine_items(detected_at)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _log_audit(self, message: str, level: int = logging.INFO) -> None:
        self._quarantine_logger.log(level, message)

    def _record_threat_event(
        self,
        *,
        file_path: str,
        event_type: str,
        severity: str,
        category: str,
        status: str,
        description: str,
        source_event_id: int | None = None,
    ) -> None:
        from services.threat_log_service import threat_log_service

        try:
            threat_log_service.log_security_event(
                file_path=file_path,
                event_type=event_type,
                severity=severity,
                category=category,
                status=status,
                description=description,
            )
        except Exception:
            logger.exception("Failed to write threat log for quarantine action")
        if source_event_id:
            self._log_audit(f"linked_source_event={source_event_id}")

    def _sync_dashboard_counters(self) -> None:
        stats = self.get_stats()
        threat_counter_store.quarantined_files = stats.active_count
        threat_counter_store.mark_scan_complete()
        from services.threat_log_service import threat_log_service

        threat_log_service.sync_dashboard_counters()

    def _row_to_item(self, row: sqlite3.Row) -> QuarantineItem:
        return QuarantineItem(
            id=row["id"],
            original_path=row["original_path"],
            quarantined_path=row["quarantined_path"],
            file_name=row["file_name"],
            file_hash=row["file_hash"],
            file_size=row["file_size"],
            severity=row["severity"],
            category=row["category"],
            reason=row["reason"],
            detected_at=self._format_timestamp(row["detected_at"]),
            restored_at=row["restored_at"] or "",
            deleted_at=row["deleted_at"] or "",
            status=row["status"],
            source_event_id=row["source_event_id"],
        )

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        if not iso_timestamp:
            return ""
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return iso_timestamp

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_metadata(self, item: QuarantineItem) -> None:
        path = METADATA_DIR / f"{item.id}.json"
        payload = item.model_dump()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_metadata(self, item_id: int) -> dict | None:
        path = METADATA_DIR / f"{item_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _get_active_by_original_path(self, original_path: str) -> sqlite3.Row | None:
        with self._db_lock:
            conn = self._connect()
            try:
                return conn.execute(
                    """
                    SELECT * FROM quarantine_items
                    WHERE original_path = ? AND status = ?
                    """,
                    (original_path, STATUS_QUARANTINED),
                ).fetchone()
            finally:
                conn.close()

    def add_file(self, request: QuarantineAddRequest) -> QuarantineActionResponse:
        source = Path(request.file_path).resolve()
        if not source.is_file():
            raise QuarantineServiceError(f"File not found: {request.file_path}")

        original_path = str(source)
        existing = self._get_active_by_original_path(original_path)
        if existing:
            raise QuarantineServiceError(
                f"File is already quarantined (id={existing['id']})"
            )

        file_name = source.name
        file_size = source.stat().st_size
        severity = request.severity.lower().strip()
        if severity not in ("low", "medium", "high", "critical"):
            severity = "medium"

        detected_at = self._now_iso()
        temp_hash = ""

        with self._db_lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO quarantine_items (
                        original_path, quarantined_path, file_name, file_hash,
                        file_size, severity, category, reason, detected_at,
                        restored_at, deleted_at, status, source_event_id
                    ) VALUES (?, '', ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?)
                    """,
                    (
                        original_path,
                        file_name,
                        temp_hash,
                        file_size,
                        severity,
                        request.category,
                        request.reason,
                        detected_at,
                        STATUS_QUARANTINED,
                        request.source_event_id,
                    ),
                )
                conn.commit()
                item_id = cursor.lastrowid or 0
            finally:
                conn.close()

        storage_name = build_storage_filename(item_id, file_name)
        dest = FILES_DIR / storage_name

        try:
            shutil.move(str(source), str(dest))
        except OSError as exc:
            self._delete_db_row(item_id)
            raise QuarantineServiceError(
                f"Failed to move file into quarantine: {exc}"
            ) from exc

        try:
            file_hash = compute_sha256(dest)
        except OSError as exc:
            dest.unlink(missing_ok=True)
            self._delete_db_row(item_id)
            raise QuarantineServiceError(
                f"Failed to hash quarantined file: {exc}"
            ) from exc

        quarantined_path = str(dest)
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE quarantine_items
                    SET quarantined_path = ?, file_hash = ?
                    WHERE id = ?
                    """,
                    (quarantined_path, file_hash, item_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM quarantine_items WHERE id = ?", (item_id,)
                ).fetchone()
            finally:
                conn.close()

        item = self._row_to_item(row)
        self._write_metadata(item)
        self._log_audit(
            f"QUARANTINED id={item.id} name={item.file_name} hash={file_hash[:12]}..."
        )
        self._record_threat_event(
            file_path=original_path,
            event_type="quarantined",
            severity=severity,
            category=request.category,
            status="Quarantined",
            description=f"File quarantined: {file_name} — {request.reason}",
            source_event_id=request.source_event_id,
        )
        self._sync_dashboard_counters()
        return QuarantineActionResponse(
            message=f"Quarantined {file_name} ({format_size_human(file_size)})",
            item=item,
        )

    def add_uploaded_file(
        self,
        *,
        upload_path: Path,
        original_filename: str,
        reason: str = "Manual upload quarantine test",
        severity: str = "medium",
        category: str = "File Activity",
    ) -> QuarantineActionResponse:
        """Quarantine a file already staged on disk (from multipart upload)."""
        return self.add_file(
            QuarantineAddRequest(
                file_path=str(upload_path.resolve()),
                reason=reason,
                severity=severity,
                category=category,
            )
        )

    def list_items(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        search: str | None = None,
    ) -> QuarantineItemListResponse:
        conditions: list[str] = []
        params: list[str | int] = []

        if status and status.lower() != "all":
            conditions.append("status = ?")
            params.append(status.lower())
        else:
            conditions.append("status = ?")
            params.append(STATUS_QUARANTINED)

        if severity and severity.lower() != "all":
            conditions.append("severity = ?")
            params.append(severity.lower())

        if search:
            term = f"%{search.strip()}%"
            conditions.append(
                "(file_name LIKE ? OR original_path LIKE ? OR reason LIKE ? OR category LIKE ?)"
            )
            params.extend([term, term, term, term])

        where_clause = f"WHERE {' AND '.join(conditions)}"

        with self._db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    f"""
                    SELECT * FROM quarantine_items {where_clause}
                    ORDER BY detected_at DESC, id DESC
                    """,
                    params,
                ).fetchall()
            finally:
                conn.close()

        items = [self._row_to_item(row) for row in rows]
        return QuarantineItemListResponse(items=items, total=len(items))

    def get_stats(self) -> QuarantineStatsResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                active = conn.execute(
                    "SELECT COUNT(*) FROM quarantine_items WHERE status = ?",
                    (STATUS_QUARANTINED,),
                ).fetchone()[0]
                critical = conn.execute(
                    """
                    SELECT COUNT(*) FROM quarantine_items
                    WHERE status = ? AND severity = ?
                    """,
                    (STATUS_QUARANTINED, "critical"),
                ).fetchone()[0]
                total_size = conn.execute(
                    """
                    SELECT COALESCE(SUM(file_size), 0) FROM quarantine_items
                    WHERE status = ?
                    """,
                    (STATUS_QUARANTINED,),
                ).fetchone()[0]
                total_ever = conn.execute(
                    "SELECT COUNT(*) FROM quarantine_items"
                ).fetchone()[0]
            finally:
                conn.close()

        return QuarantineStatsResponse(
            active_count=active,
            critical_count=critical,
            total_size_bytes=total_size,
            total_quarantined_ever=total_ever,
        )

    def get_item(self, item_id: int) -> QuarantineItem:
        with self._db_lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM quarantine_items WHERE id = ?", (item_id,)
                ).fetchone()
            finally:
                conn.close()
        if not row:
            raise QuarantineServiceError(f"Quarantine item {item_id} not found")
        return self._row_to_item(row)

    def restore_item(self, item_id: int) -> QuarantineActionResponse:
        item = self.get_item(item_id)
        if item.status != STATUS_QUARANTINED:
            raise QuarantineServiceError(
                f"Item {item_id} cannot be restored (status={item.status})"
            )

        stored = Path(item.quarantined_path)
        if not stored.is_file():
            raise QuarantineServiceError("Quarantined file missing on disk")

        if not verify_file_integrity(stored, item.file_hash):
            raise QuarantineServiceError(
                "Quarantined file failed integrity check — restore aborted"
            )

        dest = Path(item.original_path)
        if dest.exists():
            raise QuarantineServiceError(
                f"Cannot restore: file already exists at {item.original_path}"
            )

        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(stored), str(dest))
        except OSError as exc:
            raise QuarantineServiceError(f"Restore failed: {exc}") from exc

        restored_at = self._now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE quarantine_items
                    SET status = ?, restored_at = ?, quarantined_path = ''
                    WHERE id = ?
                    """,
                    (STATUS_RESTORED, restored_at, item_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM quarantine_items WHERE id = ?", (item_id,)
                ).fetchone()
            finally:
                conn.close()

        updated = self._row_to_item(row)
        meta_path = METADATA_DIR / f"{item_id}.json"
        if meta_path.exists():
            meta_path.unlink(missing_ok=True)

        self._log_audit(f"RESTORED id={item_id} to={dest}")
        self._record_threat_event(
            file_path=str(dest),
            event_type="restored",
            severity=item.severity,
            category=item.category,
            status="Logged",
            description=f"File restored from quarantine: {item.file_name}",
            source_event_id=item.source_event_id,
        )
        self._sync_dashboard_counters()
        return QuarantineActionResponse(
            message=f"Restored {item.file_name} to {dest.parent}",
            item=updated,
        )

    def delete_item(self, item_id: int) -> QuarantineActionResponse:
        item = self.get_item(item_id)
        if item.status == STATUS_DELETED:
            raise QuarantineServiceError(f"Item {item_id} is already deleted")

        stored = Path(item.quarantined_path) if item.quarantined_path else None
        if stored and stored.is_file():
            try:
                stored.unlink()
            except OSError as exc:
                raise QuarantineServiceError(
                    f"Failed to delete quarantined file: {exc}"
                ) from exc

        deleted_at = self._now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE quarantine_items
                    SET status = ?, deleted_at = ?, quarantined_path = ''
                    WHERE id = ?
                    """,
                    (STATUS_DELETED, deleted_at, item_id),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM quarantine_items WHERE id = ?", (item_id,)
                ).fetchone()
            finally:
                conn.close()

        updated = self._row_to_item(row)
        meta_path = METADATA_DIR / f"{item_id}.json"
        meta_path.unlink(missing_ok=True)

        self._log_audit(f"DELETED id={item_id} name={item.file_name}")
        self._record_threat_event(
            file_path=item.original_path,
            event_type="deleted",
            severity=item.severity,
            category=item.category,
            status="Blocked",
            description=f"Quarantined file permanently deleted: {item.file_name}",
            source_event_id=item.source_event_id,
        )
        self._sync_dashboard_counters()
        return QuarantineActionResponse(
            message=f"Permanently deleted {item.file_name}",
            item=updated,
        )

    def clear_all(self) -> QuarantineClearResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM quarantine_items WHERE status = ?",
                    (STATUS_QUARANTINED,),
                ).fetchall()
            finally:
                conn.close()

        cleared = 0
        for row in rows:
            try:
                self.delete_item(row["id"])
                cleared += 1
            except QuarantineServiceError as exc:
                self._log_audit(f"CLEAR_SKIP id={row['id']}: {exc}", logging.WARNING)

        self._log_audit(f"CLEAR_ALL removed={cleared}")
        self._sync_dashboard_counters()
        return QuarantineClearResponse(cleared=cleared)

    def _delete_db_row(self, item_id: int) -> None:
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM quarantine_items WHERE id = ?", (item_id,))
                conn.commit()
            finally:
                conn.close()

    async def add_file_async(self, request: QuarantineAddRequest) -> QuarantineActionResponse:
        return await asyncio.to_thread(self.add_file, request)

    async def list_items_async(self, **kwargs) -> QuarantineItemListResponse:
        return await asyncio.to_thread(lambda: self.list_items(**kwargs))

    async def get_stats_async(self) -> QuarantineStatsResponse:
        return await asyncio.to_thread(self.get_stats)

    async def restore_item_async(self, item_id: int) -> QuarantineActionResponse:
        return await asyncio.to_thread(self.restore_item, item_id)

    async def delete_item_async(self, item_id: int) -> QuarantineActionResponse:
        return await asyncio.to_thread(self.delete_item, item_id)

    async def clear_all_async(self) -> QuarantineClearResponse:
        return await asyncio.to_thread(self.clear_all)

    async def get_item_async(self, item_id: int) -> QuarantineItem:
        return await asyncio.to_thread(self.get_item, item_id)


quarantine_service = QuarantineService.get_instance()
