"""
LiteLLM Routing API v2 - Epic 3.1 Implementation

Enhanced multi-provider routing with:
- Power level routing (ECO/BALANCED/PRECISION)  
- WilmerAI-style cost/latency/quality optimization
- BYOK (Bring Your Own Key) with encryption
- Provider health monitoring and failover
- Usage analytics and cost tracking

Author: Ops Center Team
Version: 2.0.0
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field, validator
import asyncpg
import httpx

from auth_dependencies import require_authenticated_user, require_admin_user
from byok_manager import BYOKManager
from llm_routing_manager import LLMRoutingManager, PowerLevel, RoutingConfig, ModelScore

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v2/llm", tags=["LLM Routing v2"])

# Environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "ops-center-postgresql")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "unicorn")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "unicorn_db")

LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://unicorn-litellm:4000")

# Database pool (initialized at startup)
db_pool: Optional[asyncpg.Pool] = None


# ===============================
# Request/Response Models
# ===============================

class ProviderCreateRequest(BaseModel):
    """Request to create a new provider"""
    name: str = Field(..., max_length=100)
    provider_type: str = Field(..., max_length=50)
    api_endpoint: str
    requires_byok: bool = True
    is_enabled: bool = True
    priority: int = Field(default=50, ge=0, le=100)
    config: Dict[str, Any] = Field(default_factory=dict)


class ProviderUpdateRequest(BaseModel):
    """Request to update an existing provider"""
    is_enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    config: Optional[Dict[str, Any]] = None
    api_endpoint: Optional[str] = None


class ProviderResponse(BaseModel):
    """Provider response"""
    id: UUID
    name: str
    provider_type: str
    api_endpoint: str
    requires_byok: bool
    is_enabled: bool
    priority: int
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ModelResponse(BaseModel):
    """Model response"""
    id: UUID
    provider_id: UUID
    provider_name: str
    model_name: str
    power_level: str
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    avg_latency_ms: int
    quality_score: Decimal
    supports_streaming: bool
    max_context_tokens: int
    capabilities: List[str]
    is_enabled: bool


class BYOKKeyRequest(BaseModel):
    """Request to store a BYOK API key"""
    provider_id: UUID
    api_key: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class BYOKKeyResponse(BaseModel):
    """BYOK key response (does not include actual key)"""
    id: UUID
    provider_id: UUID
    provider_name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserSettingsRequest(BaseModel):
    """Request to update user LLM settings"""
    preferred_power_level: Optional[str] = Field(None, pattern="^(ECO|BALANCED|PRECISION)$")
    routing_config: Optional[RoutingConfig] = None
    monthly_budget_usd: Optional[Decimal] = Field(None, ge=0)


class UserSettingsResponse(BaseModel):
    """User LLM settings response"""
    user_id: UUID
    preferred_power_level: str
    routing_config: RoutingConfig
    monthly_budget_usd: Optional[Decimal]
    current_month_spend: Decimal


class RoutingRequest(BaseModel):
    """Request for intelligent routing"""
    power_level: Optional[str] = Field(None, pattern="^(ECO|BALANCED|PRECISION)$")
    task_type: Optional[str] = None
    fallback_count: int = Field(default=3, ge=1, le=5)


class RoutingResponse(BaseModel):
    """Routing recommendation response"""
    primary: ModelScore
    fallbacks: List[ModelScore]
    total_options: int


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""
    user_id: UUID
    period_start: datetime
    period_end: datetime
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: Decimal
    by_provider: Dict[str, Dict[str, Any]]
    by_power_level: Dict[str, Dict[str, Any]]


# ===============================
# Dependency: Get Services
# ===============================

async def get_routing_manager() -> LLMRoutingManager:
    """Get LLM routing manager instance"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return LLMRoutingManager(db_pool)


