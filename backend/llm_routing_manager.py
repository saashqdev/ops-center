"""
LLM Routing Manager - Epic 3.1 Multi-Provider Intelligent Routing

Implements WilmerAI-style cost/latency/quality optimization with power level routing.
Handles provider selection, failover, and BYOK key management.

Author: Ops Center Team
Version: 1.0.0
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

import asyncpg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===============================
# Models and Constants
# ===============================

class PowerLevel(str):
    """Power level constants for routing"""
    ECO = "ECO"              # Free/cheap, fast models
    BALANCED = "BALANCED"     # Value-optimized models
    PRECISION = "PRECISION"   # Premium quality models


class RoutingStrategy(str):
    """Routing strategy types"""
    COST_OPTIMIZED = "cost_optimized"       # Minimize cost
    LATENCY_OPTIMIZED = "latency_optimized" # Minimize latency
    QUALITY_OPTIMIZED = "quality_optimized" # Maximize quality
    BALANCED = "balanced"                   # WilmerAI-style weighted scoring


class ModelScore(BaseModel):
    """Model scoring for routing decisions"""
    model_id: UUID
    provider_id: UUID
    model_name: str
    provider_name: str
    composite_score: float
    cost_score: float
    latency_score: float
    quality_score: float
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    avg_latency_ms: int
    quality_rating: float
    priority: int


class RoutingConfig(BaseModel):
    """Routing configuration with weights"""
    strategy: str = Field(default="balanced")
    cost_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    latency_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    quality_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    max_retries: int = Field(default=3)
    fallback_enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30)


class ProviderHealth(BaseModel):
    """Provider health status"""
    provider_id: UUID
    provider_name: str
    is_healthy: bool
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    avg_latency_ms: int = 0


# ===============================
# LLM Routing Manager
# ===============================

class LLMRoutingManager:
    """
    Intelligent LLM routing with power levels, cost optimization, and failover.
    
    Features:
    - WilmerAI-style weighted scoring (cost 0.4, latency 0.4, quality 0.2)
    - Power level routing (ECO/BALANCED/PRECISION)
    - Provider health monitoring and failover
    - BYOK key management integration
    - Usage logging for billing/analytics
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._provider_health_cache: Dict[UUID, ProviderHealth] = {}
        self._cache_ttl_seconds = 60  # Refresh health every minute
        self._last_cache_refresh: Optional[datetime] = None
    
    # ===============================
    # Provider Selection & Routing
    # ===============================
    
    async def select_optimal_provider(
        self,
        user_id: UUID,
        power_level: str = PowerLevel.BALANCED,
        task_type: Optional[str] = None,
        routing_config: Optional[RoutingConfig] = None
    ) -> Optional[ModelScore]:
        """
        Select the optimal provider/model based on power level and routing strategy.
        
        Args:
            user_id: User requesting the routing
            power_level: ECO, BALANCED, or PRECISION
            task_type: Optional task type for specialized routing
            routing_config: Custom routing config (uses user's default if None)
        
        Returns:
            ModelScore with the best provider/model, or None if none available
        """
        try:
            # Get user's routing config if not provided
            if routing_config is None:
                routing_config = await self._get_user_routing_config(user_id)
            
            # Get available models for power level
            available_models = await self._get_available_models(
                user_id=user_id,
                power_level=power_level,
                task_type=task_type
            )
            
            if not available_models:
                logger.warning(f"No available models for user {user_id}, power level {power_level}")
                return None
            
            # Score all models
            scored_models = await self._score_models(
                models=available_models,
                routing_config=routing_config
            )
            
            if not scored_models:
                logger.warning(f"No models passed scoring for user {user_id}")
                return None
            
            # Sort by composite score (higher is better) and provider priority
            scored_models.sort(
                key=lambda m: (m.composite_score, m.priority),
                reverse=True
            )
            
            # Return top model
            best_model = scored_models[0]
            
            logger.info(
                f"Selected model {best_model.model_name} (provider: {best_model.provider_name}) "
                f"for user {user_id}, power level {power_level}. "
                f"Score: {best_model.composite_score:.3f}"
            )
            
            return best_model
            
        except Exception as e:
            logger.error(f"Error selecting optimal provider: {e}", exc_info=True)
            return None
    
    async def route_with_fallback(
        self,
        user_id: UUID,
        power_level: str = PowerLevel.BALANCED,
        max_attempts: int = 3
    ) -> List[ModelScore]:
        """
        Get a fallback chain of providers in priority order.
        
        Args:
            user_id: User requesting routing
            power_level: ECO, BALANCED, or PRECISION
            max_attempts: Maximum number of fallback options
        
        Returns:
            List of ModelScore objects in priority order
        """
        try:
            routing_config = await self._get_user_routing_config(user_id)
            available_models = await self._get_available_models(
                user_id=user_id,
                power_level=power_level
            )
            
            if not available_models:
                return []
            
            scored_models = await self._score_models(
                models=available_models,
                routing_config=routing_config
            )
            
            # Sort and return top N
            scored_models.sort(
                key=lambda m: (m.composite_score, m.priority),
                reverse=True
            )
            
            return scored_models[:max_attempts]
            
        except Exception as e:
            logger.error(f"Error getting fallback chain: {e}", exc_info=True)
            return []
    
    # ===============================
    # Model Scoring
    # ===============================
    
    async def _score_models(
        self,
        models: List[Dict[str, Any]],
        routing_config: RoutingConfig
    ) -> List[ModelScore]:
        """
        Score models using WilmerAI-style weighted composite scoring.
        
        Scoring formula:
        - Cost score: 1 - (cost / max_cost) [normalized, higher = cheaper]
        - Latency score: 1 - (latency / max_latency) [normalized, higher = faster]
        - Quality score: quality_rating / 10 [0-1 range]
        - Composite: (cost * cost_weight) + (latency * latency_weight) + (quality * quality_weight)
        """
        if not models:
            return []
        
        # Refresh provider health if needed
        await self._refresh_provider_health()
        
        # Filter out unhealthy providers
        healthy_models = []
        for model in models:
            provider_health = self._provider_health_cache.get(model['provider_id'])
            if provider_health and provider_health.is_healthy:
                healthy_models.append(model)
            elif not provider_health:
                # Unknown health, assume healthy (give it a chance)
                healthy_models.append(model)
        
        if not healthy_models:
            logger.warning("All providers unhealthy, falling back to all models")
            healthy_models = models
        
        # Calculate max values for normalization
        max_cost = max(
            float(m['input_cost_per_1m']) + float(m['output_cost_per_1m'])
            for m in healthy_models
        )
        max_latency = max(m['avg_latency_ms'] for m in healthy_models)
        
        # Avoid division by zero
        if max_cost == 0:
            max_cost = 1.0
        if max_latency == 0:
            max_latency = 1
        
        # Score each model
        scored = []
        for model in healthy_models:
            total_cost = float(model['input_cost_per_1m']) + float(model['output_cost_per_1m'])
            
            # Normalized scores (0-1 range, higher is better)
            cost_score = 1.0 - (total_cost / max_cost)
            latency_score = 1.0 - (model['avg_latency_ms'] / max_latency)
            quality_score = model['quality_score'] / 10.0  # Already 0-10, normalize to 0-1
            
            # Weighted composite score
            composite_score = (
                cost_score * routing_config.cost_weight +
                latency_score * routing_config.latency_weight +
                quality_score * routing_config.quality_weight
            )
            
            scored.append(ModelScore(
                model_id=model['model_id'],
                provider_id=model['provider_id'],
                model_name=model['model_name'],
                provider_name=model['provider_name'],
                composite_score=composite_score,
                cost_score=cost_score,
                latency_score=latency_score,
                quality_score=quality_score,
                input_cost_per_1m=model['input_cost_per_1m'],
                output_cost_per_1m=model['output_cost_per_1m'],
                avg_latency_ms=model['avg_latency_ms'],
                quality_rating=model['quality_score'],
                priority=model['priority']
            ))
        
        return scored
    
    # ===============================
    # Database Queries
    # ===============================
    
    async def _get_available_models(
        self,
        user_id: UUID,
        power_level: str,
        task_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available models filtered by power level and user's BYOK keys.
        
        Returns models from:
        1. Providers where user has BYOK keys
        2. Providers that are public/default (like OpenRouter with platform key)
        """
        query = """
            SELECT 
                m.id as model_id,
                m.provider_id,
                m.model_name,
                m.power_level,
                m.input_cost_per_1m,
                m.output_cost_per_1m,
                m.avg_latency_ms,
                m.quality_score,
                m.supports_streaming,
                m.max_context_tokens,
                m.capabilities,
                p.name as provider_name,
                p.priority,
                p.api_endpoint,
                p.is_enabled as provider_enabled,
                upk.id as user_has_key
            FROM llm_models m
            JOIN llm_providers p ON m.provider_id = p.id
            LEFT JOIN user_provider_keys upk ON upk.provider_id = p.id AND upk.user_id = $1
            WHERE m.is_enabled = true
                AND p.is_enabled = true
                AND m.power_level = $2
                AND (
                    upk.id IS NOT NULL  -- User has BYOK key
                    OR p.requires_byok = false  -- Or provider is public
                )
            ORDER BY p.priority DESC, m.quality_score DESC
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, user_id, power_level)
            return [dict(row) for row in rows]
    
    async def _get_user_routing_config(self, user_id: UUID) -> RoutingConfig:
        """Get user's routing configuration or return defaults."""
        query = """
            SELECT routing_config
            FROM user_llm_settings
            WHERE user_id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
            if row and row['routing_config']:
                config_dict = row['routing_config']
                return RoutingConfig(**config_dict)
            else:
                # Return default config
                return RoutingConfig()
    
    async def _refresh_provider_health(self):
        """Refresh provider health cache from recent usage logs."""
        now = datetime.utcnow()
        
        # Check if cache is still valid
        if (self._last_cache_refresh and 
            (now - self._last_cache_refresh).total_seconds() < self._cache_ttl_seconds):
            return
        
        query = """
            SELECT 
                p.id as provider_id,
                p.name as provider_name,
                COUNT(CASE WHEN l.status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN l.status = 'error' THEN 1 END) as error_count,
                MAX(CASE WHEN l.status = 'success' THEN l.created_at END) as last_success,
                MAX(CASE WHEN l.status = 'error' THEN l.created_at END) as last_failure,
                AVG(CASE WHEN l.status = 'success' THEN l.latency_ms END)::int as avg_latency_ms
            FROM llm_providers p
            LEFT JOIN llm_usage_logs l ON l.provider_id = p.id 
                AND l.created_at > NOW() - INTERVAL '15 minutes'
            WHERE p.is_enabled = true
            GROUP BY p.id, p.name
        """
        
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query)
                
                for row in rows:
                    success_count = row['success_count'] or 0
                    error_count = row['error_count'] or 0
                    total_requests = success_count + error_count
                    
                    # Provider is healthy if:
                    # - No recent requests (give it a chance), OR
                    # - Success rate >= 80%
                    is_healthy = (
                        total_requests == 0 or 
                        (success_count / total_requests) >= 0.8
                    )
                    
                    # Count consecutive failures from most recent logs
                    consecutive_failures = 0
                    if row['last_failure']:
                        # Could query for exact count, but this is a simple heuristic
                        if not row['last_success'] or row['last_failure'] > row['last_success']:
                            consecutive_failures = error_count
                    
                    self._provider_health_cache[row['provider_id']] = ProviderHealth(
                        provider_id=row['provider_id'],
                        provider_name=row['provider_name'],
                        is_healthy=is_healthy,
                        last_success=row['last_success'],
                        last_failure=row['last_failure'],
                        consecutive_failures=consecutive_failures,
                        avg_latency_ms=row['avg_latency_ms'] or 0
                    )
            
            self._last_cache_refresh = now
            logger.debug(f"Refreshed provider health cache: {len(self._provider_health_cache)} providers")
            
        except Exception as e:
            logger.error(f"Error refreshing provider health: {e}", exc_info=True)
    
    # ===============================
    # Usage Logging
    # ===============================
    
    async def log_usage(
        self,
        user_id: UUID,
        provider_id: UUID,
        model_id: UUID,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> UUID:
        """
        Log LLM usage for billing and analytics.
        
        Args:
            user_id: User who made the request
            provider_id: Provider used
            model_id: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Request latency in milliseconds
            status: "success" or "error"
            error_message: Error details if status is "error"
        
        Returns:
            UUID of the created log entry
        """
        query = """
            INSERT INTO llm_usage_logs (
                user_id, provider_id, model_id, input_tokens, output_tokens,
                latency_ms, status, error_message
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    user_id, provider_id, model_id, input_tokens, output_tokens,
                    latency_ms, status, error_message
                )
                
                log_id = row['id']
                logger.info(
                    f"Logged LLM usage: user={user_id}, provider={provider_id}, "
                    f"tokens={input_tokens}+{output_tokens}, latency={latency_ms}ms, status={status}"
                )
                
                return log_id
                
        except Exception as e:
            logger.error(f"Error logging usage: {e}", exc_info=True)
            raise
    
    # ===============================
    # Provider Management
    # ===============================
    
    async def get_provider_status(self, provider_id: UUID) -> Optional[ProviderHealth]:
        """Get current health status for a provider."""
        await self._refresh_provider_health()
        return self._provider_health_cache.get(provider_id)
    
    async def get_all_provider_statuses(self) -> List[ProviderHealth]:
        """Get health status for all providers."""
        await self._refresh_provider_health()
        return list(self._provider_health_cache.values())
    
    async def mark_provider_failure(self, provider_id: UUID):
        """Mark a provider as failed (increments consecutive failures)."""
        if provider_id in self._provider_health_cache:
            health = self._provider_health_cache[provider_id]
            health.consecutive_failures += 1
            health.last_failure = datetime.utcnow()
            
            # Mark unhealthy after 3 consecutive failures
            if health.consecutive_failures >= 3:
                health.is_healthy = False
                logger.warning(
                    f"Provider {health.provider_name} marked unhealthy "
                    f"after {health.consecutive_failures} failures"
                )
    
    async def mark_provider_success(self, provider_id: UUID, latency_ms: int):
        """Mark a provider as successful (resets consecutive failures)."""
        if provider_id in self._provider_health_cache:
            health = self._provider_health_cache[provider_id]
            health.consecutive_failures = 0
            health.last_success = datetime.utcnow()
            health.is_healthy = True
            
            # Update rolling average latency
            if health.avg_latency_ms > 0:
                health.avg_latency_ms = int((health.avg_latency_ms * 0.8) + (latency_ms * 0.2))
            else:
                health.avg_latency_ms = latency_ms
