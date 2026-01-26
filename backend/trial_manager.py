"""
Trial Management for Epic 5.0
Handles trial lifecycle: assignment, expiration, conversion tracking
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class TrialManager:
    """Manages trial subscriptions and conversions"""
    
    def __init__(self):
        self.default_trial_days = int(os.getenv('DEFAULT_TRIAL_DAYS', '14'))
        self.trial_tier_code = os.getenv('TRIAL_TIER_CODE', 'trial')
        self.free_tier_code = os.getenv('FREE_TIER_CODE', 'free')
    
    async def assign_trial_subscription(
        self,
        email: str,
        trial_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Assign a trial subscription to a new user
        
        Args:
            email: User email
            trial_days: Number of trial days (defaults to DEFAULT_TRIAL_DAYS)
            
        Returns:
            Dict with trial subscription details
        """
        try:
            from database import get_db_pool
            
            trial_days = trial_days or self.default_trial_days
            pool = await get_db_pool()
            
            async with pool.acquire() as conn:
                # Check if user already has a subscription
                existing = await conn.fetchrow("""
                    SELECT id FROM user_subscriptions WHERE email = $1
                """, email)
                
                if existing:
                    logger.warning(f"User {email} already has a subscription")
                    return {"error": "User already has a subscription"}
                
                # Get trial tier
                tier = await conn.fetchrow("""
                    SELECT id, code, name FROM subscription_tiers WHERE code = $1
                """, self.trial_tier_code)
                
                if not tier:
                    raise ValueError(f"Trial tier '{self.trial_tier_code}' not found")
                
                # Calculate trial period
                now = datetime.utcnow()
                trial_end = now + timedelta(days=trial_days)
                
                # Create trial subscription
                result = await conn.fetchrow("""
                    INSERT INTO user_subscriptions (
                        email,
                        tier_id,
                        status,
                        billing_cycle,
                        current_period_start,
                        current_period_end,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """, email, tier['id'], 'trialing', 'trial', now, trial_end, now)
                
                logger.info(f"Assigned {trial_days}-day trial to {email}, expires: {trial_end}")
                
                return {
                    "subscription_id": result['id'],
                    "email": email,
                    "tier_code": self.trial_tier_code,
                    "status": "trialing",
                    "trial_end": trial_end,
                    "days_remaining": trial_days
                }
                
        except Exception as e:
            logger.error(f"Error assigning trial: {e}", exc_info=True)
            raise
    
    async def check_trial_expiration(self) -> List[Dict[str, Any]]:
        """
        Check for expired trials and downgrade to free tier
        
        Returns:
            List of expired trials that were downgraded
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Find expired trials
                expired = await conn.fetch("""
                    SELECT id, email, current_period_end
                    FROM user_subscriptions
                    WHERE status = 'trialing'
                    AND current_period_end < NOW()
                """)
                
                if not expired:
                    logger.info("No expired trials found")
                    return []
                
                # Get free tier
                free_tier = await conn.fetchrow("""
                    SELECT id FROM subscription_tiers WHERE code = $1
                """, self.free_tier_code)
                
                if not free_tier:
                    logger.error(f"Free tier '{self.free_tier_code}' not found")
                    return []
                
                downgraded = []
                for sub in expired:
                    await conn.execute("""
                        UPDATE user_subscriptions
                        SET status = 'expired',
                            tier_id = $1,
                            updated_at = NOW()
                        WHERE id = $2
                    """, free_tier['id'], sub['id'])
                    
                    logger.info(f"Downgraded expired trial for {sub['email']}")
                    downgraded.append({
                        "email": sub['email'],
                        "expired_at": sub['current_period_end'],
                        "new_tier": self.free_tier_code
                    })
                    
                    # TODO: Send trial expired email
                
                return downgraded
                
        except Exception as e:
            logger.error(f"Error checking trial expiration: {e}", exc_info=True)
            return []
    
    async def get_expiring_trials(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get trials expiring within N days
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring trials
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                expiring = await conn.fetch("""
                    SELECT 
                        s.email,
                        s.current_period_end,
                        EXTRACT(DAY FROM (s.current_period_end - NOW())) as days_remaining
                    FROM user_subscriptions s
                    WHERE s.status = 'trialing'
                    AND s.current_period_end > NOW()
                    AND s.current_period_end <= NOW() + INTERVAL '%s days'
                    ORDER BY s.current_period_end ASC
                """ % days)
                
                return [dict(row) for row in expiring]
                
        except Exception as e:
            logger.error(f"Error getting expiring trials: {e}", exc_info=True)
            return []
    
    async def extend_trial(
        self,
        email: str,
        additional_days: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extend a trial subscription (admin override)
        
        Args:
            email: User email
            additional_days: Number of days to add
            reason: Reason for extension (audit log)
            
        Returns:
            Dict with new trial end date
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get current trial
                trial = await conn.fetchrow("""
                    SELECT id, current_period_end, status
                    FROM user_subscriptions
                    WHERE email = $1 AND status = 'trialing'
                """, email)
                
                if not trial:
                    raise ValueError(f"No active trial found for {email}")
                
                # Extend trial period
                new_end = trial['current_period_end'] + timedelta(days=additional_days)
                
                await conn.execute("""
                    UPDATE user_subscriptions
                    SET current_period_end = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, new_end, trial['id'])
                
                logger.info(f"Extended trial for {email} by {additional_days} days. Reason: {reason}")
                
                # TODO: Log to audit_logs table
                
                return {
                    "email": email,
                    "new_trial_end": new_end,
                    "days_added": additional_days,
                    "reason": reason
                }
                
        except Exception as e:
            logger.error(f"Error extending trial: {e}", exc_info=True)
            raise
    
    async def convert_trial_to_paid(
        self,
        email: str,
        stripe_subscription_id: str
    ) -> Dict[str, Any]:
        """
        Convert a trial to a paid subscription
        
        Args:
            email: User email
            stripe_subscription_id: Stripe subscription ID
            
        Returns:
            Dict with conversion details
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get trial subscription
                trial = await conn.fetchrow("""
                    SELECT id, tier_id FROM user_subscriptions
                    WHERE email = $1 AND status = 'trialing'
                """, email)
                
                if not trial:
                    logger.warning(f"No trial found for {email}, may be new subscription")
                    return {"converted": False}
                
                # Update to paid status
                await conn.execute("""
                    UPDATE user_subscriptions
                    SET status = 'active',
                        stripe_subscription_id = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, stripe_subscription_id, trial['id'])
                
                logger.info(f"Converted trial to paid for {email}")
                
                # TODO: Track conversion in analytics
                # TODO: Send conversion success email
                
                return {
                    "email": email,
                    "converted": True,
                    "stripe_subscription_id": stripe_subscription_id
                }
                
        except Exception as e:
            logger.error(f"Error converting trial: {e}", exc_info=True)
            raise
    
    async def get_trial_stats(self) -> Dict[str, Any]:
        """
        Get trial statistics for analytics
        
        Returns:
            Dict with trial metrics
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'trialing') as active_trials,
                        COUNT(*) FILTER (WHERE status = 'expired') as expired_trials,
                        COUNT(*) FILTER (WHERE status = 'active' AND created_at > NOW() - INTERVAL '30 days') as recent_conversions
                    FROM user_subscriptions
                """)
                
                # Get expiring soon counts
                expiring_7d = await conn.fetchval("""
                    SELECT COUNT(*) FROM user_subscriptions
                    WHERE status = 'trialing'
                    AND current_period_end > NOW()
                    AND current_period_end <= NOW() + INTERVAL '7 days'
                """)
                
                expiring_3d = await conn.fetchval("""
                    SELECT COUNT(*) FROM user_subscriptions
                    WHERE status = 'trialing'
                    AND current_period_end > NOW()
                    AND current_period_end <= NOW() + INTERVAL '3 days'
                """)
                
                return {
                    "active_trials": stats['active_trials'],
                    "expired_trials": stats['expired_trials'],
                    "recent_conversions_30d": stats['recent_conversions'],
                    "expiring_within_7_days": expiring_7d,
                    "expiring_within_3_days": expiring_3d
                }
                
        except Exception as e:
            logger.error(f"Error getting trial stats: {e}", exc_info=True)
            return {}


# Global singleton
trial_manager = TrialManager()
