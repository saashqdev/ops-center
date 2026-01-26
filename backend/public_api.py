"""
Public API Endpoints - No authentication required
These endpoints are used for public-facing pages like pricing, signup, etc.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public", tags=["Public"])


@router.get("/tiers")
async def get_public_tiers() -> List[Dict[str, Any]]:
    """
    Get all active subscription tiers for the public pricing page
    No authentication required
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            tiers = await conn.fetch("""
                SELECT 
                    id,
                    tier_code,
                    tier_name,
                    description,
                    price_monthly,
                    price_yearly,
                    api_calls_limit,
                    team_seats,
                    byok_enabled,
                    priority_support,
                    sort_order,
                    stripe_price_monthly,
                    stripe_price_yearly
                FROM subscription_tiers
                WHERE is_active = true
                ORDER BY sort_order ASC
            """)
            
            return [dict(tier) for tier in tiers]
            
    except Exception as e:
        logger.error(f"Error fetching public tiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription tiers")


@router.get("/tiers/{tier_code}/features")
async def get_tier_features(tier_code: str) -> List[Dict[str, Any]]:
    """
    Get all features for a specific tier
    No authentication required
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # First get the tier ID
            tier = await conn.fetchrow("""
                SELECT id FROM subscription_tiers
                WHERE tier_code = $1 AND is_active = true
            """, tier_code)
            
            if not tier:
                raise HTTPException(status_code=404, detail="Tier not found")
            
            # Get features for this tier
            features = await conn.fetch("""
                SELECT 
                    f.feature_name,
                    f.feature_key,
                    f.description,
                    f.category,
                    tf.enabled,
                    tf.limit_value,
                    tf.limit_unit
                FROM features f
                LEFT JOIN tier_features tf ON f.id = tf.feature_id AND tf.tier_id = $1
                WHERE f.is_active = true
                ORDER BY f.sort_order ASC
            """, tier['id'])
            
            return [dict(feature) for feature in features]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tier features: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tier features")


@router.get("/apps")
async def get_public_apps() -> List[Dict[str, Any]]:
    """
    Get all active apps for the public marketplace
    No authentication required
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            apps = await conn.fetch("""
                SELECT 
                    id,
                    app_key,
                    app_name,
                    description,
                    category,
                    sort_order
                FROM apps
                WHERE is_active = true
                ORDER BY sort_order ASC, app_name ASC
            """)
            
            return [dict(app) for app in apps]
            
    except Exception as e:
        logger.error(f"Error fetching public apps: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch apps")


@router.get("/apps/{app_key}/tiers")
async def get_app_availability(app_key: str) -> List[Dict[str, Any]]:
    """
    Get which tiers have access to a specific app
    No authentication required
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # First verify the app exists
            app = await conn.fetchrow("""
                SELECT id FROM apps WHERE app_key = $1 AND is_active = true
            """, app_key)
            
            if not app:
                raise HTTPException(status_code=404, detail="App not found")
            
            # Get tiers that have access to this app
            tiers = await conn.fetch("""
                SELECT 
                    st.tier_code,
                    st.tier_name,
                    st.price_monthly,
                    ta.enabled
                FROM subscription_tiers st
                INNER JOIN tier_apps ta ON st.id = ta.tier_id
                WHERE ta.app_id = $1 
                    AND st.is_active = true
                    AND ta.enabled = true
                ORDER BY st.sort_order ASC
            """, app['id'])
            
            return [dict(tier) for tier in tiers]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching app availability: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch app availability")


@router.get("/stats")
async def get_public_stats() -> Dict[str, Any]:
    """
    Get public statistics for the landing/pricing page
    No authentication required
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get total active users (for social proof)
            total_users = await conn.fetchval("""
                SELECT COUNT(*) FROM users WHERE is_active = true
            """)
            
            # Get total apps available
            total_apps = await conn.fetchval("""
                SELECT COUNT(*) FROM apps WHERE is_active = true
            """)
            
            # Get total tiers
            total_tiers = await conn.fetchval("""
                SELECT COUNT(*) FROM subscription_tiers WHERE is_active = true
            """)
            
            return {
                "total_users": total_users or 0,
                "total_apps": total_apps or 0,
                "total_tiers": total_tiers or 0,
                "uptime": "99.9%",  # You can integrate with actual monitoring
                "api_calls_served": 1000000  # You can integrate with actual metrics
            }
            
    except Exception as e:
        logger.error(f"Error fetching public stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
