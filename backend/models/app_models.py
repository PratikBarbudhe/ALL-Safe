from pydantic import BaseModel, Field


class MonitorStatus(BaseModel):
    name: str
    running: bool
    healthy: bool
    detail: str = ""


class DatabaseStatus(BaseModel):
    threat_logs: bool
    quarantine: bool
    ransomware: bool
    notifications: bool
    ai_analysis: bool
    settings: bool


class AppStatusResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    background_mode: bool
    window_visible: bool = True
    monitors: list[MonitorStatus]
    databases: DatabaseStatus
    active_threads: int
    warmup_complete: bool
    last_watchdog_check: str


class PerformanceMetrics(BaseModel):
    process_cpu_percent: float
    process_memory_mb: float
    process_threads: int
    status: str
    anomalies: list[str] = Field(default_factory=list)
    poll_throttle_active: bool = False
    collected_at: str


class AppActionResponse(BaseModel):
    status: str
    message: str
