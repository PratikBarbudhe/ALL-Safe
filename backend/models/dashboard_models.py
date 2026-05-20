from pydantic import BaseModel, Field


class NetworkActivity(BaseModel):
    sent: int = Field(..., ge=0)
    received: int = Field(..., ge=0)


class ProtectionStatus(BaseModel):
    realtime_protection: bool
    firewall: bool
    windows_defender: bool


class DashboardOverviewResponse(BaseModel):
    system_health: str
    cpu_usage: float = Field(..., ge=0, le=100)
    ram_usage: float = Field(..., ge=0, le=100)
    disk_usage: float = Field(..., ge=0, le=100)
    network_activity: NetworkActivity
    running_processes: int = Field(..., ge=0)
    uptime: str
    active_threats: int = Field(..., ge=0)
    blocked_threats: int = Field(..., ge=0)
    quarantined_files: int = Field(..., ge=0)
    usb_devices_connected: int = Field(..., ge=0)
    last_scan_time: str
    protection_status: ProtectionStatus
    security_score: int = Field(..., ge=0, le=100)
    network_connections: int = Field(..., ge=0)
