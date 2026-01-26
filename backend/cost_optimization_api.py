"""
Cost Optimization API for Epic 14

Comprehensive REST API endpoints for cost analysis, budgets, forecasts,
recommendations, and savings opportunities.

Features:
- Cost analysis and breakdown
- Budget CRUD and monitoring
- Cost forecasting
- Optimization recommendations
- Model pricing information
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, date
from decimal import Decimal
from enum import Enum
import asyncpg

# Import our engines
from backend.cost_analysis_engine import (
    get_cost_analysis_engine,
    CostAnalysisEngine,
    PeriodType,
    ModelCostBreakdown,
    UserCostBreakdown,
    TrendAnalysis,
    CostAnomaly,
    ModelPricing
)
from backend.budget_manager import (
    get_budget_manager,
    BudgetManager,
    BudgetConfig,
    Budget,
    BudgetStatus,
    BudgetType,
    AlertLevel
)
from backend.cost_recommendation_engine import (
    get_recommendation_engine,
    CostRecommendationEngine,
    RecommendationType,
    RecommendationStatus,
    ImplementationDifficulty,
    QualityImpact
)

# Assuming these exist from previous epics
from backend.auth_dependencies import get_current_user, require_role
from backend.database import get_db_pool

import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/costs", tags=["Cost Optimization"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TimeRangeQuery(str, Enum):
    """Predefined time ranges"""
    HOUR_1 = "1h"
    HOURS_6 = "6h"
    HOURS_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


class CostAnalysisRequest(BaseModel):
    """Request for cost analysis"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_range: Optional[TimeRangeQuery] = None
    group_by: Optional[str] = Field(None, description="model, user, day, hour")


class CostAnalysisResponse(BaseModel):
    """Cost analysis response"""
    organization_id: str
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_requests: int
    total_tokens: int
    breakdowns: List[Dict]


class ModelCostResponse(BaseModel):
    """Model cost breakdown response"""
    model_name: str
    provider: str
    total_cost: float
    total_requests: int
    total_tokens: int
    cost_per_request: float
    cost_per_1k_tokens: float
    percentage_of_total: float


class TrendResponse(BaseModel):
    """Trend analysis response"""
    metric: str
    period_type: str
    total: float
    average: float
    minimum: float
    maximum: float
    trend_direction: str
    trend_percentage: float
    growth_rate: float
    predicted_next_period: Optional[float]
    data_points: List[Dict]


class AnomalyResponse(BaseModel):
    """Cost anomaly response"""
    timestamp: datetime
    model_name: str
    actual_cost: float
    expected_cost: float
    deviation_percentage: float
    severity: str
    description: str


class BudgetCreateRequest(BaseModel):
    """Request to create a budget"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    budget_type: BudgetType
    total_limit: float = Field(..., gt=0, description="Total budget limit in USD")
    warning_threshold: float = Field(0.8, ge=0.0, le=1.0)
    critical_threshold: float = Field(0.95, ge=0.0, le=1.0)
    start_date: date
    end_date: date
    alert_enabled: bool = True
    alert_emails: Optional[List[str]] = None
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('critical_threshold')
    def critical_after_warning(cls, v, values):
        if 'warning_threshold' in values and v <= values['warning_threshold']:
            raise ValueError('critical_threshold must be greater than warning_threshold')
        return v


class BudgetUpdateRequest(BaseModel):
    """Request to update a budget"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    total_limit: Optional[float] = Field(None, gt=0)
    warning_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    critical_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    end_date: Optional[date] = None
    alert_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class BudgetResponse(BaseModel):
    """Budget response"""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    budget_type: str
    total_limit: float
    warning_threshold: float
    critical_threshold: float
    start_date: date
    end_date: date
    current_spend: float
    alert_level: str
    is_active: bool
    created_at: datetime


class BudgetStatusResponse(BaseModel):
    """Detailed budget status response"""
    budget: BudgetResponse
    utilization_percentage: float
    remaining_budget: float
    days_remaining: int
    daily_burn_rate: float
    projected_total: float
    projected_exhaustion_date: Optional[date]
    status: str
    is_on_track: bool


