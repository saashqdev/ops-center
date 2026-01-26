"""
Smart Alerts API Endpoints

REST API for anomaly detection, model management, and smart alerts.

Epic 13: Smart Alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

from auth_dependencies import get_current_user, require_role
from database.connection import get_db_pool
from smart_alerts_service import get_smart_alerts_service
from prediction_engine import get_prediction_engine
from alert_correlation_engine import get_correlation_engine
from noise_reduction_engine import get_noise_reduction_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/smart-alerts", tags=["Smart Alerts"])


# =====================================================================
# Pydantic Models
# =====================================================================

class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection record"""
    id: UUID
    device_id: UUID
    metric_name: str
    detected_at: datetime
    metric_value: float
    expected_value: Optional[float]
    expected_range_min: Optional[float]
    expected_range_max: Optional[float]
    anomaly_score: float
    model_type: str
    confidence: float
    severity: str
    alert_id: Optional[UUID]
    false_positive: Optional[bool]
    metadata: dict


class ModelPerformanceResponse(BaseModel):
    """Model performance metrics"""
    device_id: UUID
    metric_name: str
    model_type: str
    accuracy_score: Optional[float]
    false_positive_rate: Optional[float]
    last_trained_at: datetime
    version: int
    training_samples: Optional[int]


class TrainModelRequest(BaseModel):
    """Request to train a model"""
    device_id: UUID
    metric_name: str
    training_days: int = Field(default=30, ge=7, le=90)
    contamination: float = Field(default=0.05, ge=0.01, le=0.2)


class MarkFalsePositiveRequest(BaseModel):
    """Mark anomaly as false positive"""
    anomaly_id: UUID


class AnomalyStatsResponse(BaseModel):
    """Anomaly statistics"""
    total_anomalies: int
    critical_count: int
    error_count: int
    warning_count: int
    info_count: int
    false_positive_count: int
    avg_anomaly_score: float


class PredictionResponse(BaseModel):
    """Metric prediction"""
    id: UUID
    device_id: UUID
    metric_name: str
    forecast_horizon_minutes: int
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: float
    model_type: str
    predicted_at: datetime


class ThresholdCrossingResponse(BaseModel):
    """Predicted threshold crossing"""
    metric_name: str
    device_id: UUID
    threshold_value: float
    threshold_type: str
    estimated_crossing_time: datetime
    time_until_crossing_seconds: float
    confidence: float
    current_value: float
    trend: str
    growth_rate: float


class ResourceExhaustionResponse(BaseModel):
    """Resource exhaustion prediction"""
    resource: str
    current_usage: float
    threshold: float
    time_until_exhaustion: str
    time_until_exhaustion_seconds: float
    estimated_exhaustion_time: datetime
    growth_rate_per_hour: float
    confidence: float
    severity: str


class AlertCorrelationResponse(BaseModel):
    """Alert correlation group"""
    id: UUID
    correlation_group_id: str
    alert_ids: List[UUID]
    root_cause_alert_id: Optional[UUID]
    correlation_type: str
    confidence_score: float
    detected_at: datetime
    time_window_start: datetime
    time_window_end: datetime
    impact_score: float
    metadata: dict


class CorrelationDetailsResponse(BaseModel):
    """Detailed correlation information"""
    correlation: dict
    alerts: List[dict]
    root_cause: Optional[dict]
    alert_count: int
    affected_devices: int


class SuppressionRuleRequest(BaseModel):
    """Create/update suppression rule"""
    rule_name: str
    rule_type: str  # 'maintenance', 'known_issue', 'schedule', 'regex'
    device_id: Optional[UUID] = None
    alert_pattern: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    days_of_week: Optional[List[int]] = None
    metadata: Optional[dict] = None


class SuppressionRuleResponse(BaseModel):
    """Suppression rule"""
    id: UUID
    rule_name: str
    rule_type: str
    device_id: Optional[UUID]
    alert_pattern: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    days_of_week: Optional[List[int]]
    is_active: bool
    created_by: UUID
    metadata: dict


class FlappingDetectionResponse(BaseModel):
    """Flapping alert detection"""
    device_id: UUID
    alert_pattern: str
    flap_count: int
    time_window_minutes: int
    first_occurrence: datetime
    last_occurrence: datetime
    is_flapping: bool
    suppression_recommended: bool


