class AllSafeError(Exception):
    """Base exception for AllSafe backend errors."""


class SystemMonitorError(AllSafeError):
    """Raised when system metrics cannot be collected."""


class ProcessMonitorError(AllSafeError):
    """Raised when process metrics cannot be collected."""


class DashboardServiceError(AllSafeError):
    """Raised when dashboard data cannot be assembled."""


class UsbMonitorError(AllSafeError):
    """Raised when USB monitoring operations fail."""


class FileMonitorError(AllSafeError):
    """Raised when filesystem monitoring cannot start or run."""


class ThreatLogServiceError(AllSafeError):
    """Raised when threat logging or persistence fails."""


class QuarantineServiceError(AllSafeError):
    """Raised when quarantine operations fail."""


class RansomwareMonitorError(AllSafeError):
    """Raised when ransomware monitoring cannot start or run."""


class RansomwareServiceError(AllSafeError):
    """Raised when ransomware protection operations fail."""


class WindowsSecurityServiceError(AllSafeError):
    """Raised when Windows security integration operations fail."""
