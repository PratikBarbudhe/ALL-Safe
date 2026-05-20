from enum import Enum

from pydantic import BaseModel, Field


class ThreatSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(str, Enum):
    FILE_ACTIVITY = "File Activity"
    SUSPICIOUS_EXECUTABLE = "Suspicious Executable"
    SCRIPT_EXECUTION = "Script Execution"
    RAPID_MODIFICATION = "Rapid Modification"
    UNKNOWN_FILE_TYPE = "Unknown File Type"


class ThreatEventType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MOVED = "moved"


class ThreatStatus(str, Enum):
    DETECTED = "Detected"
    MONITORED = "Monitored"
    BLOCKED = "Blocked"
    QUARANTINED = "Quarantined"
    LOGGED = "Logged"


class ThreatLogEntry(BaseModel):
    id: int
    timestamp: str
    file_path: str
    event_type: str
    severity: str
    category: str
    process_name: str = ""
    status: str
    description: str


class ThreatLogListResponse(BaseModel):
    logs: list[ThreatLogEntry]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)


class ThreatStatsResponse(BaseModel):
    total_threats: int = Field(..., ge=0)
    critical_count: int = Field(..., ge=0)
    high_count: int = Field(..., ge=0)
    medium_count: int = Field(..., ge=0)
    low_count: int = Field(..., ge=0)
    active_threats: int = Field(..., ge=0)
    blocked_threats: int = Field(..., ge=0)
    events_last_24h: int = Field(..., ge=0)
    detection_rate_percent: float = Field(..., ge=0, le=100)
    monitoring_active: bool = True
    watched_paths: list[str] = Field(default_factory=list)


class ThreatClearResponse(BaseModel):
    cleared: int = Field(..., ge=0)
    status: str = "ok"
