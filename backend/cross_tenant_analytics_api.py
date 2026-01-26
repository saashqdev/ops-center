"""
Cross-Tenant Analytics API

Provides platform-wide analytics and monitoring across all tenants.
Only accessible by platform administrators.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
import asyncpg
from auth_dependencies import require_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/analytics", tags=["cross-tenant-analytics"])


# Pydantic models
class PlatformStats(BaseModel):
    """Platform-wide statistics"""
    total_tenants: int
    active_tenants: int
    total_users: int
    total_devices: int
    total_webhooks: int
    total_api_keys: int
    tier_distribution: Dict[str, int]
    growth_stats: Dict[str, Any]


class TenantMetric(BaseModel):
    """Single metric for a tenant"""
    organization_id: str
    organization_name: str
    metric_type: str
    metric_value: float
    timestamp: datetime


class TenantRanking(BaseModel):
    """Tenant ranking by metric"""
    organization_id: str
    organization_name: str
    plan_tier: str
    metric_value: float
    rank: int


class ResourceUtilization(BaseModel):
    """Resource utilization across platform"""
    resource_type: str
    total_usage: int
    quota_limit: int
    utilization_percent: float
    by_tier: Dict[str, int]


class GrowthMetrics(BaseModel):
    """Growth metrics over time"""
    period: str  # day, week, month
    new_tenants: int
    churned_tenants: int
    new_users: int
    new_devices: int
    growth_rate_percent: float


# Database helpers
async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL not configured"
        )
    
    try:
        pool = await asyncpg.create_pool(db_url)
        return pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )


# API endpoints
@router.get("/platform-stats", response_model=PlatformStats)
async def get_platform_stats(
    user: dict = Depends(require_admin_user)
):
    """
    Get platform-wide statistics
    
    Includes total counts, tier distribution, and growth metrics
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Total tenants
            total_tenants = await conn.fetchval(
                "SELECT COUNT(*) FROM organizations"
            )
            
            active_tenants = await conn.fetchval(
                "SELECT COUNT(*) FROM organizations WHERE is_active = true"
            )
            
            # Total users
            total_users = await conn.fetchval(
                "SELECT COUNT(*) FROM users"
            )
            
            # Total devices
            total_devices = await conn.fetchval(
                "SELECT COUNT(*) FROM edge_devices"
            )
            
            # Total webhooks
            total_webhooks = await conn.fetchval(
                "SELECT COUNT(*) FROM webhooks"
            )
            
            # Total API keys
            total_api_keys = await conn.fetchval(
                "SELECT COUNT(*) FROM api_keys"
            )
            
            # Tier distribution
            tier_rows = await conn.fetch(
                "SELECT plan_tier, COUNT(*) as count FROM organizations GROUP BY plan_tier"
            )
            tier_distribution = {row['plan_tier']: row['count'] for row in tier_rows}
            
            # Growth stats (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            new_tenants_30d = await conn.fetchval(
                "SELECT COUNT(*) FROM organizations WHERE created_at >= $1",
                thirty_days_ago
            )
            
            new_users_30d = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at >= $1",
                thirty_days_ago
            )
            
            growth_stats = {
                "new_tenants_30d": new_tenants_30d,
                "new_users_30d": new_users_30d,
                "avg_users_per_tenant": total_users / total_tenants if total_tenants > 0 else 0,
                "avg_devices_per_tenant": total_devices / total_tenants if total_tenants > 0 else 0
            }
            
            return PlatformStats(
                total_tenants=total_tenants,
                active_tenants=active_tenants,
                total_users=total_users,
                total_devices=total_devices,
                total_webhooks=total_webhooks,
                total_api_keys=total_api_keys,
                tier_distribution=tier_distribution,
                growth_stats=growth_stats
            )
        
    finally:
        await pool.close()


