from pydantic import BaseModel, Field


class DefenderStatusResponse(BaseModel):
    available: bool = True
    status: str = Field(description="protected | attention_needed | disabled | unavailable")
    realtime_protection: bool = False
    antivirus_enabled: bool = False
    antispyware_enabled: bool = False
    service_running: bool = False
    engine_version: str = ""
    antivirus_signature_version: str = ""
    antispyware_signature_version: str = ""
    last_quick_scan: str = ""
    last_full_scan: str = ""
    quick_scan_age_hours: float | None = None
    tamper_protection: bool | None = None
    threat_protection: str = ""


class FirewallProfileStatus(BaseModel):
    name: str
    enabled: bool
    default_inbound: str = ""
    default_outbound: str = ""


class FirewallStatusResponse(BaseModel):
    available: bool = True
    status: str = "unavailable"
    enabled: bool = False
    active_profile: str = ""
    domain_enabled: bool = False
    private_enabled: bool = False
    public_enabled: bool = False
    profiles: list[FirewallProfileStatus] = Field(default_factory=list)


class SystemProtectionResponse(BaseModel):
    available: bool = True
    status: str = "unavailable"
    smartscreen_enabled: bool | None = None
    uac_enabled: bool | None = None
    secure_boot_enabled: bool | None = None
    tpm_present: bool | None = None
    tpm_ready: bool | None = None
    security_center_health: str = ""


class WindowsSecurityStatusResponse(BaseModel):
    overall_status: str = "unavailable"
    defender: DefenderStatusResponse
    firewall: FirewallStatusResponse
    system_protection: SystemProtectionResponse
    collected_at: str = ""


class WindowsSecurityActionResponse(BaseModel):
    status: str = "ok"
    message: str
    job_started: bool = False
