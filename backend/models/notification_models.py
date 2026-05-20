from enum import Enum

from pydantic import BaseModel, Field


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationCategory(str, Enum):
    THREAT_DETECTION = "Threat Detection"
    RANSOMWARE = "Ransomware"
    USB_SECURITY = "USB Security"
    QUARANTINE = "Quarantine"
    WINDOWS_SECURITY = "Windows Security"
    SYSTEM_HEALTH = "System Health"
    SCAN_RESULTS = "Scan Results"


class NotificationEntry(BaseModel):
    id: int
    timestamp: str
    title: str
    message: str
    severity: str
    category: str
    source_module: str
    read_status: bool
    action_required: bool
    metadata: dict = Field(default_factory=dict)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationEntry]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    id: int
    read_status: bool
    status: str = "ok"


class MarkAllReadResponse(BaseModel):
    updated: int
    status: str = "ok"


class ClearNotificationsResponse(BaseModel):
    cleared: int
    status: str = "ok"


class NotificationEmitRequest(BaseModel):
    title: str
    message: str
    severity: str = NotificationSeverity.INFO.value
    category: str = NotificationCategory.SYSTEM_HEALTH.value
    source_module: str = "system"
    action_required: bool = False
    metadata: dict = Field(default_factory=dict)
    show_toast: bool = True
    dedupe_key: str | None = None