async def get_byok_manager() -> BYOKManager:
    """Get BYOK manager instance"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return BYOKManager(db_pool)


# ===============================
# Provider Management Endpoints
# ===============================

@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(
    enabled_only: bool = False,
    current_user = Depends(require_admin_user)
):
    """
    List all LLM providers.
    
    Admin only endpoint.
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT id, name, provider_type, api_endpoint, requires_byok,
                       is_enabled, priority, config, created_at, updated_at
                FROM llm_providers
                WHERE ($1 = false OR is_enabled = true)
                ORDER BY priority DESC, name ASC
            """
            rows = await conn.fetch(query, enabled_only)
            
            return [ProviderResponse(**dict(row)) for row in rows]
            
    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list providers")


@router.post("/providers", response_model=ProviderResponse)
async def create_provider(
    request: ProviderCreateRequest,
    current_user = Depends(require_admin_user)
):
    """
    Create a new LLM provider.
    
    Admin only endpoint.
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                INSERT INTO llm_providers (
                    name, provider_type, api_endpoint, requires_byok,
                    is_enabled, priority, config
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, name, provider_type, api_endpoint, requires_byok,
                          is_enabled, priority, config, created_at, updated_at
            """
            row = await conn.fetchrow(
                query,
                request.name, request.provider_type, request.api_endpoint,
                request.requires_byok, request.is_enabled, request.priority,
                json.dumps(request.config)
            )
            
            logger.info(f"Created provider: {request.name} (admin: {current_user['user_id']})")
            return ProviderResponse(**dict(row))
            
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail=f"Provider '{request.name}' already exists")
    except Exception as e:
        logger.error(f"Error creating provider: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create provider")


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    request: ProviderUpdateRequest,
    current_user = Depends(require_admin_user)
):
    """
    Update an existing provider.
    
    Admin only endpoint.
    """
    try:
        async with db_pool.acquire() as conn:
            # Build dynamic update query
            updates = []
            params = [provider_id]
            param_idx = 2
            
            if request.is_enabled is not None:
                updates.append(f"is_enabled = ${param_idx}")
                params.append(request.is_enabled)
                param_idx += 1
            
            if request.priority is not None:
                updates.append(f"priority = ${param_idx}")
                params.append(request.priority)
                param_idx += 1
            
            if request.config is not None:
                updates.append(f"config = ${param_idx}")
                params.append(json.dumps(request.config))
                param_idx += 1
            
            if request.api_endpoint is not None:
                updates.append(f"api_endpoint = ${param_idx}")
                params.append(request.api_endpoint)
                param_idx += 1
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append(f"updated_at = NOW()")
            
            query = f"""
                UPDATE llm_providers
                SET {', '.join(updates)}
                WHERE id = $1
                RETURNING id, name, provider_type, api_endpoint, requires_byok,
                          is_enabled, priority, config, created_at, updated_at
            """
            
            row = await conn.fetchrow(query, *params)
            
            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")
            
            logger.info(f"Updated provider {provider_id} (admin: {current_user['user_id']})")
            return ProviderResponse(**dict(row))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating provider: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update provider")


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: UUID,
    current_user = Depends(require_admin_user)
):
    """
    Delete a provider (soft delete - just disables it).
    
    Admin only endpoint.
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                UPDATE llm_providers
                SET is_enabled = false, updated_at = NOW()
                WHERE id = $1
                RETURNING name
            """
            row = await conn.fetchrow(query, provider_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="Provider not found")
            
            logger.info(f"Disabled provider {provider_id} (admin: {current_user['user_id']})")
            return {"message": f"Provider '{row['name']}' disabled successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting provider: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete provider")


# ===============================
# Model Catalog Endpoints
# ===============================

@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    power_level: Optional[str] = None,
    provider_id: Optional[UUID] = None,
    enabled_only: bool = True,
    current_user = Depends(require_authenticated_user)
):
    """
    List available LLM models.
    
    Filters:
    - power_level: ECO, BALANCED, or PRECISION
    - provider_id: Filter by provider
    - enabled_only: Only return enabled models
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    m.id, m.provider_id, m.model_name, m.power_level,
                    m.input_cost_per_1m, m.output_cost_per_1m, m.avg_latency_ms,
                    m.quality_score, m.supports_streaming, m.max_context_tokens,
                    m.capabilities, m.is_enabled,
                    p.name as provider_name
                FROM llm_models m
                JOIN llm_providers p ON m.provider_id = p.id
                WHERE ($1::text IS NULL OR m.power_level = $1)
                  AND ($2::uuid IS NULL OR m.provider_id = $2)
                  AND ($3 = false OR m.is_enabled = true)
                  AND p.is_enabled = true
                ORDER BY m.power_level ASC, m.quality_score DESC, m.model_name ASC
            """
            rows = await conn.fetch(query, power_level, provider_id, enabled_only)
            
            return [ModelResponse(**dict(row)) for row in rows]
            
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list models")


# ===============================
# BYOK Management Endpoints
# ===============================

@router.post("/byok", response_model=BYOKKeyResponse)
async def store_byok_key(
    request: BYOKKeyRequest,
    current_user = Depends(require_authenticated_user),
    byok_manager: BYOKManager = Depends(get_byok_manager)
):
    """
    Store a BYOK (Bring Your Own Key) API key for a provider.
    
    The key is encrypted before storage using Fernet symmetric encryption.
    """
    try:
        user_id = UUID(current_user['user_id'])
        
        # Store encrypted key
        key_id = await byok_manager.store_user_api_key(
            user_id=user_id,
            provider_id=request.provider_id,
            api_key=request.api_key,
            metadata=request.metadata or {}
        )
        
        # Get provider name and key prefix for response
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    upk.id, upk.provider_id, upk.key_prefix, upk.is_active,
                    upk.created_at, upk.updated_at,
                    p.name as provider_name
                FROM user_provider_keys upk
                JOIN llm_providers p ON upk.provider_id = p.id
                WHERE upk.id = $1
            """
            row = await conn.fetchrow(query, key_id)
            
            if not row:
                raise HTTPException(status_code=500, detail="Failed to retrieve stored key")
            
            logger.info(f"Stored BYOK key for user {user_id}, provider {request.provider_id}")
            return BYOKKeyResponse(**dict(row))
            
    except Exception as e:
        logger.error(f"Error storing BYOK key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store API key")


@router.get("/byok", response_model=List[BYOKKeyResponse])
async def list_byok_keys(
    current_user = Depends(require_authenticated_user)
):
    """
    List all BYOK keys for the current user.
    
    Returns metadata only - never returns the actual API keys.
    """
    try:
        user_id = UUID(current_user['user_id'])
        
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    upk.id, upk.provider_id, upk.key_prefix, upk.is_active,
                    upk.created_at, upk.updated_at,
                    p.name as provider_name
                FROM user_provider_keys upk
                JOIN llm_providers p ON upk.provider_id = p.id
                WHERE upk.user_id = $1
                ORDER BY p.name ASC
            """
            rows = await conn.fetch(query, user_id)
            
            return [BYOKKeyResponse(**dict(row)) for row in rows]
            
    except Exception as e:
        logger.error(f"Error listing BYOK keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.delete("/byok/{key_id}")
async def delete_byok_key(
    key_id: UUID,
    current_user = Depends(require_authenticated_user),
    byok_manager: BYOKManager = Depends(get_byok_manager)
):
    """
    Delete a BYOK API key.
    """
    try:
        user_id = UUID(current_user['user_id'])
        
        # Verify ownership
        async with db_pool.acquire() as conn:
            query = "SELECT provider_id FROM user_provider_keys WHERE id = $1 AND user_id = $2"
            row = await conn.fetchrow(query, key_id, user_id)
            
            if not row:
                raise HTTPException(status_code=404, detail="API key not found")
            
            provider_id = row['provider_id']
        
        # Delete key
        await byok_manager.delete_user_api_key(user_id, provider_id)
        
        logger.info(f"Deleted BYOK key {key_id} for user {user_id}")
        return {"message": "API key deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting BYOK key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete API key")


# ===============================
# User Settings Endpoints
# ===============================

@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user = Depends(require_authenticated_user)
):
    """Get current user's LLM settings"""
    try:
        user_id = UUID(current_user['user_id'])
        
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    user_id, preferred_power_level, routing_config,
                    monthly_budget_usd
                FROM user_llm_settings
                WHERE user_id = $1
            """
            row = await conn.fetchrow(query, user_id)
            
            if not row:
                # Return defaults if no settings exist
                return UserSettingsResponse(
                    user_id=user_id,
                    preferred_power_level="BALANCED",
                    routing_config=RoutingConfig(),
                    monthly_budget_usd=None,
                    current_month_spend=Decimal("0.00")
                )
            
            # Get current month spend
            spend_query = """
                SELECT COALESCE(SUM(
                    (input_tokens::decimal / 1000000) * m.input_cost_per_1m +
                    (output_tokens::decimal / 1000000) * m.output_cost_per_1m
                ), 0) as total_spend
                FROM llm_usage_logs l
                JOIN llm_models m ON l.model_id = m.id
                WHERE l.user_id = $1
                  AND l.created_at >= date_trunc('month', CURRENT_DATE)
                  AND l.status = 'success'
            """
            spend_row = await conn.fetchrow(spend_query, user_id)
            current_month_spend = spend_row['total_spend'] if spend_row else Decimal("0.00")
            
            return UserSettingsResponse(
                user_id=row['user_id'],
                preferred_power_level=row['preferred_power_level'],
                routing_config=RoutingConfig(**row['routing_config']),
                monthly_budget_usd=row['monthly_budget_usd'],
                current_month_spend=current_month_spend
            )
            
    except Exception as e:
        logger.error(f"Error getting user settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get settings")


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    request: UserSettingsRequest,
    current_user = Depends(require_authenticated_user)
):
    """Update current user's LLM settings"""
    try:
        user_id = UUID(current_user['user_id'])
        
        async with db_pool.acquire() as conn:
            # Upsert settings
            query = """
                INSERT INTO user_llm_settings (
                    user_id, preferred_power_level, routing_config, monthly_budget_usd
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    preferred_power_level = COALESCE($2, user_llm_settings.preferred_power_level),
                    routing_config = COALESCE($3, user_llm_settings.routing_config),
                    monthly_budget_usd = COALESCE($4, user_llm_settings.monthly_budget_usd),
                    updated_at = NOW()
                RETURNING user_id, preferred_power_level, routing_config, monthly_budget_usd
            """
            
            routing_config_json = request.routing_config.dict() if request.routing_config else None
            
            row = await conn.fetchrow(
                query,
                user_id,
                request.preferred_power_level,
                json.dumps(routing_config_json) if routing_config_json else None,
                request.monthly_budget_usd
            )
            
            # Get current month spend
            spend_query = """
                SELECT COALESCE(SUM(
                    (input_tokens::decimal / 1000000) * m.input_cost_per_1m +
                    (output_tokens::decimal / 1000000) * m.output_cost_per_1m
                ), 0) as total_spend
                FROM llm_usage_logs l
                JOIN llm_models m ON l.model_id = m.id
                WHERE l.user_id = $1
                  AND l.created_at >= date_trunc('month', CURRENT_DATE)
                  AND l.status = 'success'
            """
            spend_row = await conn.fetchrow(spend_query, user_id)
            current_month_spend = spend_row['total_spend'] if spend_row else Decimal("0.00")
            
            logger.info(f"Updated settings for user {user_id}")
            
            return UserSettingsResponse(
                user_id=row['user_id'],
                preferred_power_level=row['preferred_power_level'],
                routing_config=RoutingConfig(**row['routing_config']),
                monthly_budget_usd=row['monthly_budget_usd'],
                current_month_spend=current_month_spend
            )
            
    except Exception as e:
        logger.error(f"Error updating user settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update settings")


# ===============================
# Intelligent Routing Endpoints
# ===============================

@router.post("/route", response_model=RoutingResponse)
async def get_routing_recommendation(
    request: RoutingRequest,
    current_user = Depends(require_authenticated_user),
    routing_manager: LLMRoutingManager = Depends(get_routing_manager)
):
    """
    Get intelligent routing recommendation based on power level and user settings.
    
    Returns the optimal model/provider plus fallback options.
    """
    try:
        user_id = UUID(current_user['user_id'])
        
        # Use user's preferred power level if not specified
        power_level = request.power_level
        if not power_level:
            async with db_pool.acquire() as conn:
                query = "SELECT preferred_power_level FROM user_llm_settings WHERE user_id = $1"
                row = await conn.fetchrow(query, user_id)
                power_level = row['preferred_power_level'] if row else PowerLevel.BALANCED
        
        # Get primary recommendation
        primary = await routing_manager.select_optimal_provider(
            user_id=user_id,
            power_level=power_level,
            task_type=request.task_type
        )
        
        if not primary:
            raise HTTPException(
                status_code=404,
                detail=f"No available providers for power level {power_level}"
            )
        
        # Get fallback chain
        fallbacks = await routing_manager.route_with_fallback(
            user_id=user_id,
            power_level=power_level,
            max_attempts=request.fallback_count + 1  # Include primary
        )
        
        # Remove primary from fallbacks
        fallbacks = [f for f in fallbacks if f.model_id != primary.model_id][:request.fallback_count]
        
        logger.info(
            f"Routing recommendation for user {user_id}: "
            f"primary={primary.model_name}, fallbacks={len(fallbacks)}"
        )
        
        return RoutingResponse(
            primary=primary,
            fallbacks=fallbacks,
            total_options=len(fallbacks) + 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting routing recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get routing recommendation")


# ===============================
# Usage Analytics Endpoints
# ===============================

@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = 30,
    current_user = Depends(require_authenticated_user)
):
    """
    Get usage statistics for the current user.
    
    Includes:
    - Total requests, tokens, and cost
    - Breakdown by provider
    - Breakdown by power level
    """
    try:
        user_id = UUID(current_user['user_id'])
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            # Overall stats
            overall_query = """
                SELECT 
                    COUNT(*) as total_requests,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(
                        (input_tokens::decimal / 1000000) * m.input_cost_per_1m +
                        (output_tokens::decimal / 1000000) * m.output_cost_per_1m
                    ), 0) as total_cost_usd
                FROM llm_usage_logs l
                JOIN llm_models m ON l.model_id = m.id
                WHERE l.user_id = $1
                  AND l.created_at >= $2
                  AND l.created_at <= $3
                  AND l.status = 'success'
            """
            overall = await conn.fetchrow(overall_query, user_id, period_start, period_end)
            
            # By provider
            provider_query = """
                SELECT 
                    p.name as provider_name,
                    COUNT(*) as requests,
                    COALESCE(SUM(l.input_tokens), 0) as input_tokens,
                    COALESCE(SUM(l.output_tokens), 0) as output_tokens,
                    COALESCE(SUM(
                        (l.input_tokens::decimal / 1000000) * m.input_cost_per_1m +
                        (l.output_tokens::decimal / 1000000) * m.output_cost_per_1m
                    ), 0) as cost_usd,
                    AVG(l.latency_ms)::int as avg_latency_ms
                FROM llm_usage_logs l
                JOIN llm_models m ON l.model_id = m.id
                JOIN llm_providers p ON l.provider_id = p.id
                WHERE l.user_id = $1
                  AND l.created_at >= $2
                  AND l.created_at <= $3
                  AND l.status = 'success'
                GROUP BY p.name
                ORDER BY cost_usd DESC
            """
            provider_rows = await conn.fetch(provider_query, user_id, period_start, period_end)
            
            by_provider = {}
            for row in provider_rows:
                by_provider[row['provider_name']] = {
                    "requests": row['requests'],
                    "input_tokens": row['input_tokens'],
                    "output_tokens": row['output_tokens'],
                    "cost_usd": float(row['cost_usd']),
                    "avg_latency_ms": row['avg_latency_ms']
                }
            
            # By power level
            power_level_query = """
                SELECT 
                    m.power_level,
                    COUNT(*) as requests,
                    COALESCE(SUM(l.input_tokens), 0) as input_tokens,
                    COALESCE(SUM(l.output_tokens), 0) as output_tokens,
                    COALESCE(SUM(
                        (l.input_tokens::decimal / 1000000) * m.input_cost_per_1m +
                        (l.output_tokens::decimal / 1000000) * m.output_cost_per_1m
                    ), 0) as cost_usd
                FROM llm_usage_logs l
                JOIN llm_models m ON l.model_id = m.id
                WHERE l.user_id = $1
                  AND l.created_at >= $2
                  AND l.created_at <= $3
                  AND l.status = 'success'
                GROUP BY m.power_level
                ORDER BY cost_usd DESC
            """
            power_level_rows = await conn.fetch(power_level_query, user_id, period_start, period_end)
            
            by_power_level = {}
            for row in power_level_rows:
                by_power_level[row['power_level']] = {
                    "requests": row['requests'],
                    "input_tokens": row['input_tokens'],
                    "output_tokens": row['output_tokens'],
                    "cost_usd": float(row['cost_usd'])
                }
            
            return UsageStatsResponse(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                total_requests=overall['total_requests'],
                total_input_tokens=overall['total_input_tokens'],
                total_output_tokens=overall['total_output_tokens'],
                total_cost_usd=overall['total_cost_usd'],
                by_provider=by_provider,
                by_power_level=by_power_level
            )
            
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get usage statistics")


# ===============================
# Initialization
# ===============================

async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    
    try:
        db_pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=int(POSTGRES_PORT),
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database pool initialized for LLM Routing API v2")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}", exc_info=True)
        raise


async def close_db_pool():
    """Close database connection pool"""
    global db_pool
    
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed for LLM Routing API v2")
