from pydantic import BaseModel, Field


class QuarantineAddRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path to file on local disk")
    reason: str = Field(default="Manual quarantine")
    severity: str = Field(default="medium", description="low | medium | high | critical")
    category: str = Field(default="File Activity")
    source_event_id: int | None = Field(default=None, ge=1)


class QuarantineItem(BaseModel):
    id: int
    original_path: str
    quarantined_path: str
    file_name: str
    file_hash: str
    file_size: int = Field(..., ge=0)
    severity: str
    category: str
    reason: str
    detected_at: str
    restored_at: str = ""
    deleted_at: str = ""
    status: str = Field(description="quarantined | restored | deleted")
    source_event_id: int | None = None


class QuarantineItemListResponse(BaseModel):
    items: list[QuarantineItem]
    total: int = Field(..., ge=0)


class QuarantineStatsResponse(BaseModel):
    active_count: int = Field(..., ge=0)
    critical_count: int = Field(..., ge=0)
    total_size_bytes: int = Field(..., ge=0)
    total_quarantined_ever: int = Field(..., ge=0)


class QuarantineActionResponse(BaseModel):
    status: str = "ok"
    message: str
    item: QuarantineItem | None = None


class QuarantineClearResponse(BaseModel):
    status: str = "ok"
    cleared: int = Field(..., ge=0)
