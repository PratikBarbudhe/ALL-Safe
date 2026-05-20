"""Local weighted security scoring and risk posture helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class SecurityContext:
    """Aggregated signals for local intelligence scoring."""

    cpu_usage: float = 0.0
    ram_usage: float = 0.0
    disk_usage: float = 0.0
    active_threats: int = 0
    blocked_threats: int = 0
    events_last_hour: int = 0
    events_last_24h: int = 0
    critical_threats_24h: int = 0
    high_threats_24h: int = 0
    ransomware_events_24h: int = 0
    ransomware_critical_24h: int = 0
    usb_events_hour: int = 0
    usb_suspicious_hour: int = 0
    quarantine_active: int = 0
    quarantine_critical: int = 0
    unread_critical_notifications: int = 0
    high_cpu_processes: int = 0
    dangerous_processes: int = 0
    defender_realtime: bool = True
    defender_antivirus: bool = True
    firewall_enabled: bool = True
    signature_age_hours: float | None = None
    realtime_protection: bool = True
    threat_categories_24h: dict[str, int] = field(default_factory=dict)
    hourly_threat_counts: list[int] = field(default_factory=list)
    previous_score: int | None = None


RISK_COLORS = {
    "low": "#10B981",
    "medium": "#F59E0B",
    "high": "#EF4444",
    "secure": "#10B981",
    "warning": "#F59E0B",
    "high_risk": "#F97316",
    "critical_risk": "#EF4444",
}


def determine_risk_posture(score: int) -> str:
    if score >= 80:
        return "secure"
    if score >= 60:
        return "warning"
    if score >= 40:
        return "high_risk"
    return "critical_risk"


def posture_label(posture: str) -> str:
    labels = {
        "secure": "Secure",
        "warning": "Warning",
        "high_risk": "High Risk",
        "critical_risk": "Critical Risk",
    }
    return labels.get(posture, "Unknown")


def score_summary_text(score: int, posture: str) -> str:
    if posture == "secure":
        return "Strong security posture with effective local protections"
    if posture == "warning":
        return "Elevated risk — review recommendations and recent alerts"
    if posture == "high_risk":
        return "High risk environment — immediate investigation recommended"
    return "Critical risk — active threats or protection gaps detected"


def score_to_risk_band(score: int) -> str:
    if score >= 75:
        return "low"
    if score >= 50:
        return "medium"
    return "high"


def calculate_overall_security_score(ctx: SecurityContext) -> int:
    score = 100.0
    score -= min(ctx.cpu_usage * 0.2, 15)
    score -= min(ctx.ram_usage * 0.15, 12)
    score -= min(ctx.disk_usage * 0.08, 8)
    score -= ctx.active_threats * 10
    score -= ctx.critical_threats_24h * 4
    score -= ctx.high_threats_24h * 2
    score -= ctx.ransomware_critical_24h * 8
    score -= min(ctx.ransomware_events_24h * 2, 12)
    score -= ctx.usb_suspicious_hour * 5
    score -= min(ctx.quarantine_critical * 3, 9)
    score -= ctx.unread_critical_notifications * 2
    score -= ctx.dangerous_processes * 4
    score -= min(ctx.high_cpu_processes, 3) * 2

    if not ctx.defender_realtime or not ctx.defender_antivirus:
        score -= 18
    if not ctx.firewall_enabled:
        score -= 15
    if not ctx.realtime_protection:
        score -= 10
    if ctx.signature_age_hours is not None and ctx.signature_age_hours > 72:
        score -= 12
    elif ctx.signature_age_hours is not None and ctx.signature_age_hours > 48:
        score -= 6

    if ctx.events_last_hour >= 10:
        score -= 8
    elif ctx.events_last_hour >= 5:
        score -= 4

    return max(0, min(100, int(round(score))))


def calculate_category_scores(ctx: SecurityContext) -> list[dict[str, Any]]:
    categories: list[dict[str, Any]] = []

    system_score = 100
    system_score -= min(int(ctx.cpu_usage * 0.3), 25)
    system_score -= min(int(ctx.ram_usage * 0.25), 20)
    system_score -= min(int(ctx.disk_usage * 0.1), 10)
    system_score = max(0, min(100, system_score))
    categories.append(
        {
            "category": "System Health",
            "score": system_score,
            "risk": score_to_risk_band(system_score),
            "summary": _system_summary(ctx),
        }
    )

    threat_score = 100
    threat_score -= ctx.active_threats * 12
    threat_score -= min(ctx.events_last_24h, 20)
    threat_score -= ctx.critical_threats_24h * 5
    threat_score = max(0, min(100, threat_score))
    categories.append(
        {
            "category": "Threat Intelligence",
            "score": threat_score,
            "risk": score_to_risk_band(threat_score),
            "summary": _threat_summary(ctx),
        }
    )

    rw_score = 100
    rw_score -= ctx.ransomware_events_24h * 8
    rw_score -= ctx.ransomware_critical_24h * 15
    rw_score = max(0, min(100, rw_score))
    categories.append(
        {
            "category": "Ransomware Activity",
            "score": rw_score,
            "risk": score_to_risk_band(rw_score),
            "summary": _ransomware_summary(ctx),
        }
    )

    usb_score = 100
    usb_score -= ctx.usb_suspicious_hour * 20
    usb_score -= max(0, ctx.usb_events_hour - 3) * 3
    usb_score = max(0, min(100, usb_score))
    categories.append(
        {
            "category": "USB Security",
            "score": usb_score,
            "risk": score_to_risk_band(usb_score),
            "summary": _usb_summary(ctx),
        }
    )

    proc_score = 100
    proc_score -= ctx.dangerous_processes * 15
    proc_score -= ctx.high_cpu_processes * 5
    proc_score = max(0, min(100, proc_score))
    categories.append(
        {
            "category": "Process Behavior",
            "score": proc_score,
            "risk": score_to_risk_band(proc_score),
            "summary": _process_summary(ctx),
        }
    )

    win_score = 100
    if not ctx.defender_realtime:
        win_score -= 25
    if not ctx.defender_antivirus:
        win_score -= 20
    if not ctx.firewall_enabled:
        win_score -= 20
    if ctx.signature_age_hours and ctx.signature_age_hours > 48:
        win_score -= 15
    win_score = max(0, min(100, win_score))
    categories.append(
        {
            "category": "Windows Protection",
            "score": win_score,
            "risk": score_to_risk_band(win_score),
            "summary": _windows_summary(ctx),
        }
    )

    q_score = 100
    q_score -= ctx.quarantine_active * 4
    q_score -= ctx.quarantine_critical * 10
    q_score = max(0, min(100, q_score))
    categories.append(
        {
            "category": "Quarantine Analysis",
            "score": q_score,
            "risk": score_to_risk_band(q_score),
            "summary": _quarantine_summary(ctx),
        }
    )

    return categories


def compute_threat_probability(ctx: SecurityContext) -> list[dict[str, Any]]:
    total_weight = (
        ctx.events_last_24h
        + ctx.ransomware_events_24h * 2
        + ctx.usb_suspicious_hour * 3
        + max(1, ctx.active_threats)
    )
    script_count = ctx.threat_categories_24h.get("Script Execution", 0)
    file_count = ctx.threat_categories_24h.get("File Activity", 0)
    rapid_count = ctx.threat_categories_24h.get("Rapid Modification", 0)
    other = max(0, ctx.events_last_24h - script_count - file_count - rapid_count)

    if total_weight <= 0:
        return [
            {"name": "Low Risk", "value": 70.0, "fill": "#10B981"},
            {"name": "Medium Risk", "value": 25.0, "fill": "#F59E0B"},
            {"name": "High Risk", "value": 5.0, "fill": "#EF4444"},
        ]

    high = (
        ctx.critical_threats_24h * 3
        + ctx.high_threats_24h * 2
        + ctx.ransomware_critical_24h * 4
        + rapid_count * 2
    )
    medium = script_count + file_count + ctx.ransomware_events_24h + ctx.usb_suspicious_hour
    low = max(1, other + max(0, 10 - ctx.events_last_24h))

    raw_total = high + medium + low
    return [
        {
            "name": "Low Risk",
            "value": round(low / raw_total * 100, 1),
            "fill": "#10B981",
        },
        {
            "name": "Medium Risk",
            "value": round(medium / raw_total * 100, 1),
            "fill": "#F59E0B",
        },
        {
            "name": "High Risk",
            "value": round(high / raw_total * 100, 1),
            "fill": "#EF4444",
        },
    ]


def project_threat_trends(hourly_counts: list[int]) -> list[dict[str, int]]:
    """Heuristic forward projection from recent hourly event velocity."""
    labels = ["Now", "+1h", "+2h", "+4h", "+8h"]
    base_malware = hourly_counts[-1] if hourly_counts else 0
    base_ransomware = max(0, base_malware // 4)
    base_phishing = max(0, base_malware // 3)
    growth = 1.15 if base_malware > 3 else 1.05

    points: list[dict[str, int]] = []
    for i, label in enumerate(labels):
        factor = growth ** i
        points.append(
            {
                "time": label,
                "malware": max(0, int(round(base_malware * factor))),
                "ransomware": max(0, int(round(base_ransomware * factor))),
                "phishing": max(0, int(round(base_phishing * factor * 0.9))),
            }
        )
    return points


def compute_confidence(ctx: SecurityContext) -> str:
    signals = sum(
        1
        for v in [
            ctx.events_last_24h > 0,
            ctx.ransomware_events_24h > 0,
            ctx.usb_events_hour > 0,
            ctx.quarantine_active > 0,
            ctx.previous_score is not None,
        ]
        if v
    )
    if signals >= 4:
        return "high"
    if signals >= 2:
        return "medium"
    return "low"


def compute_trend(current: int, previous: int | None) -> tuple[str, int]:
    if previous is None:
        return "stable", 0
    delta = current - previous
    if delta >= 5:
        return "improving", delta
    if delta <= -5:
        return "declining", delta
    return "stable", delta


def _system_summary(ctx: SecurityContext) -> str:
    if ctx.cpu_usage >= 90:
        return "CPU saturation may mask or amplify suspicious process activity."
    if ctx.ram_usage >= 85:
        return "High memory pressure — monitor resource-heavy processes."
    return "System resources within normal operating range."


def _threat_summary(ctx: SecurityContext) -> str:
    if ctx.critical_threats_24h:
        return f"{ctx.critical_threats_24h} critical threat event(s) in the last 24 hours."
    if ctx.events_last_hour >= 5:
        return f"Elevated file activity: {ctx.events_last_hour} events in the last hour."
    return "Threat volume is within expected baseline for monitored paths."


def _ransomware_summary(ctx: SecurityContext) -> str:
    if ctx.ransomware_critical_24h:
        return "Rapid modification bursts may indicate ransomware-like behavior."
    if ctx.ransomware_events_24h:
        return f"{ctx.ransomware_events_24h} ransomware heuristic event(s) detected recently."
    return "No ransomware heuristic triggers in the recent window."


def _usb_summary(ctx: SecurityContext) -> str:
    if ctx.usb_suspicious_hour:
        return "Suspicious or unauthorized USB devices detected recently."
    if ctx.usb_events_hour > 5:
        return "USB activity increased significantly in the last hour."
    return "USB attach/detach activity appears routine."


def _process_summary(ctx: SecurityContext) -> str:
    if ctx.dangerous_processes:
        return f"{ctx.dangerous_processes} process(es) exceed dangerous CPU/memory thresholds."
    if ctx.high_cpu_processes:
        return f"{ctx.high_cpu_processes} process(es) show elevated resource usage."
    return "Process behavior shows no critical anomalies."


def _windows_summary(ctx: SecurityContext) -> str:
    if not ctx.defender_realtime or not ctx.defender_antivirus:
        return "Windows Defender real-time protection is disabled or degraded."
    if ctx.signature_age_hours and ctx.signature_age_hours > 72:
        return "Windows Defender signatures are outdated."
    if not ctx.firewall_enabled:
        return "Windows Firewall is disabled — network exposure risk is elevated."
    return "Windows protection services are reporting healthy status."


def _quarantine_summary(ctx: SecurityContext) -> str:
    if ctx.quarantine_critical:
        return f"{ctx.quarantine_critical} critical item(s) held in quarantine."
    if ctx.quarantine_active:
        return f"{ctx.quarantine_active} file(s) currently isolated in quarantine."
    return "Quarantine vault has no active high-risk holdings."
