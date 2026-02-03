"""
Cost Analysis Engine for Epic 14: Cost Optimization Dashboard

This module provides comprehensive cost analysis capabilities including:
- Real-time cost calculation using current model pricing
- Multi-dimensional aggregation (time, model, user, organization)
- Cost trend analysis with statistical methods
- Cost anomaly detection
- Performance optimization with caching
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from cachetools import TTLCache
except ImportError:
    # Fallback if cachetools not installed
    class TTLCache:
        def __init__(self, *args, **kwargs):
            self._cache = {}
        def get(self, key, default=None):
            return self._cache.get(key, default)
        def __setitem__(self, key, value):
            self._cache[key] = value
        def __getitem__(self, key):
            return self._cache[key]
        def __contains__(self, key):
            return key in self._cache

logger = logging.getLogger(__name__)


class PeriodType(str, Enum):
    """Time period aggregation types"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class CostAnalysis:
    """Aggregated cost analysis result"""
    organization_id: str
    user_id: Optional[str]
    period_start: datetime
    period_end: datetime
    period_type: PeriodType
    
    # Model info
    model_name: str
    provider: str
    
    # Usage metrics
    total_requests: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    
    # Cost breakdown (USD)
    total_cost: Decimal
    input_cost: Decimal
    output_cost: Decimal
    
    # Performance
    avg_latency_ms: Optional[int]
    error_count: int
    error_rate: Decimal


@dataclass
class ModelCostBreakdown:
    """Cost breakdown by model"""
    model_name: str
    provider: str
    total_cost: Decimal
    total_requests: int
    total_tokens: int
    cost_per_request: Decimal
    cost_per_1k_tokens: Decimal
    percentage_of_total: Decimal


@dataclass
class UserCostBreakdown:
    """Cost breakdown by user"""
    user_id: str
    user_email: Optional[str]
    total_cost: Decimal
    total_requests: int
    total_tokens: int
    top_model: str
    percentage_of_total: Decimal


@dataclass
class TrendAnalysis:
    """Cost trend analysis"""
    metric: str
    period_type: PeriodType
    data_points: List[Tuple[datetime, Decimal]]
    
    # Statistics
    total: Decimal
    average: Decimal
    minimum: Decimal
    maximum: Decimal
    std_deviation: Decimal
    
    # Trend
    trend_direction: str  # increasing, decreasing, stable
    trend_percentage: Decimal  # % change
    growth_rate: Decimal  # daily/weekly growth rate
    
    # Forecast
    predicted_next_period: Optional[Decimal]
    confidence_interval: Optional[Tuple[Decimal, Decimal]]


@dataclass
class CostAnomaly:
    """Detected cost anomaly"""
    timestamp: datetime
    model_name: str
    actual_cost: Decimal
    expected_cost: Decimal
    deviation_percentage: Decimal
    severity: str  # low, medium, high, critical
    description: str
    contributing_factors: List[str]


@dataclass
class ModelPricing:
    """Model pricing information"""
    provider: str
    model_name: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    model_tier: Optional[str]
    quality_score: Optional[Decimal]
    context_window: Optional[int]
    is_active: bool


