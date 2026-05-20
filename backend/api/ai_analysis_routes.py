import logging

from fastapi import APIRouter, Depends, Query

from models.ai_analysis_models import (
    ActivitySummaryResponse,
    AiAnalysisOverviewResponse,
    AnalysisHistoryResponse,
    AnalysisRunResponse,
    RecommendationsResponse,
    RiskScoreResponse,
)
from services.ai_analysis_service import AiAnalysisService, ai_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-analysis", tags=["AI Analysis"])


def get_ai_analysis_service() -> AiAnalysisService:
    return ai_analysis_service


@router.get(
    "/overview",
    response_model=AiAnalysisOverviewResponse,
    summary="Full local security intelligence overview",
)
async def get_ai_analysis_overview(
    refresh: bool = Query(False, description="Bypass cache and recompute"),
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> AiAnalysisOverviewResponse:
    return await service.get_overview_async(force=refresh)


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Protection recommendations from correlated events",
)
async def get_ai_recommendations(
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> RecommendationsResponse:
    return await service.get_recommendations_async()


@router.get(
    "/risk-score",
    response_model=RiskScoreResponse,
    summary="Overall risk score and top active risks",
)
async def get_ai_risk_score(
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> RiskScoreResponse:
    return await service.get_risk_score_async()


@router.get(
    "/activity-summary",
    response_model=ActivitySummaryResponse,
    summary="Human-readable suspicious activity summary",
)
async def get_ai_activity_summary(
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> ActivitySummaryResponse:
    return await service.get_activity_summary_async()


@router.get(
    "/history",
    response_model=AnalysisHistoryResponse,
    summary="Past local analysis runs",
)
async def get_ai_analysis_history(
    limit: int = Query(20, ge=1, le=50),
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> AnalysisHistoryResponse:
    return await service.get_history_async(limit=limit)


@router.post(
    "/run",
    response_model=AnalysisRunResponse,
    summary="Force a new local intelligence analysis run",
)
async def run_ai_analysis(
    service: AiAnalysisService = Depends(get_ai_analysis_service),
) -> AnalysisRunResponse:
    return await service.run_analysis_async()
