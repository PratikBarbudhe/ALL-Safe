from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ThreatCounterStore:
    """
    In-memory threat counters until dedicated threat/quarantine modules ship.
    Replace this store via dependency injection when persistence is added.
    """

    active_threats: int = 0
    blocked_threats: int = 0
    quarantined_files: int = 0
    last_scan_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def record_blocked(self, count: int = 1) -> None:
        self.blocked_threats += count

    def set_active_threats(self, count: int) -> None:
        self.active_threats = max(0, count)

    def quarantine(self, count: int = 1) -> None:
        self.quarantined_files += count
        self.last_scan_time = datetime.now(timezone.utc)

    def mark_scan_complete(self) -> None:
        self.last_scan_time = datetime.now(timezone.utc)


threat_counter_store = ThreatCounterStore()
