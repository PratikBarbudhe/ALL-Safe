from typing import Any

from pydantic import BaseModel, Field, field_validator

CURRENT_SETTINGS_VERSION = 1


class SystemSettings(BaseModel):
    auto_start_monitoring: bool = True
    auto_start_with_windows: bool = False
    minimize_to_tray: bool = True
    background_monitoring: bool = True


class NotificationSettings(BaseModel):
    desktop_notifications: bool = True
    threat_notifications: bool = True
    scan_complete_notifications: bool = True
    update_notifications: bool = True
    weekly_reports: bool = False
    critical_alert_popups: bool = True
    sound_alerts: bool = False
    notification_retention_days: int = Field(default=30, ge=1, le=365)


class RansomwareConfigSettings(BaseModel):
    monitoring_enabled: bool = True
    auto_quarantine: bool = True
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high)$")
    protected_folders: list[str] = Field(default_factory=list)


class UsbSettings(BaseModel):
    monitoring_enabled: bool = True
    trusted_devices_only: bool = False
    alert_unknown_devices: bool = True
    auto_scan_on_connect: bool = True


class AiAnalysisSettings(BaseModel):
    auto_analysis: bool = True
    analysis_interval_seconds: int = Field(default=60, ge=10, le=600)
    risk_threshold: int = Field(default=60, ge=0, le=100)


class DashboardSettings(BaseModel):
    refresh_interval_ms: int = Field(default=5000, ge=1000, le=60000)
    chart_history_limit: int = Field(default=7, ge=3, le=30)


class QuarantineSettings(BaseModel):
    auto_quarantine_threats: bool = True
    confirm_before_restore: bool = True
    confirm_before_delete: bool = True


class LoggingSettings(BaseModel):
    log_retention_days: int = Field(default=30, ge=1, le=365)
    verbose_logging: bool = False


class ScanSettings(BaseModel):
    scan_archives: bool = True
    heuristic_analysis: bool = True


class UpdateSettings(BaseModel):
    automatic_updates: bool = True
    auto_update_threat_database: bool = True
    beta_updates: bool = False


class UiSettings(BaseModel):
    theme: str = Field(default="dark", pattern="^(dark|light|auto)$")
    accent_color: str = Field(default="#3B82F6")


class AdvancedSettings(BaseModel):
    debug_mode: bool = False
    send_anonymous_usage_data: bool = False


class AllSafeSettings(BaseModel):
    version: int = CURRENT_SETTINGS_VERSION
    system: SystemSettings = Field(default_factory=SystemSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    ransomware: RansomwareConfigSettings = Field(default_factory=RansomwareConfigSettings)
    usb: UsbSettings = Field(default_factory=UsbSettings)
    ai_analysis: AiAnalysisSettings = Field(default_factory=AiAnalysisSettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    quarantine: QuarantineSettings = Field(default_factory=QuarantineSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
    update: UpdateSettings = Field(default_factory=UpdateSettings)
    ui: UiSettings = Field(default_factory=UiSettings)
    advanced: AdvancedSettings = Field(default_factory=AdvancedSettings)


class SettingsUpdateRequest(BaseModel):
    """Partial update — only provided groups/fields are merged."""

    system: dict[str, Any] | None = None
    notifications: dict[str, Any] | None = None
    ransomware: dict[str, Any] | None = None
    usb: dict[str, Any] | None = None
    ai_analysis: dict[str, Any] | None = None
    dashboard: dict[str, Any] | None = None
    quarantine: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    scan: dict[str, Any] | None = None
    update: dict[str, Any] | None = None
    ui: dict[str, Any] | None = None
    advanced: dict[str, Any] | None = None


class SettingsResponse(BaseModel):
    settings: AllSafeSettings
    modified: bool = False
    last_saved_at: str


class SettingsGroupResponse(BaseModel):
    group: str
    data: dict[str, Any]


class SettingsActionResponse(BaseModel):
    status: str
    message: str
    settings: AllSafeSettings | None = None


class SettingsExportResponse(BaseModel):
    exported_at: str
    settings: AllSafeSettings


class SettingsImportRequest(BaseModel):
    settings: dict[str, Any]
