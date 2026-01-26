"""
Cost Recommendation Engine for Epic 14: Cost Optimization Dashboard

This module generates intelligent cost optimization recommendations including:
- Model downgrade suggestions (use cheaper models for simple tasks)
- Caching opportunities
- Prompt optimization suggestions
- Usage pattern improvements
- Savings opportunity detection
- ROI calculation
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class RecommendationType(str, Enum):
    """Types of cost recommendations"""
    MODEL_DOWNGRADE = "model_downgrade"
    CACHING = "caching"
    BATCH_PROCESSING = "batch_processing"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    TIER_MIGRATION = "tier_migration"
    RATE_LIMITING = "rate_limiting"
    UNUSED_FEATURES = "unused_features"


class ImplementationDifficulty(str, Enum):
    """Implementation difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QualityImpact(str, Enum):
    """Quality impact levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationStatus(str, Enum):
    """Recommendation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ARCHIVED = "archived"


@dataclass
class CostRecommendation:
    """Cost optimization recommendation"""
    id: str
    organization_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    
    # Impact
    current_monthly_cost: Decimal
    projected_monthly_cost: Decimal
    estimated_savings: Decimal
    savings_percentage: Decimal
    
    # Scoring
    priority_score: int  # 0-100
    confidence_score: Decimal  # 0.0-1.0
    implementation_difficulty: ImplementationDifficulty
    
    # Quality
    quality_impact: QualityImpact
    quality_score_change: Decimal
    
    # Action details
    recommended_action: Dict[str, Any]
    analysis_data: Optional[Dict]
    
    # Status
    status: RecommendationStatus
    implemented_at: Optional[datetime]
    implemented_by: Optional[str]
    actual_savings: Optional[Decimal]
    results_verified_at: Optional[datetime]
    valid_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class ModelAlternative:
    """Alternative model suggestion"""
    current_model: str
    alternative_model: str
    provider: str
    
    # Cost comparison
    current_cost_per_1m: Decimal
    alternative_cost_per_1m: Decimal
    cost_savings_percentage: Decimal
    monthly_savings_estimate: Decimal
    
    # Quality comparison
    quality_score_current: Decimal
    quality_score_alternative: Decimal
    quality_delta: Decimal
    
    # Use case fit
    recommended_for: List[str]
    not_recommended_for: List[str]
    confidence: Decimal


@dataclass
class SavingsOpportunity:
    """Detected savings opportunity"""
    id: str
    organization_id: str
    opportunity_type: str
    title: str
    description: str
    
    # Affected resources
    affected_models: List[str]
    affected_users: List[str]
    affected_period: Dict[str, str]
    
    # Cost impact
    current_monthly_cost: Decimal
    potential_savings: Decimal
    savings_percentage: Decimal
    
    # Detection
    detection_confidence: Decimal
    detection_method: str
    supporting_data: Optional[Dict]
    
    # Actions
    recommended_actions: List[str]
    estimated_implementation_hours: Decimal
    
    # Status
    status: str
    assigned_to: Optional[str]
    verified: bool
    actual_savings: Optional[Decimal]


