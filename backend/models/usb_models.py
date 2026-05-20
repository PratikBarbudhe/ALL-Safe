from pydantic import BaseModel, Field


class UsbDevice(BaseModel):
    device_id: str
    name: str
    manufacturer: str
    serial_number: str
    connected_time: str
    device_type: str
    status: str = Field(description="Connection status: connected")
    drive_letter: str = ""
    capacity_bytes: int = Field(default=0, ge=0)
    protection_status: str = Field(
        description="trusted | unknown | suspicious | blocked | recently_connected"
    )
    threat_count: int = Field(default=0, ge=0)
    threat_reasons: list[str] = Field(default_factory=list)
    is_duplicate: bool = False
    is_unauthorized: bool = False
    last_scan_time: str = ""


class UsbEvent(BaseModel):
    event_id: str
    device_id: str
    device_name: str
    event_type: str = Field(description="inserted | removed")
    timestamp: str
    drive_letter: str = ""
    protection_status: str = ""


class UsbDeviceListResponse(BaseModel):
    devices: list[UsbDevice]
    total_connected: int = Field(..., ge=0)
    safe_count: int = Field(..., ge=0)
    threat_count: int = Field(..., ge=0)
    scanning_count: int = Field(..., ge=0)


class UsbHistoryResponse(BaseModel):
    events: list[UsbEvent]
    total_events: int = Field(..., ge=0)
