"""
Simplified Subscription Manager for Epic 5.0
Works with email-based subscriptions (no users table dependency)
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages email-based subscriptions"""
    
    async def create_subscription_from_checkout(
        self, 
        email: str, 
        tier_code: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        billing_cycle: str = 'monthly'
    ) -> Dict[str, Any]:
        """
        Create subscription after successful checkout
        
        Args:
            email: Customer email
            tier_code: Tier code (free, starter, professional, enterprise)
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            billing_cycle: monthly or yearly
            
        Returns:
            Dict with subscription details
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get tier information
                tier = await conn.fetchrow("""
                    SELECT id, code, name
                    FROM subscription_tiers
                    WHERE code = $1
                """, tier_code)
                
                if not tier:
                    raise ValueError(f"Tier not found: {tier_code}")
                
                # Calculate subscription period
                now = datetime.utcnow()
                if billing_cycle == 'yearly':
                    period_end = now + timedelta(days=365)
                else:
                    period_end = now + timedelta(days=30)
                
                # Create/update subscription
                result = await conn.fetchrow("""
                    INSERT INTO user_subscriptions (
                        email,
                        tier_id,
                        stripe_subscription_id,
                        stripe_customer_id,
                        status,
                        billing_cycle,
                        current_period_start,
                        current_period_end,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (email) DO UPDATE SET
                        tier_id = EXCLUDED.tier_id,
                        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                        stripe_customer_id = EXCLUDED.stripe_customer_id,
                        status = EXCLUDED.status,
                        billing_cycle = EXCLUDED.billing_cycle,
                        current_period_start = EXCLUDED.current_period_start,
                        current_period_end = EXCLUDED.current_period_end,
                        updated_at = NOW()
                    RETURNING id
                """, email, tier['id'], stripe_subscription_id, stripe_customer_id,
                    'active', billing_cycle, now, period_end, now)
                
                logger.info(f"Created subscription {result['id']} for {email}: {tier_code}/{billing_cycle}")
                
                # Check if this is a trial conversion
                from trial_manager import trial_manager
                await trial_manager.convert_trial_to_paid(
                    email=email,
                    stripe_subscription_id=stripe_subscription_id
                )
                
                return {
                    "subscription_id": result['id'],
                    "email": email,
                    "tier_code": tier_code,
                    "status": "active"
                }
                
        except Exception as e:
            logger.error(f"Error creating subscription: {e}", exc_info=True)
            raise
    
    async def update_subscription_status(
        self,
        stripe_subscription_id: str,
        status: str,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None
    ) -> bool:
        """
        Update subscription status from webhook
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            status: New status (active, canceled, past_due, etc.)
            current_period_start: Start of current period
            current_period_end: End of current period
            
        Returns:
            True if updated successfully
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Build update query dynamically
                updates = ["status = $2", "updated_at = NOW()"]
                params = [stripe_subscription_id, status]
                param_idx = 3
                
                if current_period_start:
                    updates.append(f"current_period_start = ${param_idx}")
                    params.append(current_period_start)
                    param_idx += 1
                
                if current_period_end:
                    updates.append(f"current_period_end = ${param_idx}")
                    params.append(current_period_end)
                
                query = f"""
                    UPDATE user_subscriptions
                    SET {', '.join(updates)}
                    WHERE stripe_subscription_id = $1
                """
                
                result = await conn.execute(query, *params)
                logger.info(f"Updated subscription {stripe_subscription_id} to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating subscription: {e}", exc_info=True)
            return False
    
    async def cancel_subscription(
        self,
        email: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a subscription
        
        Args:
            email: User email
            at_period_end: If True, cancel at end of billing period
            
        Returns:
            Dict with cancellation details
        """
        try:
            import stripe
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get subscription
                sub = await conn.fetchrow("""
                    SELECT id, stripe_subscription_id, current_period_end
                    FROM user_subscriptions
                    WHERE email = $1 AND status = 'active'
                """, email)
                
                if not sub:
                    raise ValueError("No active subscription found")
                
                # Cancel in Stripe
                stripe.Subscription.modify(
                    sub['stripe_subscription_id'],
                    cancel_at_period_end=at_period_end
                )
                
                # Update database
                now = datetime.utcnow()
                if at_period_end:
                    cancel_at = sub['current_period_end']
                    await conn.execute("""
                        UPDATE user_subscriptions
                        SET cancel_at = $1, updated_at = $2
                        WHERE id = $3
                    """, cancel_at, now, sub['id'])
                    status = 'active'
                else:
                    await conn.execute("""
                        UPDATE user_subscriptions
                        SET status = $1, canceled_at = $2, updated_at = $2
                        WHERE id = $3
                    """, 'canceled', now, sub['id'])
                    cancel_at = now
                    status = 'canceled'
                
                logger.info(f"Canceled subscription for {email} (at_period_end={at_period_end})")
                
                return {
                    "email": email,
                    "status": status,
                    "cancel_at": cancel_at
                }
                
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}", exc_info=True)
            raise
    
    async def get_subscription_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get subscription details by email"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT 
                        s.*,
                        t.code as tier_code,
                        t.name as tier_name,
                        t.price_monthly,
                        t.price_yearly
                    FROM user_subscriptions s
                    JOIN subscription_tiers t ON s.tier_id = t.id
                    WHERE s.email = $1
                """, email)
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Error getting subscription: {e}", exc_info=True)
            return None
    
    async def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by Stripe subscription ID (for webhooks)"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT *
                    FROM user_subscriptions
                    WHERE stripe_subscription_id = $1
                """, stripe_subscription_id)
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Error getting subscription by Stripe ID: {e}", exc_info=True)
            return None


# Global singleton
subscription_manager = SubscriptionManager()
