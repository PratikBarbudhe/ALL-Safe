from enum import Enum

from pydantic import BaseModel, Field


class RiskPosture(str, Enum):
    SECURE = "secure"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"


class AnalysisCategory(str, Enum):
    SYSTEM_HEALTH = "System Health"
    THREAT_INTELLIGENCE = "Threat Intelligence"
    RANSOMWARE_ACTIVITY = "Ransomware Activity"
    USB_SECURITY = "USB Security"
    PROCESS_BEHAVIOR = "Process Behavior"
    WINDOWS_PROTECTION = "Windows Protection"
    QUARANTINE_ANALYSIS = "Quarantine Analysis"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AiInsight(BaseModel):
    id: str
    title: str
    message: str
    category: str
    severity: str
    confidence: str
    icon_hint: str = "activity"


class AiRecommendation(BaseModel):
    id: str
    title: str
    message: str
    priority: str
    category: str
    action_required: bool = False


class CategoryScore(BaseModel):
    category: str
    score: int = Field(..., ge=0, le=100)
    risk: str
    summary: str


class ThreatProbabilitySlice(BaseModel):
    name: str
    value: float
    fill: str


class ThreatTrendPoint(BaseModel):
    time: str
    malware: int
    ransomware: int
    phishing: int


class TopActiveRisk(BaseModel):
    name: str
    severity: str
    confidence: str
    description: str


class EngineStats(BaseModel):
    detection_rate_percent: float
    threats_analyzed: int
    estimated_false_positive_percent: float
    last_analysis_at: str
    analysis_runs_total: int
    engine_status: str


class AnalysisHistoryEntry(BaseModel):
    id: int
    timestamp: str
    overall_score: int
    risk_posture: str
    summary: str
    insight_count: int


class RiskScoreResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    risk_posture: str
    trend: str
    trend_delta: int
    confidence: str
    top_active_risks: list[TopActiveRisk]


class ActivitySummaryResponse(BaseModel):
    summary: str
    events_last_hour: int
    events_last_24h: int
    suspicious_activity_level: str
    category_breakdown: dict[str, int]


class RecommendationsResponse(BaseModel):
    recommendations: list[AiRecommendation]
    total: int


class AiAnalysisOverviewResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    risk_posture: str
    posture_label: str
    score_summary: str
    trend: str
    trend_delta: int
    confidence: str
    threat_probability: list[ThreatProbabilitySlice]
    category_scores: list[CategoryScore]
    insights: list[AiInsight]
    recommendations: list[AiRecommendation]
    threat_trend: list[ThreatTrendPoint]
    top_active_risks: list[TopActiveRisk]
    engine_stats: EngineStats
    collected_at: str


class AnalysisRunResponse(BaseModel):
    status: str
    message: str
    overview: AiAnalysisOverviewResponse


class AnalysisHistoryResponse(BaseModel):
    history: list[AnalysisHistoryEntry]
    total: int
