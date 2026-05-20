from pydantic import BaseModel, Field


class ProcessInfo(BaseModel):
    pid: int = Field(..., ge=0)
    process_name: str
    cpu_percent: float = Field(..., ge=0)
    memory_percent: float = Field(..., ge=0)
    status: str
    username: str
    executable_path: str
    create_time: float = Field(
        ...,
        description="Process creation time as Unix epoch seconds",
    )


class ProcessListResponse(BaseModel):
    processes: list[ProcessInfo]
    total_processes: int = Field(
        ...,
        ge=0,
        description="Total running process count on the host",
    )
    system_memory_total_bytes: int = Field(
        ...,
        ge=0,
        description="Total physical memory for client-side MB conversion",
    )
