from pydantic import BaseModel, Field


class RansomwareSettings(BaseModel):
    monitoring_enabled: bool = True
    auto_quarantine: bool = True
    sensitivity: str = Field(
        default="medium",
        description="low | medium | high",
    )
    protected_folders: list[str] = Field(default_factory=list)


class RansomwareSettingsUpdate(BaseModel):
    monitoring_enabled: bool | None = None
    auto_quarantine: bool | None = None
    sensitivity: str | None = None
    protected_folders: list[str] | None = None


class RansomwareEvent(BaseModel):
    id: int
    timestamp: str
    file_path: str
    event_type: str
    severity: str
    threat_name: str
    description: str
    status: str
    response_action: str
    quarantined: bool
    folder_path: str
    heuristic_type: str


class RansomwareEventListResponse(BaseModel):
    events: list[RansomwareEvent]
    total: int = Field(..., ge=0)


class RansomwareStatusResponse(BaseModel):
    protection_status: str = Field(
        description="Protected | Monitoring | Suspicious Activity | Threat Detected"
    )
    monitoring_active: bool
    monitoring_enabled: bool
    auto_quarantine: bool
    sensitivity: str
    protected_folders: list[str]
    attempts_blocked: int = Field(..., ge=0)
    protected_files_count: int = Field(..., ge=0)
    success_rate_percent: float = Field(..., ge=0, le=100)
    events_last_24h: int = Field(..., ge=0)
    critical_events_24h: int = Field(..., ge=0)
    layers: list[dict[str, str]] = Field(default_factory=list)


class RansomwareActionResponse(BaseModel):
    status: str = "ok"
    message: str
    monitoring_active: bool = False