# =====================================================================
# Anomaly Detection Endpoints
# =====================================================================

@router.get("/anomalies", response_model=List[AnomalyDetectionResponse])
async def get_anomalies(
    device_id: Optional[UUID] = Query(None, description="Filter by device"),
    metric_name: Optional[str] = Query(None, description="Filter by metric"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Get detected anomalies with optional filters.
    
    Returns paginated list of anomaly detections.
    """
    service = await get_smart_alerts_service(db_pool)
    
    anomalies = await service.get_anomalies(
        device_id=device_id,
        metric_name=metric_name,
        severity=severity,
        limit=limit,
        offset=offset
    )
    
    return anomalies


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyDetectionResponse)
async def get_anomaly_details(
    anomaly_id: UUID,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get details of a specific anomaly detection"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id, device_id, metric_name, detected_at, metric_value,
                expected_value, expected_range_min, expected_range_max,
                anomaly_score, model_type, confidence, severity,
                alert_id, false_positive, metadata
            FROM anomaly_detections
            WHERE id = $1
        """, anomaly_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        
        return dict(row)


@router.post("/anomalies/{anomaly_id}/false-positive")
async def mark_false_positive(
    anomaly_id: UUID,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Mark an anomaly as a false positive"""
    service = await get_smart_alerts_service(db_pool)
    
    await service.mark_false_positive(anomaly_id, current_user['id'])
    
    return {"message": "Anomaly marked as false positive"}


@router.get("/anomalies/stats", response_model=AnomalyStatsResponse)
async def get_anomaly_stats(
    device_id: Optional[UUID] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get anomaly statistics for the specified time period"""
    async with db_pool.acquire() as conn:
        conditions = ["detected_at > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        
        if device_id:
            conditions.append("device_id = $1")
            params.append(device_id)
        
        where_clause = " AND ".join(conditions)
        
        row = await conn.fetchrow(f"""
            SELECT 
                COUNT(*) as total_anomalies,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical_count,
                COUNT(*) FILTER (WHERE severity = 'error') as error_count,
                COUNT(*) FILTER (WHERE severity = 'warning') as warning_count,
                COUNT(*) FILTER (WHERE severity = 'info') as info_count,
                COUNT(*) FILTER (WHERE false_positive = true) as false_positive_count,
                COALESCE(AVG(anomaly_score), 0) as avg_anomaly_score
            FROM anomaly_detections
            WHERE {where_clause}
        """, *params)
        
        return dict(row)


# =====================================================================
# Model Management Endpoints
# =====================================================================

@router.get("/models", response_model=List[ModelPerformanceResponse])
async def get_models(
    device_id: Optional[UUID] = Query(None),
    metric_name: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get ML models and their performance metrics"""
    service = await get_smart_alerts_service(db_pool)
    
    models = await service.get_model_performance(
        device_id=device_id,
        metric_name=metric_name
    )
    
    return models


@router.post("/models/train")
async def train_model(
    request: TrainModelRequest,
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """
    Train a new anomaly detection model.
    
    Requires admin role.
    """
    service = await get_smart_alerts_service(db_pool)
    
    success = await service.detector.train_model(
        device_id=request.device_id,
        metric_name=request.metric_name,
        training_days=request.training_days,
        contamination=request.contamination
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Model training failed. Check logs for details."
        )
    
    return {"message": "Model trained successfully"}


@router.post("/models/train-all")
async def train_all_models(
    organization_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """
    Train models for all devices.
    
    This is a long-running operation. Runs in background.
    Requires admin role.
    """
    service = await get_smart_alerts_service(db_pool)
    
    # Start training in background
    import asyncio
    asyncio.create_task(service.detector.train_all_models(organization_id))
    
    return {"message": "Model training started in background"}


@router.get("/models/{device_id}/{metric_name}")
async def get_model_details(
    device_id: UUID,
    metric_name: str,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get details of a specific model"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 
                id, device_id, metric_name, model_type,
                baseline_stats, training_data_start, training_data_end,
                accuracy_score, false_positive_rate,
                last_trained_at, version, status
            FROM smart_alert_models
            WHERE device_id = $1 AND metric_name = $2
              AND status = 'active'
            ORDER BY last_trained_at DESC
            LIMIT 1
        """, device_id, metric_name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Don't return the actual model_data (too large)
        result = dict(row)
        result.pop('model_data', None)
        
        return result


# =====================================================================
# Baseline Statistics Endpoints
# =====================================================================

@router.get("/baselines/{device_id}/{metric_name}")
async def get_baseline(
    device_id: UUID,
    metric_name: str,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get baseline statistics for a device metric"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT baseline_stats, last_trained_at
            FROM smart_alert_models
            WHERE device_id = $1 AND metric_name = $2
              AND status = 'active'
              AND baseline_stats IS NOT NULL
            ORDER BY last_trained_at DESC
            LIMIT 1
        """, device_id, metric_name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Baseline not found")
        
        return {
            "device_id": device_id,
            "metric_name": metric_name,
            "baseline": row['baseline_stats'],
            "last_updated": row['last_trained_at']
        }


# =====================================================================
# System Health Endpoints
# =====================================================================

@router.get("/health")
async def get_health(
    db_pool = Depends(get_db_pool)
):
    """Get Smart Alerts system health status"""
    async with db_pool.acquire() as conn:
        # Count active models
        active_models = await conn.fetchval("""
            SELECT COUNT(*) FROM smart_alert_models WHERE status = 'active'
        """)
        
        # Count anomalies in last 24h
        recent_anomalies = await conn.fetchval("""
            SELECT COUNT(*) FROM anomaly_detections
            WHERE detected_at > NOW() - INTERVAL '24 hours'
        """)
        
        # Get latest model training time
        last_training = await conn.fetchval("""
            SELECT MAX(last_trained_at) FROM smart_alert_models
        """)
        
        # Count smart alerts created today
        smart_alerts_today = await conn.fetchval("""
            SELECT COUNT(*) FROM alerts
            WHERE is_smart_alert = true
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
    
    return {
        "status": "healthy",
        "active_models": active_models,
        "recent_anomalies": recent_anomalies,
        "smart_alerts_today": smart_alerts_today,
        "last_training": last_training
    }


# =====================================================================
# Analytics Endpoints
# =====================================================================

@router.get("/analytics/model-accuracy")
async def get_model_accuracy(
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get model accuracy metrics across all models"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                model_type,
                COUNT(*) as model_count,
                AVG(accuracy_score) as avg_accuracy,
                AVG(false_positive_rate) as avg_fpr,
                MIN(accuracy_score) as min_accuracy,
                MAX(accuracy_score) as max_accuracy
            FROM smart_alert_models
            WHERE status = 'active'
              AND accuracy_score IS NOT NULL
            GROUP BY model_type
            ORDER BY model_type
        """)
        
        return [dict(row) for row in rows]


@router.get("/analytics/detection-trends")
async def get_detection_trends(
    days: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get anomaly detection trends over time"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                DATE(detected_at) as date,
                COUNT(*) as total_anomalies,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical,
                COUNT(*) FILTER (WHERE severity = 'error') as error,
                COUNT(*) FILTER (WHERE severity = 'warning') as warning,
                AVG(anomaly_score) as avg_score,
                COUNT(*) FILTER (WHERE false_positive = true) as false_positives
            FROM anomaly_detections
            WHERE detected_at > NOW() - INTERVAL '%s days'
            GROUP BY DATE(detected_at)
            ORDER BY date DESC
        """ % days)
        
        return [dict(row) for row in rows]


@router.get("/analytics/top-anomalous-devices")
async def get_top_anomalous_devices(
    limit: int = Query(10, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get devices with most anomalies"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                ad.device_id,
                d.device_name,
                COUNT(*) as anomaly_count,
                COUNT(*) FILTER (WHERE ad.severity = 'critical') as critical_count,
                AVG(ad.anomaly_score) as avg_score
            FROM anomaly_detections ad
            JOIN devices d ON d.id = ad.device_id
            WHERE ad.detected_at > NOW() - INTERVAL '%s hours'
            GROUP BY ad.device_id, d.device_name
            ORDER BY anomaly_count DESC
            LIMIT $1
        """ % hours, limit)
        
        return [dict(row) for row in rows]


# =====================================================================
# Prediction Endpoints
# =====================================================================

@router.post("/predictions/forecast/{device_id}/{metric_name}")
async def create_forecast(
    device_id: UUID,
    metric_name: str,
    horizons: List[int] = Query([60, 180, 360], description="Forecast horizons in minutes"),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Generate metric forecasts at specified time horizons.
    
    Creates predictions for 1, 3, and 6 hours by default.
    """
    engine = await get_prediction_engine(db_pool)
    
    predictions = await engine.predict_metric(
        device_id=device_id,
        metric_name=metric_name,
        forecast_horizons=horizons
    )
    
    return {
        "device_id": device_id,
        "metric_name": metric_name,
        "predictions": [p.to_dict() for p in predictions],
        "count": len(predictions)
    }


@router.get("/predictions", response_model=List[PredictionResponse])
async def get_predictions(
    device_id: Optional[UUID] = Query(None),
    metric_name: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get stored metric predictions"""
    engine = await get_prediction_engine(db_pool)
    
    predictions = await engine.get_predictions(
        device_id=device_id,
        metric_name=metric_name,
        hours=hours
    )
    
    return predictions


@router.get("/predictions/threshold-crossing/{device_id}/{metric_name}")
async def predict_threshold_crossing(
    device_id: UUID,
    metric_name: str,
    warning_threshold: Optional[float] = Query(None),
    critical_threshold: Optional[float] = Query(None),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Predict when a metric will cross its threshold.
    
    Returns estimated crossing time and confidence.
    """
    engine = await get_prediction_engine(db_pool)
    
    custom_thresholds = None
    if warning_threshold or critical_threshold:
        custom_thresholds = {}
        if warning_threshold:
            custom_thresholds['warning'] = warning_threshold
        if critical_threshold:
            custom_thresholds['critical'] = critical_threshold
    
    crossing = await engine.predict_threshold_crossing(
        device_id=device_id,
        metric_name=metric_name,
        custom_thresholds=custom_thresholds
    )
    
    if not crossing:
        return {
            "crossing_predicted": False,
            "message": "No threshold crossing predicted in next 6 hours"
        }
    
    return {
        "crossing_predicted": True,
        "crossing": crossing.to_dict()
    }


@router.get("/predictions/resource-exhaustion/{device_id}")
async def predict_resource_exhaustion(
    device_id: UUID,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Detect potential resource exhaustion scenarios.
    
    Checks disk space, memory, and connection pools.
    Returns time estimates for critical resources.
    """
    engine = await get_prediction_engine(db_pool)
    
    warnings = await engine.detect_resource_exhaustion(device_id)
    
    return {
        "device_id": device_id,
        "exhaustion_warnings": warnings,
        "count": len(warnings),
        "critical_count": sum(1 for w in warnings if w['severity'] == 'critical')
    }


# =====================================================================
# Alert Correlation Endpoints
# =====================================================================

@router.get("/correlations", response_model=List[AlertCorrelationResponse])
async def get_correlations(
    hours: int = Query(24, ge=1, le=168),
    correlation_type: Optional[str] = Query(None, description="Filter by type"),
    min_impact: Optional[float] = Query(None, ge=0, le=100, description="Minimum impact score"),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Get alert correlations with optional filters.
    
    Correlation types:
    - temporal: Alerts occurring within same time window
    - device_cascade: Related devices (rack, network, service)
    - metric_pattern: Similar metric patterns across devices
    """
    engine = await get_correlation_engine(db_pool)
    
    correlations = await engine.get_correlations(
        hours=hours,
        correlation_type=correlation_type,
        min_impact=min_impact
    )
    
    return correlations


@router.get("/correlations/{correlation_id}", response_model=CorrelationDetailsResponse)
async def get_correlation_details(
    correlation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get detailed information about a specific correlation"""
    engine = await get_correlation_engine(db_pool)
    
    details = await engine.get_correlation_details(correlation_id)
    
    if not details:
        raise HTTPException(status_code=404, detail="Correlation not found")
    
    return details


@router.post("/correlations/analyze")
async def analyze_correlations(
    time_window_minutes: int = Query(15, ge=5, le=60),
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """
    Manually trigger correlation analysis.
    
    Analyzes recent alerts and creates correlation groups.
    Requires admin role.
    """
    engine = await get_correlation_engine(db_pool)
    
    correlations = await engine.correlate_alerts(time_window_minutes)
    
    return {
        "message": "Correlation analysis completed",
        "correlations_found": len(correlations),
        "time_window_minutes": time_window_minutes,
        "correlations": [c.to_dict() for c in correlations]
    }


@router.get("/correlations/stats")
async def get_correlation_stats(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """Get correlation statistics"""
    async with db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_correlations,
                COUNT(DISTINCT correlation_group_id) as unique_groups,
                AVG(impact_score) as avg_impact,
                MAX(impact_score) as max_impact,
                COUNT(*) FILTER (WHERE correlation_type = 'temporal') as temporal_count,
                COUNT(*) FILTER (WHERE correlation_type = 'device_cascade') as cascade_count,
                COUNT(*) FILTER (WHERE correlation_type = 'metric_pattern') as pattern_count,
                AVG(confidence_score) as avg_confidence
            FROM alert_correlations
            WHERE detected_at > NOW() - INTERVAL '%s hours'
        """ % hours)
        
        # Get top correlation groups by impact
        top_groups = await conn.fetch("""
            SELECT 
                correlation_group_id,
                correlation_type,
                impact_score,
                array_length(alert_ids, 1) as alert_count,
                detected_at
            FROM alert_correlations
            WHERE detected_at > NOW() - INTERVAL '%s hours'
            ORDER BY impact_score DESC
            LIMIT 10
        """ % hours)
        
        return {
            "summary": dict(stats),
            "top_correlations": [dict(row) for row in top_groups]
        }


# =====================================================================
# Noise Reduction Endpoints
# =====================================================================

@router.get("/suppression-rules", response_model=List[SuppressionRuleResponse])
async def get_suppression_rules(
    is_active: Optional[bool] = Query(None),
    rule_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Get alert suppression rules.
    
    Rule types:
    - maintenance: Suppress during maintenance windows
    - known_issue: Suppress known/accepted issues
    - schedule: Suppress on specific days/times
    - regex: Pattern-based suppression
    """
    engine = await get_noise_reduction_engine(db_pool)
    
    rules = await engine.get_suppression_rules(
        is_active=is_active,
        rule_type=rule_type
    )
    
    return [rule.to_dict() for rule in rules]


@router.post("/suppression-rules")
async def create_suppression_rule(
    request: SuppressionRuleRequest,
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """
    Create a new alert suppression rule.
    
    Requires admin role.
    """
    engine = await get_noise_reduction_engine(db_pool)
    
    rule_id = await engine.create_suppression_rule(
        rule_name=request.rule_name,
        rule_type=request.rule_type,
        created_by=UUID(current_user['id']),
        device_id=request.device_id,
        alert_pattern=request.alert_pattern,
        start_time=request.start_time,
        end_time=request.end_time,
        days_of_week=request.days_of_week,
        metadata=request.metadata
    )
    
    return {
        "message": "Suppression rule created",
        "rule_id": str(rule_id)
    }


@router.patch("/suppression-rules/{rule_id}")
async def update_suppression_rule(
    rule_id: UUID,
    is_active: Optional[bool] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """
    Update a suppression rule.
    
    Requires admin role.
    """
    engine = await get_noise_reduction_engine(db_pool)
    
    success = await engine.update_suppression_rule(
        rule_id=rule_id,
        is_active=is_active,
        start_time=start_time,
        end_time=end_time
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    return {"message": "Suppression rule updated"}


@router.delete("/suppression-rules/{rule_id}")
async def delete_suppression_rule(
    rule_id: UUID,
    current_user: dict = Depends(require_role(['admin'])),
    db_pool = Depends(get_db_pool)
):
    """Delete a suppression rule. Requires admin role."""
    engine = await get_noise_reduction_engine(db_pool)
    
    await engine.delete_suppression_rule(rule_id)
    
    return {"message": "Suppression rule deleted"}


@router.get("/noise-reduction/flapping", response_model=List[FlappingDetectionResponse])
async def detect_flapping(
    hours: int = Query(1, ge=1, le=24),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Detect flapping alerts (rapidly opening/closing).
    
    Identifies alerts that oscillate between open/closed states.
    """
    engine = await get_noise_reduction_engine(db_pool)
    
    flapping = await engine.detect_flapping_alerts(hours=hours)
    
    return flapping


@router.get("/noise-reduction/stats")
async def get_noise_reduction_stats(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
    db_pool = Depends(get_db_pool)
):
    """
    Get noise reduction statistics.
    
    Shows how many alerts were suppressed and why.
    """
    engine = await get_noise_reduction_engine(db_pool)
    
    stats = await engine.get_noise_reduction_stats(hours=hours)
    
    return stats
