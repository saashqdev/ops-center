"""
Payment Dunning Manager
Handles payment retry logic, grace periods, and subscription suspension
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class DunningManager:
    """Manages payment retry campaigns and dunning process"""
    
    def __init__(self):
        # Dunning configuration
        self.max_retries = int(os.getenv('DUNNING_MAX_RETRIES', '3'))
        self.retry_schedule_days = [3, 5, 7]  # Days after initial failure to retry
        self.grace_period_days = int(os.getenv('DUNNING_GRACE_PERIOD_DAYS', '10'))
        
        logger.info(f"DunningManager initialized: max_retries={self.max_retries}, grace_period={self.grace_period_days} days")
    
    async def create_dunning_campaign(
        self,
        subscription_id: int,
        stripe_invoice_id: str,
        amount_due: float,
        currency: str = 'usd',
        failure_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new dunning campaign for a failed payment
        
        Args:
            subscription_id: User subscription ID
            stripe_invoice_id: Failed Stripe invoice ID
            amount_due: Amount that failed to charge
            currency: Currency code
            failure_reason: Reason for payment failure
            
        Returns:
            Dict with dunning campaign details
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Check if dunning campaign already exists for this invoice
                existing = await conn.fetchrow("""
                    SELECT id FROM payment_dunning
                    WHERE stripe_invoice_id = $1 AND status = 'active'
                """, stripe_invoice_id)
                
                if existing:
                    logger.warning(f"Dunning campaign already exists for invoice {stripe_invoice_id}")
                    return await self.get_dunning_campaign(existing['id'])
                
                # Calculate dates
                now = datetime.utcnow()
                next_retry = now + timedelta(days=self.retry_schedule_days[0])
                grace_period_ends = now + timedelta(days=self.grace_period_days)
                
                # Create dunning record
                result = await conn.fetchrow("""
                    INSERT INTO payment_dunning (
                        subscription_id,
                        stripe_invoice_id,
                        status,
                        retry_count,
                        max_retries,
                        first_failure_at,
                        next_retry_at,
                        grace_period_ends_at,
                        amount_due,
                        currency,
                        failure_reason,
                        metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    RETURNING id
                """, subscription_id, stripe_invoice_id, 'active', 0, self.max_retries,
                now, next_retry, grace_period_ends, amount_due, currency, failure_reason,
                '{"emails_sent": 0}')
                
                dunning_id = result['id']
                
                logger.info(f"Created dunning campaign {dunning_id} for subscription {subscription_id}, next retry: {next_retry}")
                
                # Send first failure notification
                await self._send_dunning_email(dunning_id, attempt=1)
                
                return {
                    "id": dunning_id,
                    "subscription_id": subscription_id,
                    "status": "active",
                    "retry_count": 0,
                    "next_retry_at": next_retry,
                    "grace_period_ends_at": grace_period_ends
                }
                
        except Exception as e:
            logger.error(f"Error creating dunning campaign: {e}", exc_info=True)
            raise
    
    async def process_retry_attempt(self, dunning_id: int) -> Dict[str, Any]:
        """
        Process a retry attempt for a dunning campaign
        
        Args:
            dunning_id: Dunning campaign ID
            
        Returns:
            Dict with retry result
        """
        try:
            from database import get_db_pool
            import stripe
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get dunning campaign
                campaign = await conn.fetchrow("""
                    SELECT * FROM payment_dunning WHERE id = $1
                """, dunning_id)
                
                if not campaign or campaign['status'] != 'active':
                    logger.warning(f"Dunning campaign {dunning_id} not found or not active")
                    return {"status": "skipped", "reason": "campaign not active"}
                
                # Check if we've exceeded max retries
                if campaign['retry_count'] >= campaign['max_retries']:
                    logger.warning(f"Dunning campaign {dunning_id} exceeded max retries")
                    await self._mark_dunning_failed(dunning_id)
                    return {"status": "failed", "reason": "max retries exceeded"}
                
                # Attempt to retry payment via Stripe
                try:
                    invoice = stripe.Invoice.retrieve(campaign['stripe_invoice_id'])
                    
                    # Stripe automatically retries - we just check status
                    if invoice.status == 'paid':
                        await self._mark_dunning_resolved(dunning_id)
                        logger.info(f"Payment succeeded for dunning campaign {dunning_id}")
                        return {"status": "resolved", "message": "Payment succeeded"}
                    
                    # Payment still failed, schedule next retry
                    retry_count = campaign['retry_count'] + 1
                    
                    if retry_count < len(self.retry_schedule_days):
                        days_to_next = self.retry_schedule_days[retry_count]
                        next_retry = datetime.utcnow() + timedelta(days=days_to_next)
                    else:
                        next_retry = None  # No more retries scheduled
                    
                    # Update dunning record
                    await conn.execute("""
                        UPDATE payment_dunning
                        SET retry_count = $1,
                            last_retry_at = NOW(),
                            next_retry_at = $2,
                            updated_at = NOW()
                        WHERE id = $3
                    """, retry_count, next_retry, dunning_id)
                    
                    # Send escalating email
                    await self._send_dunning_email(dunning_id, attempt=retry_count + 1)
                    
                    logger.info(f"Retry attempt {retry_count} for dunning {dunning_id}, next retry: {next_retry}")
                    
                    return {
                        "status": "retry_scheduled",
                        "retry_count": retry_count,
                        "next_retry_at": next_retry
                    }
                    
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe error during retry: {e}")
                    return {"status": "error", "message": str(e)}
                
        except Exception as e:
            logger.error(f"Error processing retry attempt: {e}", exc_info=True)
            raise
    
    async def check_grace_periods(self) -> List[Dict[str, Any]]:
        """
        Check for dunning campaigns where grace period has expired
        Suspend subscriptions that still have failed payments
        
        Returns:
            List of suspended subscriptions
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Find campaigns with expired grace periods
                expired = await conn.fetch("""
                    SELECT 
                        pd.id,
                        pd.subscription_id,
                        pd.amount_due,
                        us.email
                    FROM payment_dunning pd
                    JOIN user_subscriptions us ON pd.subscription_id = us.id
                    WHERE pd.status = 'active'
                    AND pd.grace_period_ends_at < NOW()
                """)
                
                if not expired:
                    logger.info("No expired grace periods found")
                    return []
                
                suspended = []
                for campaign in expired:
                    # Mark dunning as failed
                    await self._mark_dunning_failed(campaign['id'])
                    
                    # Suspend subscription
                    await conn.execute("""
                        UPDATE user_subscriptions
                        SET status = 'past_due',
                            updated_at = NOW()
                        WHERE id = $1
                    """, campaign['subscription_id'])
                    
                    logger.warning(f"Suspended subscription {campaign['subscription_id']} after grace period expiry")
                    
                    # Send final suspension email
                    await self._send_suspension_email(
                        email=campaign['email'],
                        amount_due=campaign['amount_due']
                    )
                    
                    suspended.append({
                        "subscription_id": campaign['subscription_id'],
                        "email": campaign['email'],
                        "amount_due": campaign['amount_due']
                    })
                
                return suspended
                
        except Exception as e:
            logger.error(f"Error checking grace periods: {e}", exc_info=True)
            return []
    
    async def get_pending_retries(self) -> List[Dict[str, Any]]:
        """
        Get dunning campaigns that are ready for retry
        
        Returns:
            List of campaigns ready for retry
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                pending = await conn.fetch("""
                    SELECT 
                        pd.id,
                        pd.subscription_id,
                        pd.retry_count,
                        pd.next_retry_at,
                        us.email
                    FROM payment_dunning pd
                    JOIN user_subscriptions us ON pd.subscription_id = us.id
                    WHERE pd.status = 'active'
                    AND pd.next_retry_at IS NOT NULL
                    AND pd.next_retry_at <= NOW()
                    ORDER BY pd.next_retry_at ASC
                """)
                
                return [dict(row) for row in pending]
                
        except Exception as e:
            logger.error(f"Error getting pending retries: {e}", exc_info=True)
            return []
    
    async def get_dunning_campaign(self, dunning_id: int) -> Optional[Dict[str, Any]]:
        """Get dunning campaign details"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                campaign = await conn.fetchrow("""
                    SELECT * FROM payment_dunning WHERE id = $1
                """, dunning_id)
                
                if not campaign:
                    return None
                
                return dict(campaign)
                
        except Exception as e:
            logger.error(f"Error getting dunning campaign: {e}", exc_info=True)
            return None
    
    async def _mark_dunning_resolved(self, dunning_id: int):
        """Mark dunning campaign as resolved (payment succeeded)"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE payment_dunning
                    SET status = 'resolved',
                        resolved_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                """, dunning_id)
                
                logger.info(f"Marked dunning campaign {dunning_id} as resolved")
                
        except Exception as e:
            logger.error(f"Error marking dunning resolved: {e}")
    
    async def _mark_dunning_failed(self, dunning_id: int):
        """Mark dunning campaign as failed (max retries exhausted)"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE payment_dunning
                    SET status = 'failed',
                        updated_at = NOW()
                    WHERE id = $1
                """, dunning_id)
                
                logger.info(f"Marked dunning campaign {dunning_id} as failed")
                
        except Exception as e:
            logger.error(f"Error marking dunning failed: {e}")
    
    async def _send_dunning_email(self, dunning_id: int, attempt: int):
        """Send escalating dunning email based on attempt number"""
        try:
            from database import get_db_pool
            from email_service import email_service
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get campaign and subscription details
                data = await conn.fetchrow("""
                    SELECT 
                        pd.*,
                        us.email
                    FROM payment_dunning pd
                    JOIN user_subscriptions us ON pd.subscription_id = us.id
                    WHERE pd.id = $1
                """, dunning_id)
                
                if not data:
                    logger.error(f"Dunning campaign {dunning_id} not found")
                    return
                
                # Determine urgency and days remaining
                days_remaining = (data['grace_period_ends_at'] - datetime.utcnow()).days
                
                if attempt == 1:
                    # First failure - gentle reminder
                    await email_service.send_payment_retry_reminder(
                        to=data['email'],
                        amount=float(data['amount_due']),
                        attempt=attempt,
                        days_until_suspension=days_remaining,
                        failure_reason=data['failure_reason']
                    )
                elif attempt <= 2:
                    # Second attempt - more urgent
                    await email_service.send_payment_retry_urgent(
                        to=data['email'],
                        amount=float(data['amount_due']),
                        attempt=attempt,
                        days_until_suspension=days_remaining
                    )
                else:
                    # Final attempt - critical
                    await email_service.send_payment_retry_final(
                        to=data['email'],
                        amount=float(data['amount_due']),
                        days_until_suspension=days_remaining
                    )
                
                # Update metadata
                import json
                metadata = json.loads(data['metadata']) if data['metadata'] else {}
                metadata['emails_sent'] = metadata.get('emails_sent', 0) + 1
                metadata['last_email_type'] = f'attempt_{attempt}'
                metadata['last_email_sent'] = datetime.utcnow().isoformat()
                
                await conn.execute("""
                    UPDATE payment_dunning
                    SET metadata = $1::jsonb
                    WHERE id = $2
                """, json.dumps(metadata), dunning_id)
                
                logger.info(f"Sent dunning email (attempt {attempt}) to {data['email']}")
                
        except Exception as e:
            logger.error(f"Error sending dunning email: {e}", exc_info=True)
    
    async def _send_suspension_email(self, email: str, amount_due: float):
        """Send subscription suspension notification"""
        try:
            from email_service import email_service
            
            await email_service.send_subscription_suspended(
                to=email,
                amount_due=amount_due
            )
            
            logger.info(f"Sent suspension email to {email}")
            
        except Exception as e:
            logger.error(f"Error sending suspension email: {e}")


# Global singleton
dunning_manager = DunningManager()