class CostAnalysisEngine:
    """
    Core engine for cost analysis and calculation.
    
    Features:
    - Real-time cost calculation
    - Multi-dimensional aggregation
    - Trend analysis
    - Anomaly detection
    - Performance caching
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
        # Cache for pricing data (1-hour TTL)
        self._pricing_cache = TTLCache(maxsize=100, ttl=3600)
        
        # Cache for aggregated costs (15-minute TTL)
        self._cost_cache = TTLCache(maxsize=1000, ttl=900)
        
        logger.info("Cost Analysis Engine initialized")
    
    async def calculate_costs(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[str] = None
    ) -> Dict:
        """
        Calculate costs for a given organization and time period.
        
        Args:
            organization_id: Organization to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            group_by: Optional grouping (model, user, day, hour)
            
        Returns:
            Cost analysis dictionary with breakdowns
        """
        cache_key = f"costs:{organization_id}:{start_date}:{end_date}:{group_by}"
        
        if cache_key in self._cost_cache:
            return self._cost_cache[cache_key]
        
        # Query cost_analysis table
        query = """
            SELECT 
                model_name,
                provider,
                user_id,
                period_start,
                period_type,
                SUM(total_requests) as total_requests,
                SUM(total_tokens) as total_tokens,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_cost) as total_cost,
                SUM(input_cost) as input_cost,
                SUM(output_cost) as output_cost,
                AVG(avg_latency_ms) as avg_latency_ms,
                SUM(error_count) as error_count
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_end <= $3
        """
        
        group_clause = ""
        if group_by == "model":
            group_clause = "GROUP BY model_name, provider"
        elif group_by == "user":
            group_clause = "GROUP BY user_id"
        elif group_by == "day":
            group_clause = "GROUP BY DATE(period_start), model_name, provider"
        elif group_by == "hour":
            group_clause = "GROUP BY period_start, model_name, provider"
        else:
            group_clause = "GROUP BY model_name, provider, user_id, period_start, period_type"
        
        query += f" {group_clause} ORDER BY total_cost DESC"
        
        rows = await self.db.fetch(query, organization_id, start_date, end_date)
        
        result = {
            "organization_id": organization_id,
            "period_start": start_date,
            "period_end": end_date,
            "total_cost": Decimal("0"),
            "total_requests": 0,
            "total_tokens": 0,
            "breakdowns": []
        }
        
        for row in rows:
            result["total_cost"] += row["total_cost"]
            result["total_requests"] += row["total_requests"]
            result["total_tokens"] += row["total_tokens"]
            
            result["breakdowns"].append({
                "model_name": row["model_name"],
                "provider": row["provider"],
                "user_id": row.get("user_id"),
                "total_cost": float(row["total_cost"]),
                "total_requests": row["total_requests"],
                "total_tokens": row["total_tokens"],
                "avg_latency_ms": row.get("avg_latency_ms"),
                "error_count": row.get("error_count", 0)
            })
        
        self._cost_cache[cache_key] = result
        return result
    
    async def aggregate_by_model(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[ModelCostBreakdown]:
        """
        Aggregate costs by model with rankings.
        
        Returns:
            List of ModelCostBreakdown sorted by total cost
        """
        query = """
            SELECT 
                model_name,
                provider,
                SUM(total_cost) as total_cost,
                SUM(total_requests) as total_requests,
                SUM(total_tokens) as total_tokens
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_end <= $3
            GROUP BY model_name, provider
            ORDER BY total_cost DESC
        """
        
        rows = await self.db.fetch(query, organization_id, start_date, end_date)
        
        # Calculate total for percentages
        total_cost = sum(row["total_cost"] for row in rows)
        
        breakdowns = []
        for row in rows:
            cost_per_request = (
                row["total_cost"] / row["total_requests"] 
                if row["total_requests"] > 0 else Decimal("0")
            )
            cost_per_1k_tokens = (
                (row["total_cost"] / row["total_tokens"]) * 1000
                if row["total_tokens"] > 0 else Decimal("0")
            )
            percentage = (
                (row["total_cost"] / total_cost) * 100
                if total_cost > 0 else Decimal("0")
            )
            
            breakdowns.append(ModelCostBreakdown(
                model_name=row["model_name"],
                provider=row["provider"],
                total_cost=row["total_cost"],
                total_requests=row["total_requests"],
                total_tokens=row["total_tokens"],
                cost_per_request=cost_per_request,
                cost_per_1k_tokens=cost_per_1k_tokens,
                percentage_of_total=percentage
            ))
        
        return breakdowns
    
    async def aggregate_by_user(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[UserCostBreakdown]:
        """
        Aggregate costs by user with rankings.
        
        Returns:
            List of UserCostBreakdown sorted by total cost
        """
        query = """
            WITH user_costs AS (
                SELECT 
                    user_id,
                    SUM(total_cost) as total_cost,
                    SUM(total_requests) as total_requests,
                    SUM(total_tokens) as total_tokens,
                    (
                        SELECT model_name 
                        FROM cost_analysis ca2 
                        WHERE ca2.user_id = ca.user_id 
                          AND ca2.organization_id = ca.organization_id
                        GROUP BY model_name 
                        ORDER BY SUM(total_cost) DESC 
                        LIMIT 1
                    ) as top_model
                FROM cost_analysis ca
                WHERE organization_id = $1
                  AND period_start >= $2
                  AND period_end <= $3
                  AND user_id IS NOT NULL
                GROUP BY user_id, organization_id
                ORDER BY total_cost DESC
                LIMIT $4
            )
            SELECT * FROM user_costs
        """
        
        rows = await self.db.fetch(query, organization_id, start_date, end_date, limit)
        
        # Calculate total for percentages
        total_cost = sum(row["total_cost"] for row in rows)
        
        breakdowns = []
        for row in rows:
            percentage = (
                (row["total_cost"] / total_cost) * 100
                if total_cost > 0 else Decimal("0")
            )
            
            breakdowns.append(UserCostBreakdown(
                user_id=row["user_id"],
                user_email=None,  # Could join with users table if it exists
                total_cost=row["total_cost"],
                total_requests=row["total_requests"],
                total_tokens=row["total_tokens"],
                top_model=row["top_model"] or "unknown",
                percentage_of_total=percentage
            ))
        
        return breakdowns
    
    async def get_cost_trends(
        self,
        organization_id: str,
        metric: str = "total_cost",
        days: int = 30,
        period_type: PeriodType = PeriodType.DAILY
    ) -> TrendAnalysis:
        """
        Analyze cost trends over time.
        
        Args:
            organization_id: Organization to analyze
            metric: Metric to trend (total_cost, total_requests, total_tokens)
            days: Number of days to analyze
            period_type: Aggregation period
            
        Returns:
            TrendAnalysis with statistics and predictions
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Query time series data
        query = f"""
            SELECT 
                period_start,
                SUM({metric}) as value
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_end <= $3
              AND period_type = $4
            GROUP BY period_start
            ORDER BY period_start ASC
        """
        
        rows = await self.db.fetch(
            query, 
            organization_id, 
            start_date, 
            end_date,
            period_type.value
        )
        
        if not rows:
            return TrendAnalysis(
                metric=metric,
                period_type=period_type,
                data_points=[],
                total=Decimal("0"),
                average=Decimal("0"),
                minimum=Decimal("0"),
                maximum=Decimal("0"),
                std_deviation=Decimal("0"),
                trend_direction="stable",
                trend_percentage=Decimal("0"),
                growth_rate=Decimal("0"),
                predicted_next_period=None,
                confidence_interval=None
            )
        
        # Extract data points
        data_points = [(row["period_start"], row["value"]) for row in rows]
        values = [row["value"] for row in rows]
        
        # Calculate statistics
        total = sum(values)
        average = total / len(values)
        minimum = min(values)
        maximum = max(values)
        
        # Standard deviation
        variance = sum((x - average) ** 2 for x in values) / len(values)
        std_deviation = Decimal(str(variance ** 0.5))
        
        # Trend analysis
        if len(values) >= 2:
            first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
            second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
            
            trend_percentage = (
                ((second_half_avg - first_half_avg) / first_half_avg) * 100
                if first_half_avg > 0 else Decimal("0")
            )
            
            if trend_percentage > 5:
                trend_direction = "increasing"
            elif trend_percentage < -5:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            
            # Simple growth rate (average daily change)
            growth_rate = (values[-1] - values[0]) / len(values) if len(values) > 1 else Decimal("0")
            
            # Simple prediction (last value + growth rate)
            predicted_next = values[-1] + growth_rate
            confidence_margin = std_deviation * Decimal("1.96")  # 95% CI
            
            predicted_next_period = max(Decimal("0"), predicted_next)
            confidence_interval = (
                max(Decimal("0"), predicted_next - confidence_margin),
                predicted_next + confidence_margin
            )
        else:
            trend_direction = "stable"
            trend_percentage = Decimal("0")
            growth_rate = Decimal("0")
            predicted_next_period = average
            confidence_interval = (average, average)
        
        return TrendAnalysis(
            metric=metric,
            period_type=period_type,
            data_points=data_points,
            total=total,
            average=average,
            minimum=minimum,
            maximum=maximum,
            std_deviation=std_deviation,
            trend_direction=trend_direction,
            trend_percentage=trend_percentage,
            growth_rate=growth_rate,
            predicted_next_period=predicted_next_period,
            confidence_interval=confidence_interval
        )
    
    async def detect_cost_anomalies(
        self,
        organization_id: str,
        lookback_days: int = 7
    ) -> List[CostAnomaly]:
        """
        Detect cost anomalies using statistical methods.
        
        Uses Epic 13's anomaly detection approach with Z-score.
        
        Returns:
            List of detected cost anomalies
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get daily costs by model
        query = """
            SELECT 
                period_start,
                model_name,
                SUM(total_cost) as daily_cost,
                SUM(total_requests) as daily_requests
            FROM cost_analysis
            WHERE organization_id = $1
              AND period_start >= $2
              AND period_type = 'daily'
            GROUP BY period_start, model_name
            ORDER BY period_start ASC
        """
        
        rows = await self.db.fetch(query, organization_id, start_date)
        
        # Group by model
        model_data = {}
        for row in rows:
            model = row["model_name"]
            if model not in model_data:
                model_data[model] = []
            model_data[model].append({
                "timestamp": row["period_start"],
                "cost": row["daily_cost"],
                "requests": row["daily_requests"]
            })
        
        anomalies = []
        
        # Detect anomalies for each model
        for model, data_points in model_data.items():
            if len(data_points) < 3:
                continue  # Need at least 3 points for meaningful detection
            
            costs = [dp["cost"] for dp in data_points]
            mean_cost = sum(costs) / len(costs)
            
            # Calculate standard deviation
            variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
            std_dev = Decimal(str(variance ** 0.5))
            
            if std_dev == 0:
                continue  # No variation
            
            # Check recent points for anomalies (last 2 days)
            for dp in data_points[-2:]:
                z_score = abs((dp["cost"] - mean_cost) / std_dev)
                
                if z_score > 3:  # 3 standard deviations
                    deviation_pct = ((dp["cost"] - mean_cost) / mean_cost) * 100
                    
                    # Determine severity
                    if z_score > 5:
                        severity = "critical"
                    elif z_score > 4:
                        severity = "high"
                    elif z_score > 3.5:
                        severity = "medium"
                    else:
                        severity = "low"
                    
                    # Identify contributing factors
                    factors = []
                    if dp["cost"] > mean_cost * Decimal("1.5"):
                        factors.append("Unusually high cost")
                    if dp["requests"] > sum(d["requests"] for d in data_points) / len(data_points) * 1.5:
                        factors.append("High request volume")
                    
                    anomalies.append(CostAnomaly(
                        timestamp=dp["timestamp"],
                        model_name=model,
                        actual_cost=dp["cost"],
                        expected_cost=mean_cost,
                        deviation_percentage=deviation_pct,
                        severity=severity,
                        description=f"Cost spike detected for {model}: ${dp['cost']:.2f} vs expected ${mean_cost:.2f}",
                        contributing_factors=factors or ["Statistical anomaly"]
                    ))
        
        return sorted(anomalies, key=lambda x: x.deviation_percentage, reverse=True)
    
    async def get_model_pricing(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        active_only: bool = True
    ) -> List[ModelPricing]:
        """
        Retrieve current model pricing.
        
        Args:
            model_name: Filter by specific model
            provider: Filter by provider
            active_only: Only return active models
            
        Returns:
            List of ModelPricing entries
        """
        cache_key = f"pricing:{model_name}:{provider}:{active_only}"
        
        if cache_key in self._pricing_cache:
            return self._pricing_cache[cache_key]
        
        query = """
            SELECT 
                provider,
                model_name,
                input_price_per_million,
                output_price_per_million,
                model_tier,
                quality_score,
                context_window,
                is_active
            FROM model_pricing
            WHERE 1=1
        """
        
        params = []
        param_count = 1
        
        if model_name:
            query += f" AND model_name = ${param_count}"
            params.append(model_name)
            param_count += 1
        
        if provider:
            query += f" AND provider = ${param_count}"
            params.append(provider)
            param_count += 1
        
        if active_only:
            query += " AND is_active = true"
        
        query += " ORDER BY provider, model_tier, model_name"
        
        rows = await self.db.fetch(query, *params)
        
        pricing_list = [
            ModelPricing(
                provider=row["provider"],
                model_name=row["model_name"],
                input_price_per_million=row["input_price_per_million"],
                output_price_per_million=row["output_price_per_million"],
                model_tier=row["model_tier"],
                quality_score=row.get("quality_score"),
                context_window=row.get("context_window"),
                is_active=row["is_active"]
            )
            for row in rows
        ]
        
        self._pricing_cache[cache_key] = pricing_list
        return pricing_list
    
    async def calculate_request_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        provider: Optional[str] = None
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate cost for a single API request.
        
        Args:
            model_name: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Optional provider filter
            
        Returns:
            Tuple of (input_cost, output_cost, total_cost)
        """
        # Get pricing
        pricing_list = await self.get_model_pricing(model_name, provider)
        
        if not pricing_list:
            logger.warning(f"No pricing found for model: {model_name}")
            return (Decimal("0"), Decimal("0"), Decimal("0"))
        
        pricing = pricing_list[0]  # Use first match
        
        # Calculate costs
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing.input_price_per_million
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing.output_price_per_million
        total_cost = input_cost + output_cost
        
        return (
            input_cost.quantize(Decimal("0.00000001")),
            output_cost.quantize(Decimal("0.00000001")),
            total_cost.quantize(Decimal("0.00000001"))
        )
    
    async def aggregate_costs_to_analysis_table(
        self,
        organization_id: str,
        period_start: datetime,
        period_end: datetime,
        period_type: PeriodType
    ) -> int:
        """
        Aggregate raw usage data into cost_analysis table.
        
        This would normally pull from api_usage_logs table.
        For now, returns 0 as api_usage_logs doesn't exist yet.
        
        Returns:
            Number of records created
        """
        # TODO: Implement when api_usage_logs table exists
        # This will be called by the background aggregation task
        
        logger.info(
            f"Cost aggregation scheduled for {organization_id} "
            f"from {period_start} to {period_end}"
        )
        
        return 0


# Singleton instance
_cost_analysis_engine: Optional[CostAnalysisEngine] = None


async def get_cost_analysis_engine(db_pool: asyncpg.Pool) -> CostAnalysisEngine:
    """Get or create the Cost Analysis Engine singleton"""
    global _cost_analysis_engine
    
    if _cost_analysis_engine is None:
        _cost_analysis_engine = CostAnalysisEngine(db_pool)
    
    return _cost_analysis_engine