class CostRecommendationEngine:
    """
    Generate intelligent cost optimization recommendations.
    
    Analyzes usage patterns to suggest:
    - Cheaper model alternatives
    - Optimization opportunities
    - Best practices
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        logger.info("Cost Recommendation Engine initialized")
    
    async def generate_recommendations(
        self,
        organization_id: str,
        lookback_days: int = 30
    ) -> List[CostRecommendation]:
        """
        Generate all recommendations for an organization.
        
        Args:
            organization_id: Organization to analyze
            lookback_days: Days of history to analyze
            
        Returns:
            List of CostRecommendation objects
        """
        recommendations = []
        
        # Generate different types of recommendations
        tasks = [
            self._generate_model_downgrade_recommendations(organization_id, lookback_days),
            self._generate_caching_recommendations(organization_id, lookback_days),
            self._generate_prompt_optimization_recommendations(organization_id, lookback_days),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error generating recommendations: {result}")
            elif result:
                recommendations.extend(result)
        
        # Sort by priority and savings
        recommendations.sort(
            key=lambda r: (r.priority_score, r.estimated_savings),
            reverse=True
        )
        
        return recommendations
    
    async def _generate_model_downgrade_recommendations(
        self,
        organization_id: str,
        lookback_days: int
    ) -> List[CostRecommendation]:
        """
        Suggest using cheaper models for simple tasks.
        """
        recommendations = []
        
        # Find expensive model usage
        query = """
            SELECT 
                ca.model_name,
                ca.provider,
                SUM(ca.total_cost) as total_cost,
                SUM(ca.total_requests) as total_requests,
                SUM(ca.total_tokens) as total_tokens,
                AVG(ca.avg_latency_ms) as avg_latency,
                SUM(ca.error_count) as error_count
            FROM cost_analysis ca
            JOIN model_pricing mp ON ca.model_name = mp.model_name AND ca.provider = mp.provider
            WHERE ca.organization_id = $1
              AND ca.period_start >= NOW() - INTERVAL '%s days'
              AND mp.model_tier IN ('premium', 'advanced')
            GROUP BY ca.model_name, ca.provider
            HAVING SUM(ca.total_cost) > 10.0  -- Only if spending > $10
            ORDER BY total_cost DESC
        """ % lookback_days
        
        rows = await self.db.fetch(query, organization_id)
        
        for row in rows:
            # Find cheaper alternative
            alternative = await self._find_cheaper_alternative(
                row["model_name"],
                row["provider"]
            )
            
            if not alternative:
                continue
            
            # Calculate savings
            current_monthly = row["total_cost"] * (30 / lookback_days)
            
            # Estimate 30-50% of requests could use cheaper model
            migration_rate = Decimal("0.4")  # 40% of requests
            projected_monthly = (
                current_monthly * (1 - migration_rate) +  # Keep expensive for some
                current_monthly * migration_rate * alternative.cost_savings_percentage / 100
            )
            
            estimated_savings = current_monthly - projected_monthly
            savings_percentage = (estimated_savings / current_monthly) * 100
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(
                savings_amount=estimated_savings,
                confidence=alternative.confidence,
                difficulty=ImplementationDifficulty.EASY
            )
            
            # Create recommendation
            rec = CostRecommendation(
                id=f"rec_{organization_id}_{row['model_name']}_{datetime.now().timestamp()}",
                organization_id=organization_id,
                recommendation_type=RecommendationType.MODEL_DOWNGRADE,
                title=f"Use {alternative.alternative_model} for simple tasks instead of {row['model_name']}",
                description=(
                    f"Analysis shows {row['model_name']} is being used for {row['total_requests']} requests. "
                    f"Approximately 40% of these requests could use the more cost-effective "
                    f"{alternative.alternative_model}, saving {savings_percentage:.1f}% in costs with minimal "
                    f"quality impact for simple queries."
                ),
                current_monthly_cost=current_monthly,
                projected_monthly_cost=projected_monthly,
                estimated_savings=estimated_savings,
                savings_percentage=savings_percentage,
                priority_score=priority_score,
                confidence_score=alternative.confidence,
                implementation_difficulty=ImplementationDifficulty.EASY,
                quality_impact=QualityImpact.LOW,
                quality_score_change=alternative.quality_delta,
                recommended_action={
                    "action": "switch_model",
                    "from_model": row["model_name"],
                    "to_model": alternative.alternative_model,
                    "migration_strategy": "gradual",
                    "recommended_for": alternative.recommended_for,
                    "keep_for": alternative.not_recommended_for,
                    "steps": [
                        "Identify simple query patterns (FAQ, summarization, simple Q&A)",
                        f"Route these queries to {alternative.alternative_model}",
                        "Monitor quality metrics for 1 week",
                        "Gradually increase migration percentage if quality maintained"
                    ]
                },
                analysis_data={
                    "current_usage": {
                        "requests": row["total_requests"],
                        "cost": float(row["total_cost"]),
                        "avg_latency_ms": row["avg_latency"]
                    },
                    "alternative_pricing": {
                        "model": alternative.alternative_model,
                        "cost_per_1m": float(alternative.alternative_cost_per_1m)
                    }
                },
                status=RecommendationStatus.PENDING,
                implemented_at=None,
                implemented_by=None,
                actual_savings=None,
                results_verified_at=None,
                valid_until=datetime.now() + timedelta(days=30),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            recommendations.append(rec)
        
        return recommendations
    
    async def _generate_caching_recommendations(
        self,
        organization_id: str,
        lookback_days: int
    ) -> List[CostRecommendation]:
        """
        Suggest implementing response caching for common queries.
        """
        # This would analyze request patterns to find duplicates
        # For now, return empty list (simplified)
        # TODO: Implement duplicate request detection
        return []
    
    async def _generate_prompt_optimization_recommendations(
        self,
        organization_id: str,
        lookback_days: int
    ) -> List[CostRecommendation]:
        """
        Suggest prompt optimizations to reduce token usage.
        """
        # This would analyze token usage patterns
        # For now, return empty list (simplified)
        # TODO: Implement prompt analysis
        return []
    
    async def _find_cheaper_alternative(
        self,
        current_model: str,
        provider: str
    ) -> Optional[ModelAlternative]:
        """
        Find a cheaper alternative model.
        """
        # Get current model pricing
        current = await self.db.fetchrow(
            """
            SELECT * FROM model_pricing 
            WHERE model_name = $1 AND provider = $2 AND is_active = true
            """,
            current_model,
            provider
        )
        
        if not current:
            return None
        
        # Find cheaper alternatives (same provider or others)
        query = """
            SELECT * FROM model_pricing
            WHERE is_active = true
              AND (input_price_per_million + output_price_per_million) < $1
            ORDER BY (input_price_per_million + output_price_per_million) ASC,
                     quality_score DESC
            LIMIT 3
        """
        
        current_total_price = (
            current["input_price_per_million"] + 
            current["output_price_per_million"]
        )
        
        alternatives = await self.db.fetch(query, current_total_price)
        
        if not alternatives:
            return None
        
        # Return best alternative (cheapest with highest quality)
        alt = alternatives[0]
        
        alt_total_price = (
            alt["input_price_per_million"] + 
            alt["output_price_per_million"]
        )
        
        savings_pct = ((current_total_price - alt_total_price) / current_total_price) * 100
        
        # Quality comparison
        current_quality = current.get("quality_score") or Decimal("0.8")
        alt_quality = alt.get("quality_score") or Decimal("0.7")
        quality_delta = alt_quality - current_quality
        
        # Confidence based on quality difference
        if quality_delta >= -0.05:  # Very similar quality
            confidence = Decimal("0.9")
        elif quality_delta >= -0.10:
            confidence = Decimal("0.75")
        elif quality_delta >= -0.15:
            confidence = Decimal("0.6")
        else:
            confidence = Decimal("0.4")
        
        return ModelAlternative(
            current_model=current_model,
            alternative_model=alt["model_name"],
            provider=alt["provider"],
            current_cost_per_1m=current_total_price,
            alternative_cost_per_1m=alt_total_price,
            cost_savings_percentage=savings_pct,
            monthly_savings_estimate=Decimal("0"),  # Calculated by caller
            quality_score_current=current_quality,
            quality_score_alternative=alt_quality,
            quality_delta=quality_delta,
            recommended_for=[
                "Simple queries",
                "Summarization",
                "Basic Q&A",
                "Translation",
                "Simple classification"
            ],
            not_recommended_for=[
                "Complex reasoning",
                "Code generation",
                "Advanced analysis",
                "Long context understanding"
            ],
            confidence=confidence
        )
    
    def _calculate_priority_score(
        self,
        savings_amount: Decimal,
        confidence: Decimal,
        difficulty: ImplementationDifficulty
    ) -> int:
        """
        Calculate priority score (0-100).
        
        Factors:
        - Savings amount (50%)
        - Confidence (30%)
        - Ease of implementation (20%)
        """
        # Normalize savings (assume $100/month = max for scaling)
        savings_score = min(float(savings_amount) / 100.0, 1.0) * 50
        
        # Confidence score
        confidence_score = float(confidence) * 30
        
        # Difficulty score
        difficulty_scores = {
            ImplementationDifficulty.EASY: 20,
            ImplementationDifficulty.MEDIUM: 12,
            ImplementationDifficulty.HARD: 5
        }
        difficulty_score = difficulty_scores[difficulty]
        
        total = int(savings_score + confidence_score + difficulty_score)
        return min(max(total, 0), 100)
    
    async def save_recommendation(
        self,
        recommendation: CostRecommendation
    ) -> str:
        """
        Save recommendation to database.
        
        Returns:
            Recommendation ID
        """
        query = """
            INSERT INTO cost_recommendations (
                organization_id, recommendation_type, title, description,
                current_monthly_cost, projected_monthly_cost, estimated_savings,
                savings_percentage, priority_score, confidence_score,
                implementation_difficulty, quality_impact, quality_score_change,
                recommended_action, analysis_data, status, valid_until
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id
        """
        
        row = await self.db.fetchrow(
            query,
            recommendation.organization_id,
            recommendation.recommendation_type.value,
            recommendation.title,
            recommendation.description,
            recommendation.current_monthly_cost,
            recommendation.projected_monthly_cost,
            recommendation.estimated_savings,
            recommendation.savings_percentage,
            recommendation.priority_score,
            recommendation.confidence_score,
            recommendation.implementation_difficulty.value,
            recommendation.quality_impact.value,
            recommendation.quality_score_change,
            json.dumps(recommendation.recommended_action),
            json.dumps(recommendation.analysis_data) if recommendation.analysis_data else None,
            recommendation.status.value,
            recommendation.valid_until
        )
        
        return row["id"]
    
    async def get_recommendation(self, recommendation_id: str) -> Optional[CostRecommendation]:
        """Get recommendation by ID"""
        row = await self.db.fetchrow(
            "SELECT * FROM cost_recommendations WHERE id = $1",
            recommendation_id
        )
        
        if not row:
            return None
        
        return self._row_to_recommendation(row)
    
    async def list_recommendations(
        self,
        organization_id: str,
        status: Optional[RecommendationStatus] = None,
        min_savings: Optional[Decimal] = None,
        limit: int = 50
    ) -> List[CostRecommendation]:
        """List recommendations for an organization"""
        query = "SELECT * FROM cost_recommendations WHERE organization_id = $1"
        params = [organization_id]
        param_count = 2
        
        if status:
            query += f" AND status = ${param_count}"
            params.append(status.value)
            param_count += 1
        
        if min_savings:
            query += f" AND estimated_savings >= ${param_count}"
            params.append(min_savings)
            param_count += 1
        
        query += f" ORDER BY priority_score DESC, estimated_savings DESC LIMIT ${param_count}"
        params.append(limit)
        
        rows = await self.db.fetch(query, *params)
        
        return [self._row_to_recommendation(row) for row in rows]
    
    async def update_recommendation_status(
        self,
        recommendation_id: str,
        status: RecommendationStatus,
        implemented_by: Optional[str] = None
    ) -> CostRecommendation:
        """Update recommendation status"""
        if status == RecommendationStatus.IMPLEMENTED:
            query = """
                UPDATE cost_recommendations
                SET status = $1, implemented_at = NOW(), implemented_by = $2, updated_at = NOW()
                WHERE id = $3
                RETURNING *
            """
            row = await self.db.fetchrow(query, status.value, implemented_by, recommendation_id)
        else:
            query = """
                UPDATE cost_recommendations
                SET status = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING *
            """
            row = await self.db.fetchrow(query, status.value, recommendation_id)
        
        if not row:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        return self._row_to_recommendation(row)
    
    async def verify_savings(
        self,
        recommendation_id: str,
        actual_savings: Decimal,
        verified_by: Optional[str] = None
    ) -> CostRecommendation:
        """Verify actual savings achieved"""
        query = """
            UPDATE cost_recommendations
            SET actual_savings = $1,
                results_verified_at = NOW(),
                updated_at = NOW()
            WHERE id = $2
            RETURNING *
        """
        
        row = await self.db.fetchrow(query, actual_savings, recommendation_id)
        
        if not row:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        logger.info(
            f"Verified savings for recommendation {recommendation_id}: "
            f"${actual_savings:.2f} (estimated: ${row['estimated_savings']:.2f})"
        )
        
        return self._row_to_recommendation(row)
    
    def _row_to_recommendation(self, row: asyncpg.Record) -> CostRecommendation:
        """Convert database row to CostRecommendation"""
        return CostRecommendation(
            id=row["id"],
            organization_id=row["organization_id"],
            recommendation_type=RecommendationType(row["recommendation_type"]),
            title=row["title"],
            description=row["description"],
            current_monthly_cost=row["current_monthly_cost"],
            projected_monthly_cost=row["projected_monthly_cost"],
            estimated_savings=row["estimated_savings"],
            savings_percentage=row["savings_percentage"],
            priority_score=row["priority_score"],
            confidence_score=row["confidence_score"],
            implementation_difficulty=ImplementationDifficulty(row["implementation_difficulty"]),
            quality_impact=QualityImpact(row["quality_impact"]),
            quality_score_change=row["quality_score_change"],
            recommended_action=row["recommended_action"],
            analysis_data=row.get("analysis_data"),
            status=RecommendationStatus(row["status"]),
            implemented_at=row.get("implemented_at"),
            implemented_by=row.get("implemented_by"),
            actual_savings=row.get("actual_savings"),
            results_verified_at=row.get("results_verified_at"),
            valid_until=row.get("valid_until"),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


# Singleton
_recommendation_engine: Optional[CostRecommendationEngine] = None


async def get_recommendation_engine(db_pool: asyncpg.Pool) -> CostRecommendationEngine:
    """Get or create singleton"""
    global _recommendation_engine
    
    if _recommendation_engine is None:
        _recommendation_engine = CostRecommendationEngine(db_pool)
    
    return _recommendation_engine
