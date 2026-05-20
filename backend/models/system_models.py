from pydantic import BaseModel, Field


class SystemStatsResponse(BaseModel):
    """Real-time system metrics returned by GET /system-stats."""

    cpu_usage: float = Field(
        ...,
        ge=0,
        le=100,
        description="CPU utilization percentage across all cores",
    )
    ram_usage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Physical memory utilization percentage",
    )
    disk_usage: float = Field(
        ...,
        ge=0,
        le=100,
        description="System drive disk space utilization percentage",
    )
    network_sent: int = Field(
        ...,
        ge=0,
        description="Total bytes sent since boot (all interfaces)",
    )
    network_received: int = Field(
        ...,
        ge=0,
        description="Total bytes received since boot (all interfaces)",
    )
    running_processes: int = Field(
        ...,
        ge=0,
        description="Number of currently running processes",
    )
    uptime: str = Field(
        ...,
        description="Human-readable system uptime since last boot",
    )
