import logging
import math
import os
import threading
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from utils.exceptions import RansomwareMonitorError

logger = logging.getLogger(__name__)

ENCRYPTED_EXTENSIONS = {
    ".encrypted",
    ".locked",
    ".crypt",
    ".enc",
    ".rsa",
    ".aes",
    ".lockbit",
    ".ryuk",
    ".zzz",
    ".micro",
}
SCRIPT_EXTENSIONS = {".ps1", ".vbs", ".bat", ".cmd", ".js", ".jse", ".wsf"}
EXECUTABLE_EXTENSIONS = {".exe", ".scr", ".com", ".msi"}
HIGH_RISK_DIRS = ("download", "appdata", "temp", "tmp")

SENSITIVITY_THRESHOLDS = {
    "low": {
        "mod_burst": 18,
        "rename_burst": 10,
        "write_burst": 12,
        "window": 15.0,
        "entropy": 7.8,
    },
    "medium": {
        "mod_burst": 10,
        "rename_burst": 6,
        "write_burst": 8,
        "window": 10.0,
        "entropy": 7.5,
    },
    "high": {
        "mod_burst": 6,
        "rename_burst": 4,
        "write_burst": 5,
        "window": 8.0,
        "entropy": 7.2,
    },
}


@dataclass
class RansomwareDetection:
    file_path: str
    event_type: str
    severity: str
    threat_name: str
    description: str
    heuristic_type: str
    folder_path: str


RansomwareCallback = Callable[[RansomwareDetection], None]


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


