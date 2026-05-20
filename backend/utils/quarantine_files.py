import hashlib
import re
import uuid
from pathlib import Path

QUARANTINE_STORAGE_SUFFIX = ".quarantine"
MAX_FILENAME_LENGTH = 120


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return hex SHA-256 digest for a file on disk."""
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_quarantine_filename(original_name: str) -> str:
    """
    Produce a safe storage basename (no path separators, no reserved Windows chars).
    Executable extensions are neutralized in storage names.
    """
    name = Path(original_name).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not name:
        name = "unnamed_file"
    if len(name) > MAX_FILENAME_LENGTH:
        stem = Path(name).stem[: MAX_FILENAME_LENGTH - 20]
        suffix = Path(name).suffix[:10]
        name = f"{stem}{suffix}"

    lower = name.lower()
    dangerous = (".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".scr", ".com")
    for ext in dangerous:
        if lower.endswith(ext):
            name = f"{name}.bin"
            break
    return name


def build_storage_filename(item_id: int, original_name: str) -> str:
    """Unique on-disk name: {id}_{uuid}_{sanitized}.quarantine"""
    safe = sanitize_quarantine_filename(original_name)
    token = uuid.uuid4().hex[:8]
    return f"{item_id}_{token}_{safe}{QUARANTINE_STORAGE_SUFFIX}"


def verify_file_integrity(file_path: Path, expected_hash: str) -> bool:
    """Verify file matches expected SHA-256; empty expected hash skips check."""
    if not expected_hash:
        return file_path.is_file()
    if not file_path.is_file():
        return False
    try:
        return compute_sha256(file_path) == expected_hash.lower()
    except OSError:
        return False


def format_size_human(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
