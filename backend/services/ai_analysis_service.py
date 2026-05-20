"""Local rule-based security intelligence and event correlation engine."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from models.ai_analysis_models import (
    ActivitySummaryResponse,
    AiAnalysisOverviewResponse,
    AiInsight,
    AiRecommendation,
    AnalysisHistoryEntry,
    AnalysisHistoryResponse,
    AnalysisRunResponse,
    CategoryScore,
    ConfidenceLevel,
    EngineStats,
    RecommendationsResponse,
    RiskScoreResponse,
    ThreatProbabilitySlice,
    ThreatTrendPoint,
    TopActiveRisk,
)
from utils.exceptions import AiAnalysisServiceError
from utils.security_scoring import (
    SecurityContext,
    calculate_category_scores,
    calculate_overall_security_score,
    compute_confidence,
    compute_threat_probability,
    compute_trend,
    determine_risk_posture,
    posture_label,
    project_threat_trends,
    score_summary_text,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "ai_analysis.db"
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "ai_analysis.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
CACHE_TTL_SECONDS = 45
HISTORY_LIMIT = 50


class AiAnalysisService:
    """Offline security intelligence: correlation, scoring, and recommendations."""

    _instance: AiAnalysisService | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._db_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._cached_overview: AiAnalysisOverviewResponse | None = None
        self._cached_at: float = 0.0
        self._cache_ttl_seconds = CACHE_TTL_SECONDS
        self._auto_analysis = True
        self._analysis_interval_seconds = 60
        self._risk_threshold = 60
        self._auto_thread: threading.Thread | None = None
        self._auto_stop = threading.Event()
        self._event_logger = self._configure_logger()
        self._init_database()

    def apply_preferences(self, prefs: Any) -> None:
        self._auto_analysis = prefs.auto_analysis
        self._analysis_interval_seconds = prefs.analysis_interval_seconds
        self._risk_threshold = prefs.risk_threshold
        self._cache_ttl_seconds = min(
            CACHE_TTL_SECONDS * 2,
            max(15, prefs.analysis_interval_seconds // 2),
        )
        if prefs.auto_analysis:
            self._start_auto_analysis()
        else:
            self._stop_auto_analysis()

    def _start_auto_analysis(self) -> None:
        if self._auto_thread and self._auto_thread.is_alive():
            return
        self._auto_stop.clear()
        self._auto_thread = threading.Thread(
            target=self._auto_analysis_loop,
            name="allsafe-ai-auto-analysis",
            daemon=True,
        )
        self._auto_thread.start()

    def _stop_auto_analysis(self) -> None:
        self._auto_stop.set()

    def _auto_analysis_loop(self) -> None:
        while not self._auto_stop.wait(self._analysis_interval_seconds):
            try:
                self.run_analysis(force=True)
            except Exception:
                logger.exception("Scheduled AI analysis failed")

    @classmethod
    def get_instance(cls) -> AiAnalysisService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _configure_logger(self) -> logging.Logger:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ai_logger = logging.getLogger("allsafe.ai_analysis")
        if not ai_logger.handlers:
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
            ai_logger.addHandler(handler)
            ai_logger.setLevel(logging.INFO)
            ai_logger.propagate = False
        return ai_logger

    def _init_database(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_analysis_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        overall_score INTEGER NOT NULL,
                        risk_posture TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        insight_count INTEGER NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ai_runs_ts ON ai_analysis_runs(timestamp)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _collect_context(self) -> SecurityContext:
        from monitoring.process_monitor import ProcessMonitor
        from monitoring.system_monitor import SystemMonitor
        from services.notification_service import notification_service
        from services.quarantine_service import quarantine_service
        from services.ransomware_service import ransomware_service
        from services.threat_log_service import threat_log_service
        from services.usb_service import usb_service
        from services.windows_defender_service import windows_defender_service

        ctx = SecurityContext()
        try:
            stats = SystemMonitor()._collect_system_stats()
            ctx.cpu_usage = stats.cpu_usage
            ctx.ram_usage = stats.ram_usage
            ctx.disk_usage = stats.disk_usage
        except Exception:
            logger.debug("System metrics unavailable for AI analysis")

        try:
            processes = ProcessMonitor()._collect_processes().processes
            for proc in processes:
                if proc.cpu_percent >= 50 or proc.memory_percent >= 80:
                    ctx.dangerous_processes += 1
                elif proc.cpu_percent >= 25 or proc.memory_percent >= 50:
                    ctx.high_cpu_processes += 1
        except Exception:
            logger.debug("Process metrics unavailable for AI analysis")

        try:
            threat_stats = threat_log_service.get_stats()
            ctx.active_threats = threat_stats.active_threats
            ctx.blocked_threats = threat_stats.blocked_threats
            ctx.events_last_24h = threat_stats.events_last_24h
            ctx.events_last_hour = self._count_threats_since_hours(1)
            ctx.critical_threats_24h = self._count_threats_since_hours(
                24, severities=("critical",)
            )
            ctx.high_threats_24h = self._count_threats_since_hours(
                24, severities=("high", "critical")
            )
            ctx.threat_categories_24h = self._threat_categories_24h()
            ctx.hourly_threat_counts = self._hourly_threat_buckets()
        except Exception:
            logger.debug("Threat stats unavailable for AI analysis")

        try:
            rw_status = ransomware_service.get_status()
            ctx.ransomware_events_24h = rw_status.events_last_24h
            ctx.ransomware_critical_24h = rw_status.critical_events_24h
        except Exception:
            pass

        try:
            history = usb_service._build_history_response()
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            for event in history.events:
                try:
                    ts = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if ts >= hour_ago:
                    ctx.usb_events_hour += 1
                    if event.protection_status in ("suspicious", "blocked"):
                        ctx.usb_suspicious_hour += 1
        except Exception:
            pass

        try:
            q_stats = quarantine_service.get_stats()
            ctx.quarantine_active = q_stats.active_count
            ctx.quarantine_critical = q_stats.critical_count
        except Exception:
            pass

        try:
            win = windows_defender_service.get_full_status()
            ctx.defender_realtime = win.defender.realtime_protection
            ctx.defender_antivirus = win.defender.antivirus_enabled
            ctx.firewall_enabled = win.firewall.enabled
            ctx.realtime_protection = win.defender.realtime_protection
            ctx.signature_age_hours = win.defender.quick_scan_age_hours
        except Exception:
            pass

        try:
            unread = notification_service.get_unread_count().unread_count
            critical = notification_service.list_notifications(
                limit=20, severity="critical", unread_only=True
            )
            ctx.unread_critical_notifications = min(unread, len(critical.notifications))
        except Exception:
            pass

        ctx.previous_score = self._latest_historical_score()
        return ctx

    def _count_threats_since_hours(
        self, hours: int, severities: tuple[str, ...] | None = None
    ) -> int:
        threat_db = DATA_DIR / "threat_logs.db"
        if not threat_db.exists():
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._db_lock:
            conn = sqlite3.connect(threat_db, check_same_thread=False)
            try:
                if severities:
                    placeholders = ",".join("?" * len(severities))
                    row = conn.execute(
                        f"""
                        SELECT COUNT(*) FROM threat_logs
                        WHERE timestamp >= ? AND severity IN ({placeholders})
                        """,
                        (cutoff, *severities),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM threat_logs WHERE timestamp >= ?",
                        (cutoff,),
                    ).fetchone()
                return int(row[0]) if row else 0
            finally:
                conn.close()

    def _threat_categories_24h(self) -> dict[str, int]:
        threat_db = DATA_DIR / "threat_logs.db"
        if not threat_db.exists():
            return {}
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self._db_lock:
            conn = sqlite3.connect(threat_db, check_same_thread=False)
            try:
                rows = conn.execute(
                    """
                    SELECT category, COUNT(*) as cnt FROM threat_logs
                    WHERE timestamp >= ?
                    GROUP BY category
                    """,
                    (cutoff,),
                ).fetchall()
                return {row[0]: row[1] for row in rows}
            finally:
                conn.close()

    def _hourly_threat_buckets(self) -> list[int]:
        threat_db = DATA_DIR / "threat_logs.db"
        buckets = [0] * 8
        if not threat_db.exists():
            return buckets
        now = datetime.now(timezone.utc)
        with self._db_lock:
            conn = sqlite3.connect(threat_db, check_same_thread=False)
            try:
                for i in range(8):
                    start = now - timedelta(hours=8 - i)
                    end = now - timedelta(hours=7 - i) if i < 7 else now
                    count = conn.execute(
                        """
                        SELECT COUNT(*) FROM threat_logs
                        WHERE timestamp >= ? AND timestamp < ?
                        """,
                        (start.isoformat(), end.isoformat()),
                    ).fetchone()[0]
                    buckets[i] = int(count)
            finally:
                conn.close()
        return buckets

    def _latest_historical_score(self) -> int | None:
        with self._db_lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    """
                    SELECT overall_score FROM ai_analysis_runs
                    ORDER BY timestamp DESC, id DESC LIMIT 1 OFFSET 1
                    """
                ).fetchone()
                return int(row["overall_score"]) if row else None
            finally:
                conn.close()

    def _generate_insights(self, ctx: SecurityContext) -> list[AiInsight]:
        insights: list[AiInsight] = []

        script_count = ctx.threat_categories_24h.get("Script Execution", 0)
        if script_count >= 2:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Suspicious Script Activity",
                    message=(
                        f"Multiple suspicious script files were detected "
                        f"({script_count} events in 24h)."
                    ),
                    category="Threat Intelligence",
                    severity="high",
                    confidence=ConfidenceLevel.HIGH.value,
                    icon_hint="alert",
                )
            )

        if ctx.signature_age_hours and ctx.signature_age_hours > 72:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Outdated Signatures",
                    message="Windows Defender signatures are outdated.",
                    category="Windows Protection",
                    severity="warning",
                    confidence=ConfidenceLevel.HIGH.value,
                    icon_hint="alert",
                )
            )

        if ctx.ransomware_critical_24h or ctx.ransomware_events_24h >= 3:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Ransomware Heuristics",
                    message=(
                        "Rapid modification bursts may indicate "
                        "ransomware-like behavior."
                    ),
                    category="Ransomware Activity",
                    severity="critical" if ctx.ransomware_critical_24h else "high",
                    confidence=ConfidenceLevel.HIGH.value,
                    icon_hint="alert",
                )
            )

        if ctx.usb_events_hour > 5:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="USB Activity Spike",
                    message="USB activity increased significantly in the last hour.",
                    category="USB Security",
                    severity="warning",
                    confidence=ConfidenceLevel.MEDIUM.value,
                    icon_hint="activity",
                )
            )

        if ctx.dangerous_processes:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Resource Anomaly",
                    message=(
                        f"{ctx.dangerous_processes} process(es) show dangerous "
                        "CPU or memory usage patterns."
                    ),
                    category="Process Behavior",
                    severity="high",
                    confidence=ConfidenceLevel.MEDIUM.value,
                    icon_hint="activity",
                )
            )

        if ctx.quarantine_critical:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Critical Quarantine Holdings",
                    message=(
                        f"{ctx.quarantine_critical} critical file(s) isolated — "
                        "review before restore."
                    ),
                    category="Quarantine Analysis",
                    severity="high",
                    confidence=ConfidenceLevel.HIGH.value,
                    icon_hint="alert",
                )
            )

        if ctx.events_last_24h == 0 and not insights:
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Baseline Stable",
                    message="No significant threat events in the last 24 hours.",
                    category="Threat Intelligence",
                    severity="info",
                    confidence=ConfidenceLevel.MEDIUM.value,
                    icon_hint="trend",
                )
            )

        if ctx.blocked_threats > 0 and ctx.events_last_24h > 5:
            rate = min(100, round((ctx.blocked_threats / max(ctx.events_last_24h, 1)) * 100))
            insights.append(
                AiInsight(
                    id=str(uuid.uuid4()),
                    title="Protection Effectiveness",
                    message=f"Approximately {rate}% of recent events were blocked or contained.",
                    category="Threat Intelligence",
                    severity="info",
                    confidence=ConfidenceLevel.MEDIUM.value,
                    icon_hint="trend",
                )
            )

        return insights[:8]

    def _generate_recommendations(
        self, ctx: SecurityContext, posture: str
    ) -> list[AiRecommendation]:
        recs: list[AiRecommendation] = []

        if not ctx.defender_realtime or not ctx.defender_antivirus:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Enable Windows Defender",
                    message="Turn on real-time and antivirus protection immediately.",
                    priority="critical",
                    category="Windows Protection",
                    action_required=True,
                )
            )

        if not ctx.firewall_enabled:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Enable Windows Firewall",
                    message="Re-enable the host firewall to reduce network exposure.",
                    priority="high",
                    category="Windows Protection",
                    action_required=True,
                )
            )

        if ctx.signature_age_hours and ctx.signature_age_hours > 48:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Update Threat Signatures",
                    message="Run a signature update to refresh Defender intelligence.",
                    priority="high",
                    category="Windows Protection",
                    action_required=True,
                )
            )

        if ctx.ransomware_critical_24h:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Investigate Ransomware Alerts",
                    message="Review ransomware events and enable auto-quarantine if disabled.",
                    priority="critical",
                    category="Ransomware Activity",
                    action_required=True,
                )
            )

        if ctx.usb_suspicious_hour:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Review USB Devices",
                    message="Inspect suspicious USB connections and update block/trust policies.",
                    priority="high",
                    category="USB Security",
                    action_required=True,
                )
            )

        if ctx.quarantine_active > 0:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Audit Quarantine Vault",
                    message=f"Verify {ctx.quarantine_active} quarantined item(s) before restore or deletion.",
                    priority="medium",
                    category="Quarantine Analysis",
                )
            )

        if ctx.dangerous_processes:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Inspect High-Risk Processes",
                    message="Open Process Monitor and terminate or investigate anomalous workloads.",
                    priority="high",
                    category="Process Behavior",
                    action_required=True,
                )
            )

        if posture in ("warning", "high_risk", "critical_risk") and ctx.events_last_hour >= 5:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Run Full Threat Review",
                    message="Open Threat Logs and filter by high/critical severity from the last hour.",
                    priority="medium",
                    category="Threat Intelligence",
                )
            )

        if not recs:
            recs.append(
                AiRecommendation(
                    id=str(uuid.uuid4()),
                    title="Maintain Protections",
                    message="Continue monitoring — local protections are operating normally.",
                    priority="low",
                    category="System Health",
                )
            )

        return recs[:10]

    def _top_active_risks(
        self, ctx: SecurityContext, insights: list[AiInsight]
    ) -> list[TopActiveRisk]:
        risks: list[TopActiveRisk] = []
        for insight in insights[:5]:
            risks.append(
                TopActiveRisk(
                    name=insight.title,
                    severity=insight.severity,
                    confidence=insight.confidence,
                    description=insight.message,
                )
            )
        if not risks and ctx.active_threats:
            risks.append(
                TopActiveRisk(
                    name="Active Threats",
                    severity="high",
                    confidence="medium",
                    description=f"{ctx.active_threats} active threat(s) require review.",
                )
            )
        return risks

    def _build_engine_stats(self, ctx: SecurityContext) -> EngineStats:
        from services.threat_log_service import threat_log_service

        try:
            stats = threat_log_service.get_stats()
            detection_rate = stats.detection_rate_percent
            total = stats.total_threats
        except Exception:
            detection_rate = 100.0
            total = 0

        low_ratio = 0.0
        if total > 0:
            try:
                stats = threat_log_service.get_stats()
                low_ratio = max(0, 100 - stats.detection_rate_percent) * 0.1
            except Exception:
                low_ratio = 0.8

        last_run = self._last_run_timestamp()
        runs_total = self._total_runs()

        return EngineStats(
            detection_rate_percent=detection_rate,
            threats_analyzed=total,
            estimated_false_positive_percent=round(low_ratio, 1),
            last_analysis_at=last_run,
            analysis_runs_total=runs_total,
            engine_status="active",
        )

    def _last_run_timestamp(self) -> str:
        with self._db_lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT timestamp FROM ai_analysis_runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
        if not row:
            return "Never"
        return self._format_timestamp(row["timestamp"])

    def _total_runs(self) -> int:
        with self._db_lock:
            conn = self._connect()
            try:
                return conn.execute("SELECT COUNT(*) FROM ai_analysis_runs").fetchone()[0]
            finally:
                conn.close()

    def run_analysis(self, *, force: bool = False) -> AiAnalysisOverviewResponse:
        if not force:
            cached = self._get_cached_overview()
            if cached:
                return cached

        ctx = self._collect_context()
        overall = calculate_overall_security_score(ctx)
        posture = determine_risk_posture(overall)
        trend, delta = compute_trend(overall, ctx.previous_score)
        confidence = compute_confidence(ctx)

        category_raw = calculate_category_scores(ctx)
        categories = [CategoryScore(**c) for c in category_raw]
        insights = self._generate_insights(ctx)
        recommendations = self._generate_recommendations(ctx, posture)
        threat_prob = [
            ThreatProbabilitySlice(**s) for s in compute_threat_probability(ctx)
        ]
        threat_trend = [
            ThreatTrendPoint(**p) for p in project_threat_trends(ctx.hourly_threat_counts)
        ]
        top_risks = self._top_active_risks(ctx, insights)

        overview = AiAnalysisOverviewResponse(
            overall_score=overall,
            risk_posture=posture,
            posture_label=posture_label(posture),
            score_summary=score_summary_text(overall, posture),
            trend=trend,
            trend_delta=delta,
            confidence=confidence,
            threat_probability=threat_prob,
            category_scores=categories,
            insights=insights,
            recommendations=recommendations,
            threat_trend=threat_trend,
            top_active_risks=top_risks,
            engine_stats=self._build_engine_stats(ctx),
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

        self._persist_run(overview)
        self._set_cache(overview)
        self._notify_critical_posture(overview)
        self._event_logger.info(
            "Analysis complete | score=%d | posture=%s | insights=%d",
            overall,
            posture,
            len(insights),
        )
        return overview

    def _persist_run(self, overview: AiAnalysisOverviewResponse) -> None:
        summary = overview.score_summary[:500]
        payload = overview.model_dump_json()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO ai_analysis_runs (
                        timestamp, overall_score, risk_posture, summary,
                        insight_count, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        overview.collected_at,
                        overview.overall_score,
                        overview.risk_posture,
                        summary,
                        len(overview.insights),
                        payload,
                    ),
                )
                count = conn.execute("SELECT COUNT(*) FROM ai_analysis_runs").fetchone()[0]
                if count > HISTORY_LIMIT:
                    excess = count - HISTORY_LIMIT
                    conn.execute(
                        """
                        DELETE FROM ai_analysis_runs WHERE id IN (
                            SELECT id FROM ai_analysis_runs
                            ORDER BY timestamp ASC, id ASC LIMIT ?
                        )
                        """,
                        (excess,),
                    )
                conn.commit()
            finally:
                conn.close()

    def _notify_critical_posture(self, overview: AiAnalysisOverviewResponse) -> None:
        if overview.overall_score >= self._risk_threshold:
            return
        if overview.risk_posture not in ("high_risk", "critical_risk"):
            return
        try:
            from models.notification_models import NotificationCategory, NotificationSeverity
            from services.notification_service import notification_service

            severity = (
                NotificationSeverity.CRITICAL.value
                if overview.risk_posture == "critical_risk"
                else NotificationSeverity.HIGH.value
            )
            notification_service.emit(
                title="Security Intelligence Alert",
                message=overview.score_summary,
                severity=severity,
                category=NotificationCategory.SYSTEM_HEALTH.value,
                source_module="ai_analysis",
                action_required=True,
                show_toast=overview.risk_posture == "critical_risk",
                dedupe_key=f"ai:posture:{overview.risk_posture}",
            )
        except Exception:
            logger.debug("Failed to emit AI analysis notification", exc_info=True)

    def _set_cache(self, overview: AiAnalysisOverviewResponse) -> None:
        with self._cache_lock:
            self._cached_overview = overview
            self._cached_at = time.monotonic()

    def _get_cached_overview(self) -> AiAnalysisOverviewResponse | None:
        with self._cache_lock:
            if (
                self._cached_overview
                and time.monotonic() - self._cached_at < self._cache_ttl_seconds
            ):
                return self._cached_overview
        return None

    def get_overview(self, *, force: bool = False) -> AiAnalysisOverviewResponse:
        if not force:
            try:
                from services.performance_monitor_service import (
                    performance_monitor_service,
                )

                if performance_monitor_service.should_throttle_expensive_work():
                    cached = self._get_cached_overview()
                    if cached:
                        return cached
            except Exception:
                pass
        return self.run_analysis(force=force)

    def get_risk_score(self) -> RiskScoreResponse:
        overview = self.get_overview()
        return RiskScoreResponse(
            overall_score=overview.overall_score,
            risk_posture=overview.risk_posture,
            trend=overview.trend,
            trend_delta=overview.trend_delta,
            confidence=overview.confidence,
            top_active_risks=overview.top_active_risks,
        )

    def get_recommendations(self) -> RecommendationsResponse:
        overview = self.get_overview()
        return RecommendationsResponse(
            recommendations=overview.recommendations,
            total=len(overview.recommendations),
        )

    def get_activity_summary(self) -> ActivitySummaryResponse:
        ctx = self._collect_context()
        level = "low"
        if ctx.events_last_hour >= 10 or ctx.ransomware_critical_24h:
            level = "high"
        elif ctx.events_last_hour >= 3:
            level = "medium"

        parts = []
        if ctx.events_last_hour:
            parts.append(f"{ctx.events_last_hour} threat-related event(s) in the last hour")
        if ctx.usb_events_hour:
            parts.append(f"{ctx.usb_events_hour} USB event(s)")
        if ctx.ransomware_events_24h:
            parts.append(f"{ctx.ransomware_events_24h} ransomware heuristic(s) in 24h")

        summary = (
            "; ".join(parts) + "."
            if parts
            else "No significant correlated activity in the recent monitoring window."
        )

        return ActivitySummaryResponse(
            summary=summary,
            events_last_hour=ctx.events_last_hour,
            events_last_24h=ctx.events_last_24h,
            suspicious_activity_level=level,
            category_breakdown=ctx.threat_categories_24h,
        )

    def get_history(self, limit: int = 20) -> AnalysisHistoryResponse:
        limit = max(1, min(limit, 50))
        with self._db_lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT id, timestamp, overall_score, risk_posture, summary, insight_count
                    FROM ai_analysis_runs
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM ai_analysis_runs").fetchone()[0]
            finally:
                conn.close()

        history = [
            AnalysisHistoryEntry(
                id=row["id"],
                timestamp=self._format_timestamp(row["timestamp"]),
                overall_score=row["overall_score"],
                risk_posture=row["risk_posture"],
                summary=row["summary"],
                insight_count=row["insight_count"],
            )
            for row in rows
        ]
        return AnalysisHistoryResponse(history=history, total=total)

    def get_cached_score(self) -> int | None:
        """Return cached analysis score without forcing a new run."""
        cached = self._get_cached_overview()
        return cached.overall_score if cached else None

    def get_latest_score_for_dashboard(self) -> int | None:
        """Score for dashboard: cached first, otherwise lightweight run."""
        score = self.get_cached_score()
        if score is not None:
            return score
        try:
            return self.get_overview().overall_score
        except Exception:
            return None

    async def get_overview_async(self, *, force: bool = False) -> AiAnalysisOverviewResponse:
        return await asyncio.to_thread(lambda: self.get_overview(force=force))

    async def get_risk_score_async(self) -> RiskScoreResponse:
        return await asyncio.to_thread(self.get_risk_score)

    async def get_recommendations_async(self) -> RecommendationsResponse:
        return await asyncio.to_thread(self.get_recommendations)

    async def get_activity_summary_async(self) -> ActivitySummaryResponse:
        return await asyncio.to_thread(self.get_activity_summary)

    async def run_analysis_async(self) -> AnalysisRunResponse:
        return await asyncio.to_thread(self._run_analysis_response)

    async def get_history_async(self, limit: int = 20) -> AnalysisHistoryResponse:
        return await asyncio.to_thread(lambda: self.get_history(limit=limit))

    def _run_analysis_response(self) -> AnalysisRunResponse:
        overview = self.run_analysis(force=True)
        return AnalysisRunResponse(
            status="ok",
            message="Local security analysis completed",
            overview=overview,
        )

    @staticmethod
    def _format_timestamp(iso_timestamp: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return iso_timestamp


ai_analysis_service = AiAnalysisService.get_instance()