class _RansomwareEventHandler(FileSystemEventHandler):
    """Heuristic ransomware behavior detection on protected user folders."""

    def __init__(
        self,
        on_detection: RansomwareCallback,
        protected_roots: list[Path],
        sensitivity: str = "medium",
    ) -> None:
        super().__init__()
        self._on_detection = on_detection
        self._protected_roots = [str(p.resolve()).lower() for p in protected_roots]
        self._sensitivity = sensitivity if sensitivity in SENSITIVITY_THRESHOLDS else "medium"
        self._lock = threading.Lock()
        self._mod_events: dict[str, deque[float]] = defaultdict(deque)
        self._rename_events: dict[str, deque[tuple[float, str]]] = defaultdict(deque)
        self._write_events: dict[str, deque[float]] = defaultdict(deque)
        self._recent_alerts: set[str] = set()

    def set_sensitivity(self, sensitivity: str) -> None:
        if sensitivity in SENSITIVITY_THRESHOLDS:
            self._sensitivity = sensitivity

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._analyze(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._analyze(event.src_path, "modified")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        dest = getattr(event, "dest_path", None) or event.src_path
        path = Path(dest)
        if self._is_protected(path):
            folder_key = self._folder_key(path)
            self._track_rename(dest, getattr(event, "src_path", ""))
            self._check_rename_burst(folder_key, dest)
        self._analyze(dest, "renamed")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._check_folder_burst(event.src_path, "mass_delete", "deleted")

    def _analyze(self, file_path: str, event_type: str) -> None:
        path = Path(file_path)
        if not self._is_protected(path):
            return

        ext = path.suffix.lower()
        parent_lower = str(path.parent).lower()
        folder_key = self._folder_key(path)

        if ext in ENCRYPTED_EXTENSIONS:
            self._emit(
                file_path,
                event_type,
                "critical",
                "Ransomware.EncryptedExtension",
                f"Ransomware-like extension detected: {path.name}",
                "encrypted_extension",
                folder_key,
            )
            return

        if event_type == "created" and ext in EXECUTABLE_EXTENSIONS:
            if any(marker in parent_lower for marker in HIGH_RISK_DIRS):
                self._emit(
                    file_path,
                    event_type,
                    "high",
                    "Ransomware.SuspiciousExecutable",
                    f"Executable created in high-risk folder: {path.name}",
                    "suspicious_executable",
                    folder_key,
                )

        if event_type == "created" and ext in SCRIPT_EXTENSIONS:
            self._track_write(folder_key, file_path)
            self._check_script_burst(folder_key, file_path, event_type)

        if event_type in ("modified", "created"):
            self._track_modification(folder_key, file_path)
            self._check_modification_burst(folder_key, file_path, event_type)
            self._check_entropy(path, file_path, event_type, folder_key)

        if event_type in ("modified", "created"):
            self._track_write(folder_key, file_path)
            self._check_write_burst(folder_key, file_path, event_type)

    def _emit(
        self,
        file_path: str,
        event_type: str,
        severity: str,
        threat_name: str,
        description: str,
        heuristic_type: str,
        folder_path: str,
    ) -> None:
        alert_key = f"{heuristic_type}:{folder_path}"
        with self._lock:
            if alert_key in self._recent_alerts:
                return
            self._recent_alerts.add(alert_key)
            if len(self._recent_alerts) > 300:
                self._recent_alerts.clear()

        self._on_detection(
            RansomwareDetection(
                file_path=file_path,
                event_type=event_type,
                severity=severity,
                threat_name=threat_name,
                description=description,
                heuristic_type=heuristic_type,
                folder_path=folder_path,
            )
        )

    def _is_protected(self, path: Path) -> bool:
        try:
            resolved = str(path.resolve()).lower()
        except OSError:
            resolved = str(path).lower()
        return any(
            resolved.startswith(root + os.sep) or resolved == root
            for root in self._protected_roots
        )

    @staticmethod
    def _folder_key(path: Path) -> str:
        return str(path.parent.resolve()).lower()

    def _thresholds(self) -> dict:
        return SENSITIVITY_THRESHOLDS[self._sensitivity]

    def _track_modification(self, folder_key: str, file_path: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._mod_events[folder_key].append(now)
            self._trim_deque(self._mod_events[folder_key], now)

    def _track_rename(self, dest_path: str, src_path: str) -> None:
        path = Path(dest_path)
        if not self._is_protected(path):
            return
        folder_key = self._folder_key(path)
        now = time.monotonic()
        with self._lock:
            self._rename_events[folder_key].append((now, dest_path))
            while self._rename_events[folder_key] and now - self._rename_events[folder_key][0][0] > self._thresholds()["window"]:
                self._rename_events[folder_key].popleft()

    def _track_write(self, folder_key: str, file_path: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._write_events[folder_key].append(now)
            self._trim_deque(self._write_events[folder_key], now)

    def _trim_deque(self, dq: deque, now: float) -> None:
        window = self._thresholds()["window"]
        while dq and now - dq[0] > window:
            dq.popleft()

    def _check_modification_burst(
        self, folder_key: str, file_path: str, event_type: str
    ) -> None:
        thresholds = self._thresholds()
        with self._lock:
            count = len(self._mod_events[folder_key])
        if count >= thresholds["mod_burst"]:
            self._emit(
                file_path,
                event_type,
                "critical",
                "Ransomware.RapidModification",
                f"Rapid modification burst in protected folder ({count} events)",
                "rapid_modification",
                folder_key,
            )

    def _check_rename_burst(self, folder_key: str, file_path: str) -> None:
        thresholds = self._thresholds()
        with self._lock:
            count = len(self._rename_events[folder_key])
        if count >= thresholds["rename_burst"]:
            self._emit(
                file_path,
                "renamed",
                "critical",
                "Ransomware.MassRename",
                f"Mass rename activity detected ({count} renames)",
                "mass_rename",
                folder_key,
            )

    def _check_write_burst(
        self, folder_key: str, file_path: str, event_type: str
    ) -> None:
        thresholds = self._thresholds()
        with self._lock:
            count = len(self._write_events[folder_key])
        if count >= thresholds["write_burst"]:
            self._emit(
                file_path,
                event_type,
                "high",
                "Ransomware.WriteBurst",
                f"Repeated write burst in protected folder ({count} writes)",
                "write_burst",
                folder_key,
            )

    def _check_script_burst(
        self, folder_key: str, file_path: str, event_type: str
    ) -> None:
        thresholds = self._thresholds()
        path = Path(file_path)
        if path.suffix.lower() not in SCRIPT_EXTENSIONS:
            return
        with self._lock:
            count = len(self._write_events[folder_key])
        script_threshold = max(3, thresholds["write_burst"] - 2)
        if count >= script_threshold:
            self._emit(
                file_path,
                event_type,
                "high",
                "Ransomware.ScriptBurst",
                f"Script-driven modification burst: {path.name}",
                "script_burst",
                folder_key,
            )

    def _check_folder_burst(
        self, file_path: str, heuristic: str, event_type: str
    ) -> None:
        path = Path(file_path)
        if not self._is_protected(path):
            return
        folder_key = self._folder_key(path)
        self._track_modification(folder_key, file_path)
        thresholds = self._thresholds()
        with self._lock:
            count = len(self._mod_events[folder_key])
        if count >= thresholds["mod_burst"]:
            self._emit(
                file_path,
                event_type,
                "high",
                "Ransomware.MassDelete",
                f"Mass delete activity in protected folder ({count} signals)",
                heuristic,
                folder_key,
            )

    def _check_entropy(
        self, path: Path, file_path: str, event_type: str, folder_key: str
    ) -> None:
        if not path.is_file() or path.stat().st_size < 256:
            return
        try:
            with path.open("rb") as handle:
                sample = handle.read(4096)
        except OSError:
            return
        entropy = shannon_entropy(sample)
        if entropy >= self._thresholds()["entropy"]:
            self._emit(
                file_path,
                event_type,
                "high",
                "Ransomware.HighEntropy",
                f"High-entropy file change detected (entropy={entropy:.2f})",
                "high_entropy",
                folder_key,
            )


class RansomwareMonitor:
    """Dedicated watchdog observer for ransomware heuristics."""

    def __init__(self, on_detection: RansomwareCallback) -> None:
        self._on_detection = on_detection
        self._observer: Observer | None = None
        self._handler: _RansomwareEventHandler | None = None
        self._watched_paths: list[str] = []
        self._lock = threading.Lock()

    @staticmethod
    def resolve_default_folders() -> list[Path]:
        home = Path.home()
        candidates = [
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "Pictures",
        ]
        paths: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
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

    def start(
        self,
        protected_folders: list[str] | None = None,
        sensitivity: str = "medium",
    ) -> list[str]:
        with self._lock:
            if self._observer and self._observer.is_alive():
                if self._handler:
                    self._handler.set_sensitivity(sensitivity)
                return list(self._watched_paths)

            if protected_folders:
                roots = []
                for folder in protected_folders:
                    try:
                        p = Path(folder).resolve()
                        if p.exists():
                            roots.append(p)
                    except OSError:
                        continue
            else:
                roots = self.resolve_default_folders()

            if not roots:
                raise RansomwareMonitorError(
                    "No valid protected folders for ransomware monitoring"
                )

            self._handler = _RansomwareEventHandler(
                self._on_detection, roots, sensitivity
            )
            self._observer = Observer()
            started: list[str] = []

            for path in roots:
                try:
                    self._observer.schedule(
                        self._handler, str(path), recursive=True
                    )
                    started.append(str(path))
                    logger.info("Ransomware monitor watching: %s", path)
                except OSError as exc:
                    logger.warning("Could not watch %s: %s", path, exc)

            if not started:
                raise RansomwareMonitorError("Failed to schedule ransomware watches")

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
                    logger.warning("Error stopping ransomware observer: %s", exc)
                finally:
                    self._observer = None
            self._handler = None
            self._watched_paths = []

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    @property
    def watched_paths(self) -> list[str]:
        return list(self._watched_paths)