class RecommendationResponse(BaseModel):
    """Cost recommendation response"""
    id: str
    recommendation_type: str
    title: str
    description: str
    estimated_savings: float
    savings_percentage: float
    priority_score: int
    confidence_score: float
    implementation_difficulty: str
    quality_impact: str
    status: str
    recommended_action: Dict
    created_at: datetime


class ModelPricingResponse(BaseModel):
    """Model pricing response"""
    provider: str
    model_name: str
    input_price_per_million: float
    output_price_per_million: float
    model_tier: Optional[str]
    quality_score: Optional[float]
    is_active: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_time_range(time_range: TimeRangeQuery) -> tuple[datetime, datetime]:
    """Convert time range enum to datetime tuple"""
    end_date = datetime.now()
    
    if time_range == TimeRangeQuery.HOUR_1:
        start_date = end_date - timedelta(hours=1)
    elif time_range == TimeRangeQuery.HOURS_6:
        start_date = end_date - timedelta(hours=6)
    elif time_range == TimeRangeQuery.HOURS_24:
        start_date = end_date - timedelta(hours=24)
    elif time_range == TimeRangeQuery.DAYS_7:
        start_date = end_date - timedelta(days=7)
    elif time_range == TimeRangeQuery.DAYS_30:
        start_date = end_date - timedelta(days=30)
    elif time_range == TimeRangeQuery.DAYS_90:
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=30)  # Default
    
    return start_date, end_date


