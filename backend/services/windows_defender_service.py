import asyncio
import logging
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from models.windows_security_models import (
    DefenderStatusResponse,
    FirewallProfileStatus,
    FirewallStatusResponse,
    SystemProtectionResponse,
    WindowsSecurityActionResponse,
    WindowsSecurityStatusResponse,
)
from utils.exceptions import WindowsSecurityServiceError
from utils.powershell_runner import run_powershell, run_powershell_bool, run_powershell_json

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = BACKEND_ROOT / "logs" / "windows_security.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
CACHE_TTL_SECONDS = 45


def _status_from_flags(
    *,
    available: bool,
    primary_on: bool,
    secondary_on: bool | None = None,
) -> str:
    if not available:
        return "unavailable"
    if primary_on and (secondary_on is None or secondary_on):
        return "protected"
    if primary_on or (secondary_on is True):
        return "attention_needed"
    return "disabled"


class WindowsDefenderService:
    """Native Windows Defender, Firewall, and Security Center integration."""

    _instance: "WindowsDefenderService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._cache_lock = threading.Lock()
        self._cached_status: WindowsSecurityStatusResponse | None = None
        self._cached_at: float = 0.0
        self._event_logger = self._configure_logger()

    @classmethod
    def get_instance(cls) -> "WindowsDefenderService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        sec_logger = logging.getLogger("allsafe.windows_security")
        if not sec_logger.handlers:
            handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            sec_logger.addHandler(handler)
            sec_logger.setLevel(logging.INFO)
            sec_logger.propagate = False
        return sec_logger

    def _log(self, message: str, level: int = logging.INFO) -> None:
        self._event_logger.log(level, message)

    @staticmethod
    def _format_ps_datetime(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text or text.startswith("0001"):
            return ""
        try:
            if text.endswith("Z"):
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return text

    def _collect_defender(self) -> DefenderStatusResponse:
        script = (
            "try { "
            "$s = Get-MpComputerStatus -ErrorAction Stop; "
            "$p = Get-MpPreference -ErrorAction SilentlyContinue; "
            "[PSCustomObject]@{ "
            "RealTimeProtectionEnabled = $s.RealTimeProtectionEnabled; "
            "AntivirusEnabled = $s.AntivirusEnabled; "
            "AntispywareEnabled = $s.AntispywareEnabled; "
            "AMServiceEnabled = $s.AMServiceEnabled; "
            "AMEngineVersion = $s.AMEngineVersion; "
            "AntivirusSignatureVersion = $s.AntivirusSignatureVersion; "
            "AntispywareSignatureVersion = $s.AntispywareSignatureVersion; "
            "QuickScanStartTime = $s.QuickScanStartTime; "
            "FullScanStartTime = $s.FullScanStartTime; "
            "QuickScanEndTime = $s.QuickScanEndTime; "
            "IsTamperProtected = $(if ($p) { $p.IsTamperProtected } else { $null }); "
            "ComputerState = $s.ComputerState "
            "} | ConvertTo-Json -Compress "
            "} catch { '{}' }"
        )
        data = run_powershell_json(script)
        if not data:
            return DefenderStatusResponse(available=False, status="unavailable")

        realtime = bool(data.get("RealTimeProtectionEnabled"))
        av = bool(data.get("AntivirusEnabled", data.get("AMServiceEnabled")))
        antispyware = bool(data.get("AntispywareEnabled"))
        service = bool(data.get("AMServiceEnabled"))
        tamper = data.get("IsTamperProtected")
        tamper_bool = bool(tamper) if tamper is not None else None

        last_quick = self._format_ps_datetime(
            data.get("QuickScanEndTime") or data.get("QuickScanStartTime")
        )
        last_full = self._format_ps_datetime(data.get("FullScanStartTime"))

        quick_age = None
        raw_quick = data.get("QuickScanEndTime") or data.get("QuickScanStartTime")
        if raw_quick:
            try:
                text = str(raw_quick).replace("Z", "+00:00")
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                quick_age = round(
                    (datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1
                )
            except ValueError:
                pass

        computer_state = str(data.get("ComputerState", ""))
        threat_protection = "healthy" if realtime and av else "at_risk"
        if computer_state:
            threat_protection = computer_state.lower()

        status = _status_from_flags(
            available=True,
            primary_on=realtime and av,
            secondary_on=service,
        )

        return DefenderStatusResponse(
            available=True,
            status=status,
            realtime_protection=realtime,
            antivirus_enabled=av,
            antispyware_enabled=antispyware,
            service_running=service,
            engine_version=str(data.get("AMEngineVersion", "")),
            antivirus_signature_version=str(
                data.get("AntivirusSignatureVersion", "")
            ),
            antispyware_signature_version=str(
                data.get("AntispywareSignatureVersion", "")
            ),
            last_quick_scan=last_quick,
            last_full_scan=last_full,
            quick_scan_age_hours=quick_age,
            tamper_protection=tamper_bool,
            threat_protection=threat_protection,
        )

    def _collect_firewall(self) -> FirewallStatusResponse:
        script = (
            "Get-NetFirewallProfile -ErrorAction SilentlyContinue | "
            "Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction | "
            "ConvertTo-Json -Compress"
        )
        data = run_powershell_json(script)
        if not data:
            return FirewallStatusResponse(available=False, status="unavailable")

        profiles_raw = data if isinstance(data, list) else [data]
        profiles: list[FirewallProfileStatus] = []
        domain = private = public = False
        active = ""

        for item in profiles_raw:
            name = str(item.get("Name", ""))
            enabled = bool(item.get("Enabled"))
            profiles.append(
                FirewallProfileStatus(
                    name=name,
                    enabled=enabled,
                    default_inbound=str(item.get("DefaultInboundAction", "")),
                    default_outbound=str(item.get("DefaultOutboundAction", "")),
                )
            )
            lower = name.lower()
            if lower == "domain":
                domain = enabled
            elif lower == "private":
                private = enabled
            elif lower == "public":
                public = enabled
            if enabled and not active:
                active = name

        all_on = domain and private and public
        any_on = domain or private or public
        status = _status_from_flags(
            available=True,
            primary_on=all_on,
            secondary_on=any_on if not all_on else True,
        )

        return FirewallStatusResponse(
            available=True,
            status=status if any_on else "disabled",
            enabled=all_on,
            active_profile=active,
            domain_enabled=domain,
            private_enabled=private,
            public_enabled=public,
            profiles=profiles,
        )

    def _collect_system_protection(self) -> SystemProtectionResponse:
        smartscreen = run_powershell_bool(
            "(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer' "
            "-Name SmartScreenEnabled -ErrorAction SilentlyContinue).SmartScreenEnabled -eq 1"
        )
        uac = run_powershell_bool(
            "(Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' "
            "-Name EnableLUA -ErrorAction SilentlyContinue).EnableLUA -eq 1"
        )
        secure_boot = run_powershell_bool(
            "try { Confirm-SecureBootUEFI } catch { $false }"
        )
        tpm_data = run_powershell_json(
            "Get-Tpm -ErrorAction SilentlyContinue | "
            "Select-Object TpmPresent, TpmReady | ConvertTo-Json -Compress"
        )
        tpm_present = tpm_ready = None
        if isinstance(tpm_data, dict):
            tpm_present = bool(tpm_data.get("TpmPresent"))
            tpm_ready = bool(tpm_data.get("TpmReady"))

        health_script = (
            "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct "
            "-ErrorAction SilentlyContinue | "
            "Select-Object -First 1 displayName, productState | "
            "ConvertTo-Json -Compress"
        )
        health_data = run_powershell_json(health_script)
        health_label = ""
        if isinstance(health_data, dict):
            health_label = str(health_data.get("displayName", ""))

        flags = [v for v in (smartscreen, uac, secure_boot, tpm_ready) if v is not None]
        primary = all(v for v in flags if v is not None) if flags else False
        status = _status_from_flags(
            available=True,
            primary_on=primary,
            secondary_on=any(flags) if flags else None,
        )

        return SystemProtectionResponse(
            available=True,
            status=status,
            smartscreen_enabled=smartscreen,
            uac_enabled=uac,
            secure_boot_enabled=secure_boot,
            tpm_present=tpm_present,
            tpm_ready=tpm_ready,
            security_center_health=health_label or "Windows Security Center",
        )

    def get_full_status(self, *, force_refresh: bool = False) -> WindowsSecurityStatusResponse:
        import time

        now = time.monotonic()
        with self._cache_lock:
            if (
                not force_refresh
                and self._cached_status
                and now - self._cached_at < CACHE_TTL_SECONDS
            ):
                return self._cached_status

        defender = self._collect_defender()
        firewall = self._collect_firewall()
        system_protection = self._collect_system_protection()

        statuses = [
            defender.status,
            firewall.status,
            system_protection.status,
        ]
        if all(s == "unavailable" for s in statuses):
            overall = "unavailable"
        elif any(s == "disabled" for s in statuses):
            overall = "disabled"
        elif any(s == "attention_needed" for s in statuses):
            overall = "attention_needed"
        else:
            overall = "protected"

        result = WindowsSecurityStatusResponse(
            overall_status=overall,
            defender=defender,
            firewall=firewall,
            system_protection=system_protection,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._cache_lock:
            self._cached_status = result
            self._cached_at = now

        self._log(
            f"STATUS overall={overall} defender={defender.status} "
            f"firewall={firewall.status} rtp={defender.realtime_protection}"
        )
        return result

    def get_defender(self) -> DefenderStatusResponse:
        return self.get_full_status().defender

    def get_firewall(self) -> FirewallStatusResponse:
        return self.get_full_status().firewall

    def get_system_protection(self) -> SystemProtectionResponse:
        return self.get_full_status().system_protection

    def get_protection_summary(self) -> dict[str, bool]:
        """Compact booleans for dashboard overview."""
        status = self.get_full_status()
        return {
            "realtime_protection": status.defender.realtime_protection,
            "windows_defender": status.defender.antivirus_enabled
            and status.defender.service_running,
            "firewall": status.firewall.enabled,
        }

    def trigger_quick_scan(self) -> WindowsSecurityActionResponse:
        script = (
            "try { "
            "Start-MpScan -ScanType QuickScan -ErrorAction Stop; "
            "'started' "
            "} catch { $_.Exception.Message }"
        )
        ok, stdout, stderr = run_powershell(script, timeout=30)
        if ok and stdout.strip().lower() == "started":
            self._log("Defender quick scan started")
            with self._cache_lock:
                self._cached_at = 0.0
            return WindowsSecurityActionResponse(
                message="Windows Defender quick scan started",
                job_started=True,
            )
        detail = stderr or stdout or "Quick scan could not be started"
        self._log(f"Quick scan failed: {detail}", logging.WARNING)
        raise WindowsSecurityServiceError(detail)

    def update_signatures(self) -> WindowsSecurityActionResponse:
        script = (
            "try { "
            "Update-MpSignature -ErrorAction Stop; "
            "'updated' "
            "} catch { $_.Exception.Message }"
        )
        ok, stdout, stderr = run_powershell(script, timeout=120)
        if ok and "updated" in stdout.lower():
            self._log("Defender signatures updated")
            with self._cache_lock:
                self._cached_at = 0.0
            return WindowsSecurityActionResponse(
                message="Windows Defender signatures updated successfully",
                job_started=False,
            )
        detail = stderr or stdout or "Signature update failed"
        self._log(f"Signature update failed: {detail}", logging.WARNING)
        raise WindowsSecurityServiceError(detail)

    def calculate_security_score_adjustment(
        self, base_score: float, status: WindowsSecurityStatusResponse
    ) -> int:
        score = base_score
        if status.defender.status == "disabled":
            score -= 20
        elif status.defender.status == "attention_needed":
            score -= 10
        elif not status.defender.available:
            score -= 5

        if status.firewall.status == "disabled":
            score -= 15
        elif status.firewall.status == "attention_needed":
            score -= 8
        elif not status.firewall.available:
            score -= 5

        if status.system_protection.secure_boot_enabled is False:
            score -= 5
        if status.system_protection.tpm_ready is False:
            score -= 5

        return max(0, min(100, int(round(score))))

    async def get_full_status_async(
        self, *, force_refresh: bool = False
    ) -> WindowsSecurityStatusResponse:
        return await asyncio.to_thread(
            lambda: self.get_full_status(force_refresh=force_refresh)
        )

    async def get_defender_async(self) -> DefenderStatusResponse:
        return await asyncio.to_thread(self.get_defender)

    async def get_firewall_async(self) -> FirewallStatusResponse:
        return await asyncio.to_thread(self.get_firewall)

    async def get_system_protection_async(self) -> SystemProtectionResponse:
        return await asyncio.to_thread(self.get_system_protection)

    async def trigger_quick_scan_async(self) -> WindowsSecurityActionResponse:
        return await asyncio.to_thread(self.trigger_quick_scan)

    async def update_signatures_async(self) -> WindowsSecurityActionResponse:
        return await asyncio.to_thread(self.update_signatures)


windows_defender_service = WindowsDefenderService.get_instance()
