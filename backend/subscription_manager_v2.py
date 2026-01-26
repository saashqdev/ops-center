"""
Subscription Manager for Epic 5.0 E-commerce
Handles subscription lifecycle: creation, updates, cancellation, upgrades
Integrates with Stripe webhooks and database
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages user subscriptions and tier assignments
    """
    
    def __init__(self):
        self.default_trial_days = int(os.getenv('DEFAULT_TRIAL_DAYS', '14'))
    
    async def create_user_from_checkout(
        self, 
        email: str, 
        tier_code: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        billing_cycle: str = 'monthly'
    ) -> Dict[str, Any]:
        """
        Create or update user account after successful checkout
        
        Args:
            email: User's email address
            tier_code: Subscription tier (trial, starter, etc.)
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            billing_cycle: monthly or yearly
            
        Returns:
            Dict with user info and subscription details
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Check if user exists
                user = await conn.fetchrow("""
                    SELECT id, email, is_active FROM users WHERE email = $1
                """, email)
                
                if user:
                    user_id = user['id']
                    logger.info(f"Existing user found: {email} (id: {user_id})")
                else:
                    # Create new user
                    user_id = await conn.fetchval("""
                        INSERT INTO users (
                            email, 
                            is_active, 
                            created_at,
                            stripe_customer_id
                        ) VALUES ($1, $2, $3, $4)
                        RETURNING id
                    """, email, True, datetime.utcnow(), stripe_customer_id)
                    logger.info(f"Created new user: {email} (id: {user_id})")
                
                # Get tier information
                tier = await conn.fetchrow("""
                    SELECT id, tier_code, tier_name, price_monthly, price_yearly
                    FROM subscription_tiers
                    WHERE tier_code = $1 AND is_active = true
                """, tier_code)
                
                if not tier:
                    raise ValueError(f"Tier not found: {tier_code}")
                
                # Calculate subscription dates
                now = datetime.utcnow()
                if billing_cycle == 'yearly':
                    period_end = now + timedelta(days=365)
                else:
                    period_end = now + timedelta(days=30)
                
                # Create or update subscription record
                subscription = await conn.fetchrow("""
                    INSERT INTO user_subscriptions (
                        user_id,
                        tier_id,
                        stripe_subscription_id,
                        stripe_customer_id,
                        status,
                        billing_cycle,
                        current_period_start,
                        current_period_end,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (user_id) DO UPDATE SET
                        tier_id = EXCLUDED.tier_id,
                        stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                        stripe_customer_id = EXCLUDED.stripe_customer_id,
                        status = EXCLUDED.status,
                        billing_cycle = EXCLUDED.billing_cycle,
                        current_period_start = EXCLUDED.current_period_start,
                        current_period_end = EXCLUDED.current_period_end,
                        updated_at = $9
                    RETURNING id, status
                """, 
                    user_id, 
                    tier['id'], 
                    stripe_subscription_id,
                    stripe_customer_id,
                    'active',
                    billing_cycle,
                    now,
                    period_end,
                    now
                )
                
                logger.info(f"Subscription created/updated for user {user_id}: {subscription['status']}")
                
                return {
                    'user_id': user_id,
                    'email': email,
                    'tier_code': tier_code,
                    'tier_name': tier['tier_name'],
                    'subscription_id': subscription['id'],
                    'stripe_subscription_id': stripe_subscription_id,
                    'status': subscription['status']
                }
                
        except Exception as e:
            logger.error(f"Error creating user from checkout: {e}")
            raise
    
    async def update_subscription_status(
        self,
        stripe_subscription_id: str,
        status: str,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None
    ) -> bool:
        """
        Update subscription status from webhook events
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            status: New status (active, canceled, past_due, etc.)
            current_period_start: Period start date
            current_period_end: Period end date
            
        Returns:
            True if updated successfully
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                update_fields = ['status = $2', 'updated_at = $3']
                params = [stripe_subscription_id, status, datetime.utcnow()]
                param_count = 3
                
                if current_period_start:
                    param_count += 1
                    update_fields.append(f'current_period_start = ${param_count}')
                    params.append(current_period_start)
                
                if current_period_end:
                    param_count += 1
                    update_fields.append(f'current_period_end = ${param_count}')
                    params.append(current_period_end)
                
                query = f"""
                    UPDATE user_subscriptions
                    SET {', '.join(update_fields)}
                    WHERE stripe_subscription_id = $1
                    RETURNING id
                """
                
                result = await conn.fetchval(query, *params)
                
                if result:
                    logger.info(f"Updated subscription {stripe_subscription_id} to status: {status}")
                    return True
                else:
                    logger.warning(f"Subscription not found: {stripe_subscription_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            raise
    
    async def cancel_subscription(
        self,
        user_id: int,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel user's subscription
        
        Args:
            user_id: User ID
            at_period_end: If True, cancel at end of billing period
            
        Returns:
            Cancellation details
        """
        try:
            import stripe
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get user's subscription
                subscription = await conn.fetchrow("""
                    SELECT 
                        id,
                        stripe_subscription_id,
                        status,
                        current_period_end
                    FROM user_subscriptions
                    WHERE user_id = $1 AND status = 'active'
                """, user_id)
                
                if not subscription:
                    raise ValueError("No active subscription found")
                
                # Cancel in Stripe
                stripe_sub = stripe.Subscription.modify(
                    subscription['stripe_subscription_id'],
                    cancel_at_period_end=at_period_end
                )
                
                # Update database
                if at_period_end:
                    new_status = 'active'  # Keep active until period end
                    cancel_at = subscription['current_period_end']
                else:
                    new_status = 'canceled'
                    cancel_at = datetime.utcnow()
                
                await conn.execute("""
                    UPDATE user_subscriptions
                    SET 
                        status = $1,
                        cancel_at = $2,
                        canceled_at = $3,
                        updated_at = $4
                    WHERE id = $5
                """, new_status, cancel_at, datetime.utcnow(), datetime.utcnow(), subscription['id'])
                
                logger.info(f"Canceled subscription for user {user_id}, at_period_end: {at_period_end}")
                
                return {
                    'subscription_id': subscription['id'],
                    'status': new_status,
                    'cancel_at': cancel_at,
                    'at_period_end': at_period_end
                }
                
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            raise
    
    async def upgrade_subscription(
        self,
        user_id: int,
        new_tier_code: str,
        billing_cycle: str = 'monthly',
        prorate: bool = True
    ) -> Dict[str, Any]:
        """
        Upgrade user's subscription to a new tier
        
        Args:
            user_id: User ID
            new_tier_code: Target tier code
            billing_cycle: monthly or yearly
            prorate: Whether to prorate the upgrade
            
        Returns:
            Upgrade details
        """
        try:
            import stripe
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get current subscription
                current = await conn.fetchrow("""
                    SELECT 
                        us.id,
                        us.stripe_subscription_id,
                        us.tier_id,
                        st.tier_code as current_tier_code,
                        st.tier_name as current_tier_name
                    FROM user_subscriptions us
                    JOIN subscription_tiers st ON us.tier_id = st.id
                    WHERE us.user_id = $1 AND us.status = 'active'
                """, user_id)
                
                if not current:
                    raise ValueError("No active subscription found")
                
                # Get new tier
                new_tier = await conn.fetchrow("""
                    SELECT 
                        id, 
                        tier_code, 
                        tier_name,
                        stripe_price_monthly,
                        stripe_price_yearly
                    FROM subscription_tiers
                    WHERE tier_code = $1 AND is_active = true
                """, new_tier_code)
                
                if not new_tier:
                    raise ValueError(f"Tier not found: {new_tier_code}")
                
                # Get new price ID
                new_price_id = (
                    new_tier['stripe_price_yearly'] if billing_cycle == 'yearly'
                    else new_tier['stripe_price_monthly']
                )
                
                if not new_price_id:
                    raise ValueError(f"Price ID not configured for {new_tier_code} ({billing_cycle})")
                
                # Update subscription in Stripe
                stripe_sub = stripe.Subscription.retrieve(current['stripe_subscription_id'])
                
                updated_sub = stripe.Subscription.modify(
                    current['stripe_subscription_id'],
                    items=[{
                        'id': stripe_sub['items']['data'][0].id,
                        'price': new_price_id,
                    }],
                    proration_behavior='create_prorations' if prorate else 'none'
                )
                
                # Update database
                await conn.execute("""
                    UPDATE user_subscriptions
                    SET 
                        tier_id = $1,
                        billing_cycle = $2,
                        updated_at = $3
                    WHERE id = $4
                """, new_tier['id'], billing_cycle, datetime.utcnow(), current['id'])
                
                logger.info(
                    f"Upgraded subscription for user {user_id}: "
                    f"{current['current_tier_code']} → {new_tier_code}"
                )
                
                return {
                    'subscription_id': current['id'],
                    'old_tier': current['current_tier_code'],
                    'new_tier': new_tier_code,
                    'billing_cycle': billing_cycle,
                    'prorated': prorate
                }
                
        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            raise
    
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's current subscription details
        
        Args:
            user_id: User ID
            
        Returns:
            Subscription details or None
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                subscription = await conn.fetchrow("""
                    SELECT 
                        us.id,
                        us.user_id,
                        us.status,
                        us.billing_cycle,
                        us.current_period_start,
                        us.current_period_end,
                        us.cancel_at,
                        us.canceled_at,
                        us.stripe_subscription_id,
                        us.stripe_customer_id,
                        st.tier_code,
                        st.tier_name,
                        st.price_monthly,
                        st.price_yearly,
                        st.api_calls_limit,
                        st.team_seats,
                        st.byok_enabled,
                        st.priority_support
                    FROM user_subscriptions us
                    JOIN subscription_tiers st ON us.tier_id = st.id
                    WHERE us.user_id = $1
                    ORDER BY us.created_at DESC
                    LIMIT 1
                """, user_id)
                
                if not subscription:
                    return None
                
                return dict(subscription)
                
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            raise
    
    async def get_subscription_by_stripe_id(
        self, 
        stripe_subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription by Stripe subscription ID
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            
        Returns:
            Subscription details or None
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                subscription = await conn.fetchrow("""
                    SELECT 
                        us.id,
                        us.user_id,
                        us.tier_id,
                        us.status,
                        u.email
                    FROM user_subscriptions us
                    JOIN users u ON us.user_id = u.id
                    WHERE us.stripe_subscription_id = $1
                """, stripe_subscription_id)
                
                if not subscription:
                    return None
                
                return dict(subscription)
                
        except Exception as e:
            logger.error(f"Error getting subscription by Stripe ID: {e}")
            raise


# Global singleton instance
subscription_manager = SubscriptionManager()