@router.get("/top-tenants")
async def get_top_tenants(
    metric: str = Query("users", description="Metric to rank by: users, devices, webhooks, api_calls"),
    limit: int = Query(10, ge=1, le=100),
    user: dict = Depends(require_admin_user)
):
    """
    Get top tenants by specified metric
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Map metric to table and column
            metric_queries = {
                'users': "SELECT organization_id, COUNT(*) as count FROM users GROUP BY organization_id",
                'devices': "SELECT organization_id, COUNT(*) as count FROM edge_devices GROUP BY organization_id",
                'webhooks': "SELECT organization_id, COUNT(*) as count FROM webhooks GROUP BY organization_id",
                'api_keys': "SELECT organization_id, COUNT(*) as count FROM api_keys GROUP BY organization_id"
            }
            
            if metric not in metric_queries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid metric. Choose from: {list(metric_queries.keys())}"
                )
            
            # Get metric counts
            query = f"""
                WITH metric_counts AS (
                    {metric_queries[metric]}
                )
                SELECT 
                    o.organization_id,
                    o.name as organization_name,
                    o.plan_tier,
                    COALESCE(mc.count, 0) as metric_value,
                    ROW_NUMBER() OVER (ORDER BY COALESCE(mc.count, 0) DESC) as rank
                FROM organizations o
                LEFT JOIN metric_counts mc ON o.organization_id = mc.organization_id
                WHERE o.is_active = true
                ORDER BY metric_value DESC
                LIMIT $1
            """
            
            rows = await conn.fetch(query, limit)
            
            rankings = [
                TenantRanking(
                    organization_id=row['organization_id'],
                    organization_name=row['organization_name'],
                    plan_tier=row['plan_tier'],
                    metric_value=float(row['metric_value']),
                    rank=row['rank']
                )
                for row in rows
            ]
            
            return {
                "metric": metric,
                "rankings": rankings
            }
        
    finally:
        await pool.close()


@router.get("/resource-utilization")
async def get_resource_utilization(
    user: dict = Depends(require_admin_user)
):
    """
    Get resource utilization across all tenants
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            resources = []
            
            # Resource types to check
            resource_types = [
                ('users', 'users'),
                ('devices', 'edge_devices'),
                ('webhooks', 'webhooks'),
                ('api_keys', 'api_keys')
            ]
            
            for resource_name, table_name in resource_types:
                # Total usage
                total_query = f"SELECT COUNT(*) FROM {table_name}"
                total_usage = await conn.fetchval(total_query)
                
                # Usage by tier
                tier_query = f"""
                    SELECT o.plan_tier, COUNT(t.*) as count
                    FROM organizations o
                    LEFT JOIN {table_name} t ON o.organization_id = t.organization_id
                    GROUP BY o.plan_tier
                """
                tier_rows = await conn.fetch(tier_query)
                by_tier = {row['plan_tier']: row['count'] for row in tier_rows}
                
                # Placeholder quota limit (would come from tier definitions)
                quota_limit = 10000
                
                resources.append(ResourceUtilization(
                    resource_type=resource_name,
                    total_usage=total_usage,
                    quota_limit=quota_limit,
                    utilization_percent=(total_usage / quota_limit * 100) if quota_limit > 0 else 0,
                    by_tier=by_tier
                ))
            
            return {"resources": resources}
        
    finally:
        await pool.close()


@router.get("/growth-metrics")
async def get_growth_metrics(
    period: str = Query("month", description="Period: day, week, month"),
    user: dict = Depends(require_admin_user)
):
    """
    Get growth metrics for specified period
    """
    pool = await get_db_pool()
    
    try:
        # Determine time window
        period_days = {
            'day': 1,
            'week': 7,
            'month': 30
        }
        
        if period not in period_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Choose: day, week, month"
            )
        
        days = period_days[period]
        start_date = datetime.utcnow() - timedelta(days=days)
        prev_start_date = start_date - timedelta(days=days)
        
        async with pool.acquire() as conn:
            # New tenants in current period
            new_tenants = await conn.fetchval(
                "SELECT COUNT(*) FROM organizations WHERE created_at >= $1",
                start_date
            )
            
            # Churned tenants (deactivated)
            churned_tenants = await conn.fetchval(
                """
                SELECT COUNT(*) FROM organizations 
                WHERE is_active = false 
                AND updated_at >= $1
                """,
                start_date
            )
            
            # New users
            new_users = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at >= $1",
                start_date
            )
            
            # New devices
            new_devices = await conn.fetchval(
                "SELECT COUNT(*) FROM edge_devices WHERE registered_at >= $1",
                start_date
            )
            
            # Previous period counts for growth rate
            prev_tenants = await conn.fetchval(
                "SELECT COUNT(*) FROM organizations WHERE created_at >= $1 AND created_at < $2",
                prev_start_date, start_date
            )
            
            # Calculate growth rate
            growth_rate = 0.0
            if prev_tenants > 0:
                growth_rate = ((new_tenants - prev_tenants) / prev_tenants) * 100
            
            return GrowthMetrics(
                period=period,
                new_tenants=new_tenants,
                churned_tenants=churned_tenants,
                new_users=new_users,
                new_devices=new_devices,
                growth_rate_percent=growth_rate
            )
        
    finally:
        await pool.close()


