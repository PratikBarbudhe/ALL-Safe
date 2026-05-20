import logging
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from models.threat_models import (
    ThreatCategory,
    ThreatEventType,
    ThreatSeverity,
    ThreatStatus,
)
from utils.exceptions import FileMonitorError

logger = logging.getLogger(__name__)

EXECUTABLE_EXTENSIONS = {".exe", ".bat", ".ps1", ".vbs"}
SCRIPT_EXTENSIONS = {".ps1", ".vbs", ".bat", ".cmd", ".js", ".jse", ".wsf"}
SUSPICIOUS_EXTENSIONS = {
    ".scr",
    ".pif",
    ".hta",
    ".com",
    ".msi",
    ".dll",
    ".lnk",
    ".inf",
    ".reg",
    ".jar",
}
UNKNOWN_EXTENSIONS = {
    ".xyz",
    ".abc",
    ".encrypted",
    ".locked",
    ".crypt",
    ".enc",
}

RAPID_MOD_WINDOW_SECONDS = 10.0
RAPID_MOD_THRESHOLD = 5

ThreatEventCallback = Callable[
    [
        str,
        str,
        str,
        str,
        str,
        str,
        str,
        str,
    ],
    None,
]


class _AllSafeFileEventHandler(FileSystemEventHandler):
    """Classifies filesystem events and forwards security-relevant activity."""

    def __init__(self, on_threat_event: ThreatEventCallback) -> None:
        super().__init__()
        self._on_threat_event = on_threat_event
        self._modification_times: dict[str, deque[float]] = defaultdict(deque)
        self._burst_lock = threading.Lock()
        self._recent_bursts: set[str] = set()

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path, ThreatEventType.CREATED)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path, ThreatEventType.MODIFIED)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_event(event.src_path, ThreatEventType.DELETED)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", None) or event.src_path
        self._handle_event(dest, ThreatEventType.RENAMED, src_path=event.src_path)

    def _handle_event(
        self,
        file_path: str,
        event_type: ThreatEventType,
        src_path: str | None = None,
    ) -> None:
        try:
            normalized = str(Path(file_path).resolve())
        except (OSError, ValueError):
            normalized = file_path

        if self._check_rapid_modification(normalized, event_type):
            return

        classification = self._classify(
            normalized, event_type, src_path=src_path
        )
        if classification is None:
            return

        severity, category, status, description = classification
        self._on_threat_event(
            normalized,
            event_type.value,
            severity.value,
            category.value,
            "",
            status.value,
            description,
        )

    def _check_rapid_modification(
        self, file_path: str, event_type: ThreatEventType
    ) -> bool:
        if event_type != ThreatEventType.MODIFIED:
            return False

        now = time.monotonic()
        with self._burst_lock:
            times = self._modification_times[file_path]
            times.append(now)
            while times and now - times[0] > RAPID_MOD_WINDOW_SECONDS:
                times.popleft()

            if len(times) < RAPID_MOD_THRESHOLD:
                return False

            if file_path in self._recent_bursts:
                return True

            self._recent_bursts.add(file_path)
            if len(self._recent_bursts) > 500:
                self._recent_bursts.clear()

        name = Path(file_path).name
        self._on_threat_event(
            file_path,
            ThreatEventType.MODIFIED.value,
            ThreatSeverity.CRITICAL.value,
            ThreatCategory.RAPID_MODIFICATION.value,
            "",
            ThreatStatus.BLOCKED.value,
            f"Rapid modification burst detected on {name} "
            f"({RAPID_MOD_THRESHOLD}+ changes in {int(RAPID_MOD_WINDOW_SECONDS)}s)",
        )
        return True

    def _classify(
        self,
        file_path: str,
        event_type: ThreatEventType,
        src_path: str | None = None,
    ) -> tuple[ThreatSeverity, ThreatCategory, ThreatStatus, str] | None:
        path = Path(file_path)
        ext = path.suffix.lower()
        name = path.name
        parent_lower = str(path.parent).lower()
        in_temp = "temp" in parent_lower or "tmp" in parent_lower
        in_downloads = "download" in parent_lower

        if ext in EXECUTABLE_EXTENSIONS and event_type == ThreatEventType.CREATED:
            severity = ThreatSeverity.CRITICAL if in_temp or in_downloads else ThreatSeverity.HIGH
            category = ThreatCategory.SUSPICIOUS_EXECUTABLE
            status = ThreatStatus.BLOCKED if severity == ThreatSeverity.CRITICAL else ThreatStatus.DETECTED
            location = "temporary directory" if in_temp else "user folder"
            return (
                severity,
                category,
                status,
                f"Executable file created: {name} in {location}",
            )

        if ext in SCRIPT_EXTENSIONS:
            severity = ThreatSeverity.CRITICAL if in_temp else ThreatSeverity.HIGH
            category = ThreatCategory.SCRIPT_EXECUTION
            status = ThreatStatus.BLOCKED if in_temp else ThreatStatus.MONITORED
            return (
                severity,
                category,
                status,
                f"Script file {event_type.value}: {name}",
            )

        if ext in SUSPICIOUS_EXTENSIONS:
            return (
                ThreatSeverity.HIGH,
                ThreatCategory.SUSPICIOUS_EXECUTABLE,
                ThreatStatus.DETECTED,
                f"Suspicious file type ({ext}) {event_type.value}: {name}",
            )

        if ext in UNKNOWN_EXTENSIONS or (
            ext and ext not in {".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".zip", ".json", ".xml", ".html", ".css", ".md", ".log", ".csv", ".db", ".sqlite"}
            and event_type == ThreatEventType.CREATED
        ):
            if ext in {".xyz", ".abc", ".encrypted", ".locked", ".crypt", ".enc"}:
                return (
                    ThreatSeverity.MEDIUM,
                    ThreatCategory.UNKNOWN_FILE_TYPE,
                    ThreatStatus.MONITORED,
                    f"Unknown or suspicious extension created: {name}",
                )

        if event_type == ThreatEventType.RENAMED and src_path:
            old_ext = Path(src_path).suffix.lower()
            if ext in EXECUTABLE_EXTENSIONS or old_ext in EXECUTABLE_EXTENSIONS:
                return (
                    ThreatSeverity.MEDIUM,
                    ThreatCategory.FILE_ACTIVITY,
                    ThreatStatus.MONITORED,
                    f"Executable renamed: {Path(src_path).name} → {name}",
                )

        severity, status = self._severity_for_generic_event(event_type, in_temp)
        description = self._describe_event(event_type, name, src_path)
        return (
            severity,
            ThreatCategory.FILE_ACTIVITY,
            status,
            description,
        )

    @staticmethod
    def _severity_for_generic_event(
        event_type: ThreatEventType, in_temp: bool
    ) -> tuple[ThreatSeverity, ThreatStatus]:
        if event_type == ThreatEventType.DELETED:
            return ThreatSeverity.LOW, ThreatStatus.LOGGED
        if event_type == ThreatEventType.MODIFIED:
            return (
                ThreatSeverity.MEDIUM if in_temp else ThreatSeverity.LOW,
                ThreatStatus.MONITORED if in_temp else ThreatStatus.LOGGED,
            )
        if event_type == ThreatEventType.RENAMED:
            return ThreatSeverity.LOW, ThreatStatus.LOGGED
        return ThreatSeverity.LOW, ThreatStatus.LOGGED

    @staticmethod
    def _describe_event(
        event_type: ThreatEventType,
        name: str,
        src_path: str | None,
    ) -> str:
        if event_type == ThreatEventType.RENAMED and src_path:
            return f"File renamed: {Path(src_path).name} → {name}"
        return f"File {event_type.value}: {name}"


class FileMonitor:
    """Watchdog-based real-time filesystem monitor for user profile paths."""

    def __init__(self, on_threat_event: ThreatEventCallback) -> None:
        self._on_threat_event = on_threat_event
        self._observer: Observer | None = None
        self._handler: _AllSafeFileEventHandler | None = None
        self._watched_paths: list[str] = []
        self._lock = threading.Lock()

    @staticmethod
    def resolve_watch_paths() -> list[Path]:
        paths: list[Path] = []
        home = Path.home()
        candidates = [
            home / "Desktop",
            home / "Downloads",
            home / "Documents",
            Path(os.environ.get("TEMP", home / "AppData" / "Local" / "Temp")),
            Path(os.environ.get("TMP", "")),
        ]
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate:
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            key = str(resolved).lower()
            if key in seen or not resolved.exists():
                continue
            seen.add(key)
            paths.append(resolved)
        return paths

    def start(self) -> list[str]:
        with self._lock:
            if self._observer and self._observer.is_alive():
                return list(self._watched_paths)

            watch_paths = self.resolve_watch_paths()
            if not watch_paths:
                raise FileMonitorError("No valid directories available for file monitoring")

            self._handler = _AllSafeFileEventHandler(self._on_threat_event)
            self._observer = Observer()
            started: list[str] = []

            for path in watch_paths:
                try:
                    self._observer.schedule(
                        self._handler,
                        str(path),
                        recursive=True,
                    )
                    started.append(str(path))
                    logger.info("Watching directory: %s", path)
                except OSError as exc:
                    logger.warning("Could not watch %s: %s", path, exc)

            if not started:
                raise FileMonitorError("Failed to schedule any watch directories")

            self._observer.start()
            self._watched_paths = started
            return started

    def stop(self) -> None:
        with self._lock:
            if self._observer:
                try:
                    self._observer.stop()
                    self._observer.join(timeout=5)
                except Exception as exc:
                    logger.warning("Error stopping file observer: %s", exc)
                finally:
                    self._observer = None
            self._handler = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    @property
    def watched_paths(self) -> list[str]:
        return list(self._watched_paths)
