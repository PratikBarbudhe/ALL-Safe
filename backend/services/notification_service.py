"""Centralized notification and alerting for AllSafe security modules."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from models.notification_models import (
    ClearNotificationsResponse,
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationCategory,
    NotificationEmitRequest,
    NotificationEntry,
    NotificationListResponse,
    NotificationSeverity,
    UnreadCountResponse,
)
from utils.exceptions import NotificationServiceError
from utils.windows_notifications import show_toast

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "notifications.db"
NOTIFICATION_LOG_FILE = (
    Path(__file__).resolve().parent.parent / "logs" / "notification_events.log"
)
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

MAX_STORED_NOTIFICATIONS = 500
DEFAULT_RETENTION_DAYS = 30
DEDUPE_WINDOW_SECONDS = 60
TOAST_RATE_LIMIT_PER_MINUTE = 12
DEFAULT_LIST_LIMIT = 100


def map_threat_severity_to_notification(severity: str) -> str:
    mapping = {
        "low": NotificationSeverity.INFO.value,
        "medium": NotificationSeverity.WARNING.value,
        "high": NotificationSeverity.HIGH.value,
        "critical": NotificationSeverity.CRITICAL.value,
    }
    return mapping.get(severity.lower(), NotificationSeverity.INFO.value)


class NotificationService:
    """Persistent notification store with deduplication, retention, and Windows toasts."""

    _instance: NotificationService | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._db_lock = threading.Lock()
        self._event_logger = self._configure_logger()
        self._dedupe_cache: dict[str, float] = {}
        self._toast_timestamps: deque[float] = deque(maxlen=TOAST_RATE_LIMIT_PER_MINUTE * 2)
        self._desktop_notifications = True
        self._threat_notifications = True
        self._scan_notifications = True
        self._update_notifications = True
        self._critical_alert_popups = True
        self._sound_alerts = False
        self._retention_days = DEFAULT_RETENTION_DAYS
        self._init_database()

    def apply_preferences(self, prefs: Any) -> None:
        """Apply notification settings from centralized configuration."""
        self._desktop_notifications = prefs.desktop_notifications
        self._threat_notifications = prefs.threat_notifications
        self._scan_notifications = prefs.scan_complete_notifications
        self._update_notifications = prefs.update_notifications
        self._critical_alert_popups = prefs.critical_alert_popups
        self._sound_alerts = prefs.sound_alerts
        self._retention_days = prefs.notification_retention_days

    def _category_allowed(self, category: str) -> bool:
        if category in ("Threat Detection", "Ransomware", "USB Security", "Quarantine"):
            return self._threat_notifications
        if category == "Scan Results":
            return self._scan_notifications
        if category in ("Windows Security", "System Health"):
            return self._update_notifications or self._threat_notifications
        return self._desktop_notifications

    @classmethod
    def get_instance(cls) -> NotificationService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        NOTIFICATION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        event_logger = logging.getLogger("allsafe.notifications")
        if not event_logger.handlers:
            handler = RotatingFileHandler(
                NOTIFICATION_LOG_FILE,
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
            event_logger.addHandler(handler)
            event_logger.setLevel(logging.INFO)
            event_logger.propagate = False
        return event_logger

    def _init_database(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        category TEXT NOT NULL,
                        source_module TEXT NOT NULL,
                        read_status INTEGER NOT NULL DEFAULT 0,
                        action_required INTEGER NOT NULL DEFAULT 0,
                        metadata TEXT NOT NULL DEFAULT '{}'
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_notif_timestamp ON notifications(timestamp)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_notif_read ON notifications(read_status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_notif_severity ON notifications(severity)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def emit(
        self,
        *,
        title: str,
        message: str,
        severity: str = NotificationSeverity.INFO.value,
        category: str = NotificationCategory.SYSTEM_HEALTH.value,
        source_module: str = "system",
        action_required: bool = False,
        metadata: dict[str, Any] | None = None,
        show_toast: bool = True,
        dedupe_key: str | None = None,
    ) -> NotificationEntry | None:
        """Create a notification with deduplication and optional Windows toast."""
        severity = severity.lower()
        if severity not in {s.value for s in NotificationSeverity}:
            severity = NotificationSeverity.INFO.value

        key = dedupe_key or self._build_dedupe_key(
            category, source_module, title, message
        )
        if self._is_duplicate(key):
            return None

        if not self._category_allowed(category):
            return None

        timestamp = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        with self._db_lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO notifications (
                        timestamp, title, message, severity, category,
                        source_module, read_status, action_required, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        timestamp,
                        title,
                        message,
                        severity,
                        category,
                        source_module,
                        1 if action_required else 0,
                        meta_json,
                    ),
                )
                conn.commit()
                row_id = cursor.lastrowid or 0
                self._enforce_retention(conn)
                conn.commit()
            finally:
                conn.close()

        entry = NotificationEntry(
            id=row_id,
            timestamp=self._format_timestamp(timestamp),
            title=title,
            message=message,
            severity=severity,
            category=category,
            source_module=source_module,
            read_status=False,
            action_required=action_required,
            metadata=metadata or {},
        )

        self._event_logger.info(
            "%s | %s | %s | %s | %s",
            severity.upper(),
            category,
            source_module,
            title,
            message,
        )

        if (
            show_toast
            and self._desktop_notifications
            and self._can_show_toast()
        ):
            critical_popup = (
                severity == NotificationSeverity.CRITICAL.value
                and self._critical_alert_popups
            )
            show_toast(
                title=title,
                message=message,
                severity=severity,
                critical_popup=critical_popup,
            )

        return entry

    def emit_from_request(self, request: NotificationEmitRequest) -> NotificationEntry | None:
        return self.emit(
            title=request.title,
            message=request.message,
            severity=request.severity,
            category=request.category,
            source_module=request.source_module,
            action_required=request.action_required,
            metadata=request.metadata,
            show_toast=request.show_toast,
            dedupe_key=request.dedupe_key,
        )

    @staticmethod
    def _build_dedupe_key(
        category: str, source_module: str, title: str, message: str
    ) -> str:
        raw = f"{category}|{source_module}|{title}|{message}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_duplicate(self, key: str) -> bool:
        now = time.monotonic()
        expired = [
            k for k, ts in self._dedupe_cache.items() if now - ts > DEDUPE_WINDOW_SECONDS
        ]
        for k in expired:
            del self._dedupe_cache[k]
        if key in self._dedupe_cache:
            return True
        self._dedupe_cache[key] = now
        return False

    def _can_show_toast(self) -> bool:
        now = time.monotonic()
        while self._toast_timestamps and now - self._toast_timestamps[0] > 60:
            self._toast_timestamps.popleft()
        if len(self._toast_timestamps) >= TOAST_RATE_LIMIT_PER_MINUTE:
            return False
        self._toast_timestamps.append(now)
        return True

    def _enforce_retention(self, conn: sqlite3.Connection) -> None:
        retention_days = max(1, self._retention_days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        conn.execute("DELETE FROM notifications WHERE timestamp < ?", (cutoff,))
        count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        if count > MAX_STORED_NOTIFICATIONS:
            excess = count - MAX_STORED_NOTIFICATIONS
            conn.execute(
                """
                DELETE FROM notifications WHERE id IN (
                    SELECT id FROM notifications ORDER BY timestamp ASC, id ASC LIMIT ?
                )
                """,
                (excess,),
            )

    def list_notifications(
        self,
        *,
        limit: int = DEFAULT_LIST_LIMIT,
        unread_only: bool = False,
        category: str | None = None,
        severity: str | None = None,
    ) -> NotificationListResponse:
        limit = max(1, min(limit, 200))
        conditions: list[str] = []
        params: list[Any] = []

        if unread_only:
            conditions.append("read_status = 0")
        if category:
            conditions.append("category = ?")
            params.append(category)
        if severity:
            conditions.append("severity = ?")
            params.append(severity.lower())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._db_lock:
            conn = self._connect()
            try:
                total = conn.execute(
                    f"SELECT COUNT(*) FROM notifications {where_clause}",
                    params,
                ).fetchone()[0]
                unread = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE read_status = 0"
                ).fetchone()[0]
                rows = conn.execute(
                    f"""
                    SELECT * FROM notifications {where_clause}
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    [*params, limit],
                ).fetchall()
            finally:
                conn.close()

        notifications = [self._row_to_entry(row) for row in rows]
        return NotificationListResponse(
            notifications=notifications,
            total=total,
            unread_count=unread,
        )

    def get_unread_count(self) -> UnreadCountResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                unread = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE read_status = 0"
                ).fetchone()[0]
            finally:
                conn.close()
        return UnreadCountResponse(unread_count=unread)

    def mark_read(self, notification_id: int) -> MarkReadResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    "UPDATE notifications SET read_status = 1 WHERE id = ?",
                    (notification_id,),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT read_status FROM notifications WHERE id = ?",
                    (notification_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            raise NotificationServiceError(f"Notification {notification_id} not found")
        return MarkReadResponse(
            id=notification_id,
            read_status=bool(row["read_status"]),
        )

    def mark_all_read(self) -> MarkAllReadResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                updated = conn.execute(
                    "SELECT COUNT(*) FROM notifications WHERE read_status = 0"
                ).fetchone()[0]
                conn.execute("UPDATE notifications SET read_status = 1")
                conn.commit()
            finally:
                conn.close()
        return MarkAllReadResponse(updated=updated)

    def clear_all(self) -> ClearNotificationsResponse:
        with self._db_lock:
            conn = self._connect()
            try:
                count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
                conn.execute("DELETE FROM notifications")
                conn.commit()
            finally:
                conn.close()
        self._event_logger.info("Notifications cleared (%d entries)", count)
        return ClearNotificationsResponse(cleared=count)

    def _row_to_entry(self, row: sqlite3.Row) -> NotificationEntry:
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return NotificationEntry(
            id=row["id"],
            timestamp=self._format_timestamp(row["timestamp"]),
            title=row["title"],
            message=row["message"],
            severity=row["severity"],
            category=row["category"],
            source_module=row["source_module"],
            read_status=bool(row["read_status"]),
            action_required=bool(row["action_required"]),
            metadata=metadata,
        )

    async def list_notifications_async(self, **kwargs: Any) -> NotificationListResponse:
        return await asyncio.to_thread(lambda: self.list_notifications(**kwargs))

    async def get_unread_count_async(self) -> UnreadCountResponse:
        return await asyncio.to_thread(self.get_unread_count)

    async def mark_read_async(self, notification_id: int) -> MarkReadResponse:
        return await asyncio.to_thread(self.mark_read, notification_id)

    async def mark_all_read_async(self) -> MarkAllReadResponse:
        return await asyncio.to_thread(self.mark_all_read)

    async def clear_all_async(self) -> ClearNotificationsResponse:
        return await asyncio.to_thread(self.clear_all)

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return iso_timestamp


notification_service = NotificationService.get_instance()