@router.post("/record-metric")
async def record_tenant_metric(
    organization_id: str,
    metric_type: str,
    metric_value: float,
    metadata: Optional[Dict[str, Any]] = None,
    user: dict = Depends(require_admin_user)
):
    """
    Record a custom metric for a tenant
    
    Used for tracking custom analytics events
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            query = """
                INSERT INTO tenant_analytics (
                    organization_id, metric_type, metric_value, metadata, timestamp
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            
            metric_id = await conn.fetchval(
                query,
                organization_id,
                metric_type,
                metric_value,
                metadata or {},
                datetime.utcnow()
            )
            
            return {
                "message": "Metric recorded successfully",
                "metric_id": metric_id,
                "organization_id": organization_id,
                "metric_type": metric_type
            }
        
    finally:
        await pool.close()


@router.get("/tenant-metrics/{organization_id}")
async def get_tenant_metrics(
    organization_id: str,
    metric_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(require_admin_user)
):
    """
    Get metrics for a specific tenant
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Build query
            conditions = ["ta.organization_id = $1"]
            params = [organization_id]
            param_count = 2
            
            if metric_type:
                conditions.append(f"ta.metric_type = ${param_count}")
                params.append(metric_type)
                param_count += 1
            
            if start_date:
                conditions.append(f"ta.timestamp >= ${param_count}")
                params.append(start_date)
                param_count += 1
            
            if end_date:
                conditions.append(f"ta.timestamp <= ${param_count}")
                params.append(end_date)
                param_count += 1
            
            params.append(limit)
            
            query = f"""
                SELECT 
                    ta.*,
                    o.name as organization_name
                FROM tenant_analytics ta
                JOIN organizations o ON ta.organization_id = o.organization_id
                WHERE {' AND '.join(conditions)}
                ORDER BY ta.timestamp DESC
                LIMIT ${param_count}
            """
            
            rows = await conn.fetch(query, *params)
            
            metrics = [
                TenantMetric(
                    organization_id=row['organization_id'],
                    organization_name=row['organization_name'],
                    metric_type=row['metric_type'],
                    metric_value=row['metric_value'],
                    timestamp=row['timestamp']
                )
                for row in rows
            ]
            
            return {"metrics": metrics, "count": len(metrics)}
        
    finally:
        await pool.close()


@router.get("/tier-comparison")
async def get_tier_comparison(
    user: dict = Depends(require_admin_user)
):
    """
    Compare metrics across subscription tiers
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    o.plan_tier,
                    COUNT(DISTINCT o.organization_id) as tenant_count,
                    COUNT(DISTINCT u.user_id) as total_users,
                    COUNT(DISTINCT d.device_id) as total_devices,
                    COUNT(DISTINCT w.webhook_id) as total_webhooks,
                    AVG((SELECT COUNT(*) FROM users WHERE organization_id = o.organization_id)) as avg_users_per_tenant,
                    AVG((SELECT COUNT(*) FROM edge_devices WHERE organization_id = o.organization_id)) as avg_devices_per_tenant
                FROM organizations o
                LEFT JOIN users u ON o.organization_id = u.organization_id
                LEFT JOIN edge_devices d ON o.organization_id = d.organization_id
                LEFT JOIN webhooks w ON o.organization_id = w.webhook_id
                WHERE o.is_active = true
                GROUP BY o.plan_tier
                ORDER BY 
                    CASE o.plan_tier
                        WHEN 'trial' THEN 1
                        WHEN 'starter' THEN 2
                        WHEN 'professional' THEN 3
                        WHEN 'enterprise' THEN 4
                    END
            """
            
            rows = await conn.fetch(query)
            
            comparison = {}
            for row in rows:
                comparison[row['plan_tier']] = {
                    'tenant_count': row['tenant_count'],
                    'total_users': row['total_users'] or 0,
                    'total_devices': row['total_devices'] or 0,
                    'total_webhooks': row['total_webhooks'] or 0,
                    'avg_users_per_tenant': float(row['avg_users_per_tenant'] or 0),
                    'avg_devices_per_tenant': float(row['avg_devices_per_tenant'] or 0)
                }
            
            return {"tier_comparison": comparison}
        
    finally:
        await pool.close()
