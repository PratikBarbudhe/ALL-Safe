import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Application settings (override via ALLSAFE_* environment variables)."""

    app_name: str = "AllSafe Security API"
    app_version: str = "1.0.0"
    debug: bool = field(
        default_factory=lambda: os.getenv("ALLSAFE_DEBUG", "false").lower()
        == "true"
    )

    host: str = field(
        default_factory=lambda: os.getenv("ALLSAFE_HOST", "127.0.0.1")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("ALLSAFE_PORT", "8000"))
    )

    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://tauri.localhost",
        "tauri://localhost",
    )

    cpu_sample_interval: float = field(
        default_factory=lambda: float(
            os.getenv("ALLSAFE_CPU_SAMPLE_INTERVAL", "0.1")
        )
    )

    process_limit: int = field(
        default_factory=lambda: int(os.getenv("ALLSAFE_PROCESS_LIMIT", "50"))
    )


settings = Settings()