# ============================================================================
# COST ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/analysis", response_model=CostAnalysisResponse)
async def get_cost_analysis(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    time_range: Optional[TimeRangeQuery] = None,
    group_by: Optional[str] = Query(None, regex="^(model|user|day|hour)$"),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get cost analysis for organization.
    
    Query params:
    - start_date, end_date: Custom date range
    - time_range: Predefined range (1h, 6h, 24h, 7d, 30d, 90d)
    - group_by: Grouping dimension (model, user, day, hour)
    """
    engine = await get_cost_analysis_engine(db)
    organization_id = current_user.get("organization_id")
    
    # Determine date range
    if time_range:
        start_date, end_date = parse_time_range(time_range)
    elif not start_date or not end_date:
        start_date, end_date = parse_time_range(TimeRangeQuery.DAYS_30)
    
    result = await engine.calculate_costs(
        organization_id,
        start_date,
        end_date,
        group_by
    )
    
    return CostAnalysisResponse(
        organization_id=result["organization_id"],
        period_start=result["period_start"],
        period_end=result["period_end"],
        total_cost=float(result["total_cost"]),
        total_requests=result["total_requests"],
        total_tokens=result["total_tokens"],
        breakdowns=result["breakdowns"]
    )


@router.get("/breakdown/models", response_model=List[ModelCostResponse])
async def get_model_breakdown(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get cost breakdown by model"""
    engine = await get_cost_analysis_engine(db)
    organization_id = current_user.get("organization_id")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    breakdowns = await engine.aggregate_by_model(
        organization_id,
        start_date,
        end_date
    )
    
    return [
        ModelCostResponse(
            model_name=b.model_name,
            provider=b.provider,
            total_cost=float(b.total_cost),
            total_requests=b.total_requests,
            total_tokens=b.total_tokens,
            cost_per_request=float(b.cost_per_request),
            cost_per_1k_tokens=float(b.cost_per_1k_tokens),
            percentage_of_total=float(b.percentage_of_total)
        )
        for b in breakdowns
    ]


@router.get("/trends", response_model=TrendResponse)
async def get_cost_trends(
    metric: str = Query("total_cost", regex="^(total_cost|total_requests|total_tokens)$"),
    days: int = Query(30, ge=1, le=365),
    period_type: PeriodType = PeriodType.DAILY,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get cost trends over time"""
    engine = await get_cost_analysis_engine(db)
    organization_id = current_user.get("organization_id")
    
    trend = await engine.get_cost_trends(
        organization_id,
        metric,
        days,
        period_type
    )
    
    return TrendResponse(
        metric=trend.metric,
        period_type=trend.period_type.value,
        total=float(trend.total),
        average=float(trend.average),
        minimum=float(trend.minimum),
        maximum=float(trend.maximum),
        trend_direction=trend.trend_direction,
        trend_percentage=float(trend.trend_percentage),
        growth_rate=float(trend.growth_rate),
        predicted_next_period=float(trend.predicted_next_period) if trend.predicted_next_period else None,
        data_points=[
            {"timestamp": ts.isoformat(), "value": float(val)}
            for ts, val in trend.data_points
        ]
    )


@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_cost_anomalies(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get detected cost anomalies"""
    engine = await get_cost_analysis_engine(db)
    organization_id = current_user.get("organization_id")
    
    anomalies = await engine.detect_cost_anomalies(organization_id, days)
    
    return [
        AnomalyResponse(
            timestamp=a.timestamp,
            model_name=a.model_name,
            actual_cost=float(a.actual_cost),
            expected_cost=float(a.expected_cost),
            deviation_percentage=float(a.deviation_percentage),
            severity=a.severity,
            description=a.description
        )
        for a in anomalies
    ]


# ============================================================================
# BUDGET ENDPOINTS
# ============================================================================

@router.post("/budgets", response_model=BudgetResponse, status_code=201)
async def create_budget(
    request: BudgetCreateRequest,
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Create a new budget (admin/org_admin only)"""
    manager = await get_budget_manager(db)
    organization_id = current_user.get("organization_id")
    user_id = current_user.get("sub")
    
    config = BudgetConfig(
        name=request.name,
        description=request.description,
        budget_type=request.budget_type,
        total_limit=Decimal(str(request.total_limit)),
        warning_threshold=Decimal(str(request.warning_threshold)),
        critical_threshold=Decimal(str(request.critical_threshold)),
        start_date=request.start_date,
        end_date=request.end_date,
        alert_enabled=request.alert_enabled,
        alert_contacts={"emails": request.alert_emails} if request.alert_emails else None
    )
    
    budget = await manager.create_budget(organization_id, config, user_id)
    
    return _budget_to_response(budget)


@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    is_active: Optional[bool] = None,
    budget_type: Optional[BudgetType] = None,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """List budgets for organization"""
    manager = await get_budget_manager(db)
    organization_id = current_user.get("organization_id")
    
    budgets = await manager.list_budgets(organization_id, is_active, budget_type)
    
    return [_budget_to_response(b) for b in budgets]


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get budget details"""
    manager = await get_budget_manager(db)
    
    try:
        budget = await manager.get_budget(budget_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Verify access
    if budget.organization_id != current_user.get("organization_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _budget_to_response(budget)


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    request: BudgetUpdateRequest,
    budget_id: str = Path(...),
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Update budget (admin/org_admin only)"""
    manager = await get_budget_manager(db)
    
    # Verify access
    budget = await manager.get_budget(budget_id)
    if budget.organization_id != current_user.get("organization_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Prepare updates
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    # Convert floats to Decimal
    for key in ['total_limit', 'warning_threshold', 'critical_threshold']:
        if key in updates:
            updates[key] = Decimal(str(updates[key]))
    
    updated_budget = await manager.update_budget(budget_id, updates)
    
    return _budget_to_response(updated_budget)


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: str = Path(...),
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Delete budget (admin/org_admin only)"""
    manager = await get_budget_manager(db)
    
    # Verify access
    budget = await manager.get_budget(budget_id)
    if budget.organization_id != current_user.get("organization_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    await manager.delete_budget(budget_id)


@router.get("/budgets/{budget_id}/status", response_model=BudgetStatusResponse)
async def get_budget_status(
    budget_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get detailed budget status"""
    manager = await get_budget_manager(db)
    
    # Verify access
    budget = await manager.get_budget(budget_id)
    if budget.organization_id != current_user.get("organization_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    status = await manager.check_budget_status(budget_id)
    
    return BudgetStatusResponse(
        budget=_budget_to_response(status.budget),
        utilization_percentage=float(status.utilization_percentage),
        remaining_budget=float(status.remaining_budget),
        days_remaining=status.days_remaining,
        daily_burn_rate=float(status.daily_burn_rate),
        projected_total=float(status.projected_total),
        projected_exhaustion_date=status.projected_exhaustion_date,
        status=status.status,
        is_on_track=status.is_on_track
    )


# ============================================================================
# RECOMMENDATION ENDPOINTS
# ============================================================================

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def list_recommendations(
    status: Optional[RecommendationStatus] = None,
    min_savings: Optional[float] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """List cost optimization recommendations"""
    engine = await get_recommendation_engine(db)
    organization_id = current_user.get("organization_id")
    
    min_savings_decimal = Decimal(str(min_savings)) if min_savings else None
    
    recommendations = await engine.list_recommendations(
        organization_id,
        status,
        min_savings_decimal,
        limit
    )
    
    return [_recommendation_to_response(r) for r in recommendations]


@router.post("/recommendations/generate", response_model=List[RecommendationResponse])
async def generate_recommendations(
    days: int = Query(30, ge=7, le=90),
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Generate new recommendations (admin/org_admin only)"""
    engine = await get_recommendation_engine(db)
    organization_id = current_user.get("organization_id")
    
    recommendations = await engine.generate_recommendations(organization_id, days)
    
    # Save to database
    for rec in recommendations:
        await engine.save_recommendation(rec)
    
    return [_recommendation_to_response(r) for r in recommendations]


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Get recommendation details"""
    engine = await get_recommendation_engine(db)
    
    rec = await engine.get_recommendation(recommendation_id)
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Verify access
    if rec.organization_id != current_user.get("organization_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _recommendation_to_response(rec)


@router.post("/recommendations/{recommendation_id}/accept", response_model=RecommendationResponse)
async def accept_recommendation(
    recommendation_id: str = Path(...),
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Accept a recommendation"""
    engine = await get_recommendation_engine(db)
    user_id = current_user.get("sub")
    
    rec = await engine.update_recommendation_status(
        recommendation_id,
        RecommendationStatus.ACCEPTED,
        user_id
    )
    
    return _recommendation_to_response(rec)


@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationResponse)
async def reject_recommendation(
    recommendation_id: str = Path(...),
    reason: str = Body(..., embed=True),
    current_user: dict = Depends(require_role(["admin", "org_admin"])),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """Reject a recommendation"""
    engine = await get_recommendation_engine(db)
    
    rec = await engine.update_recommendation_status(
        recommendation_id,
        RecommendationStatus.REJECTED
    )
    
    logger.info(f"Recommendation {recommendation_id} rejected: {reason}")
    
    return _recommendation_to_response(rec)


# ============================================================================
# MODEL PRICING ENDPOINTS
# ============================================================================

@router.get("/pricing/models", response_model=List[ModelPricingResponse])
async def list_model_pricing(
    provider: Optional[str] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Pool = Depends(get_db_pool)
):
    """List model pricing information"""
    engine = await get_cost_analysis_engine(db)
    
    pricing_list = await engine.get_model_pricing(None, provider, active_only)
    
    return [
        ModelPricingResponse(
            provider=p.provider,
            model_name=p.model_name,
            input_price_per_million=float(p.input_price_per_million),
            output_price_per_million=float(p.output_price_per_million),
            model_tier=p.model_tier,
            quality_score=float(p.quality_score) if p.quality_score else None,
            is_active=p.is_active
        )
        for p in pricing_list
    ]


# ============================================================================
# HELPER CONVERTERS
# ============================================================================

def _budget_to_response(budget: Budget) -> BudgetResponse:
    """Convert Budget to BudgetResponse"""
    return BudgetResponse(
        id=budget.id,
        organization_id=budget.organization_id,
        name=budget.name,
        description=budget.description,
        budget_type=budget.budget_type.value,
        total_limit=float(budget.total_limit),
        warning_threshold=float(budget.warning_threshold),
        critical_threshold=float(budget.critical_threshold),
        start_date=budget.start_date,
        end_date=budget.end_date,
        current_spend=float(budget.current_spend),
        alert_level=budget.alert_level.value,
        is_active=budget.is_active,
        created_at=budget.created_at
    )


def _recommendation_to_response(rec) -> RecommendationResponse:
    """Convert CostRecommendation to RecommendationResponse"""
    return RecommendationResponse(
        id=rec.id,
        recommendation_type=rec.recommendation_type.value,
        title=rec.title,
        description=rec.description,
        estimated_savings=float(rec.estimated_savings),
        savings_percentage=float(rec.savings_percentage),
        priority_score=rec.priority_score,
        confidence_score=float(rec.confidence_score),
        implementation_difficulty=rec.implementation_difficulty.value,
        quality_impact=rec.quality_impact.value,
        status=rec.status.value,
        recommended_action=rec.recommended_action,
        created_at=rec.created_at
    )
