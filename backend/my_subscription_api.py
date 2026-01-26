"""
User Subscription Management API
Epic 5.0 - Authenticated endpoints for subscription management
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from subscription_manager_v2 import subscription_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/my-subscription", tags=["my-subscription"])


class SubscriptionResponse(BaseModel):
    id: int
    tier_code: str
    tier_name: str
    status: str
    billing_cycle: str
    current_period_end: Optional[str]
    cancel_at: Optional[str]
    price_monthly: str
    price_yearly: str
    api_calls_limit: int
    team_seats: int
    byok_enabled: bool
    priority_support: bool


class UpgradeRequest(BaseModel):
    tier_code: str
    billing_cycle: str  # 'monthly' or 'yearly'


class CancelRequest(BaseModel):
    at_period_end: bool = True
    reason: Optional[str] = None


async def get_current_user_id(request: Request) -> int:
    """Get current user ID from session"""
    from redis_session import redis_session_manager
    
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = redis_session_manager.get(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = session_data.get("user", {})
    user_id = user.get("id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in session")
    
    return user_id


@router.get("/", response_model=SubscriptionResponse)
async def get_my_subscription(user_id: int = Depends(get_current_user_id)):
    """
    Get current user's subscription details
    """
    try:
        subscription = await subscription_manager.get_user_subscription(user_id)
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        return SubscriptionResponse(
            id=subscription['id'],
            tier_code=subscription['tier_code'],
            tier_name=subscription['tier_name'],
            status=subscription['status'],
            billing_cycle=subscription['billing_cycle'],
            current_period_end=subscription['current_period_end'].isoformat() if subscription['current_period_end'] else None,
            cancel_at=subscription['cancel_at'].isoformat() if subscription['cancel_at'] else None,
            price_monthly=str(subscription['price_monthly']),
            price_yearly=str(subscription['price_yearly']),
            api_calls_limit=subscription['api_calls_limit'],
            team_seats=subscription['team_seats'],
            byok_enabled=subscription['byok_enabled'],
            priority_support=subscription['priority_support']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription")


@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Upgrade to a higher tier
    """
    try:
        result = await subscription_manager.upgrade_subscription(
            user_id=user_id,
            new_tier_code=request.tier_code,
            billing_cycle=request.billing_cycle,
            prorate=True
        )
        
        return {
            "status": "success",
            "message": f"Upgraded to {result['new_tier']}",
            "details": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error upgrading subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to upgrade subscription")


@router.post("/cancel")
async def cancel_subscription(
    request: CancelRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Cancel subscription
    """
    try:
        result = await subscription_manager.cancel_subscription(
            user_id=user_id,
            at_period_end=request.at_period_end
        )
        
        message = (
            f"Subscription will be canceled at end of billing period ({result['cancel_at'].isoformat()})"
            if request.at_period_end
            else "Subscription canceled immediately"
        )
        
        return {
            "status": "success",
            "message": message,
            "details": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/reactivate")
async def reactivate_subscription(user_id: int = Depends(get_current_user_id)):
    """
    Reactivate a canceled subscription before period end
    """
    try:
        import stripe
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            subscription = await conn.fetchrow("""
                SELECT stripe_subscription_id, cancel_at
                FROM user_subscriptions
                WHERE user_id = $1 AND status = 'active'
            """, user_id)
            
            if not subscription:
                raise HTTPException(status_code=404, detail="No subscription found")
            
            if not subscription['cancel_at']:
                raise HTTPException(status_code=400, detail="Subscription is not scheduled for cancellation")
            
            # Reactivate in Stripe
            stripe.Subscription.modify(
                subscription['stripe_subscription_id'],
                cancel_at_period_end=False
            )
            
            # Update database
            await conn.execute("""
                UPDATE user_subscriptions
                SET cancel_at = NULL, updated_at = NOW()
                WHERE user_id = $1
            """, user_id)
            
            logger.info(f"Reactivated subscription for user {user_id}")
            
            return {
                "status": "success",
                "message": "Subscription reactivated successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")


@router.get("/usage")
async def get_subscription_usage(user_id: int = Depends(get_current_user_id)):
    """
    Get current usage statistics for the subscription
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get subscription limits
            subscription = await conn.fetchrow("""
                SELECT 
                    us.current_period_start,
                    us.current_period_end,
                    st.api_calls_limit,
                    st.team_seats
                FROM user_subscriptions us
                JOIN subscription_tiers st ON us.tier_id = st.id
                WHERE us.user_id = $1
            """, user_id)
            
            if not subscription:
                raise HTTPException(status_code=404, detail="No subscription found")
            
            # Get actual usage (TODO: integrate with usage tracking system)
            # For now, return placeholder data
            
            return {
                "period_start": subscription['current_period_start'].isoformat() if subscription['current_period_start'] else None,
                "period_end": subscription['current_period_end'].isoformat() if subscription['current_period_end'] else None,
                "api_calls": {
                    "used": 0,  # TODO: Get from usage tracking
                    "limit": subscription['api_calls_limit'],
                    "percentage": 0
                },
                "team_seats": {
                    "used": 1,  # At least the user themselves
                    "limit": subscription['team_seats']
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage statistics")
