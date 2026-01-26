"""
Trial Expiration Scheduler
Background task to check and process trial expirations
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class TrialScheduler:
    """Background scheduler for trial management tasks"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 3600  # Check every hour
    
    async def start(self):
        """Start the trial expiration scheduler"""
        if self.running:
            logger.warning("Trial scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Trial scheduler started")
    
    async def stop(self):
        """Stop the trial expiration scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Trial scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        from trial_manager import trial_manager
        
        while self.running:
            try:
                logger.info("Running trial expiration check...")
                
                # Check for expired trials
                downgraded = await trial_manager.check_trial_expiration()
                if downgraded:
                    logger.info(f"Downgraded {len(downgraded)} expired trials")
                
                # Send expiration warnings
                await self._send_expiration_warnings()
                
                # Wait for next interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trial scheduler: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _send_expiration_warnings(self):
        """Send warning emails for expiring trials"""
        from trial_manager import trial_manager
        from email_service import email_service
        
        try:
            # Get trials expiring in 3 days (only send once)
            expiring_3d = await trial_manager.get_expiring_trials(days=3)
            for trial in expiring_3d:
                # Check if we already sent 3-day warning
                if not await self._warning_sent(trial['email'], 'trial_expiring_3d'):
                    await email_service.send_trial_expiring_soon(
                        to=trial['email'],
                        days_remaining=3,
                        trial_end_date=trial['trial_end_date'].strftime('%B %d, %Y')
                    )
                    await self._mark_warning_sent(trial['email'], 'trial_expiring_3d')
                    logger.info(f"Sent 3-day expiration warning to {trial['email']}")
            
            # Get trials expiring in 1 day (only send once)
            expiring_1d = await trial_manager.get_expiring_trials(days=1)
            for trial in expiring_1d:
                # Check if we already sent 1-day warning
                if not await self._warning_sent(trial['email'], 'trial_expiring_1d'):
                    await email_service.send_trial_expiring_soon(
                        to=trial['email'],
                        days_remaining=1,
                        trial_end_date=trial['trial_end_date'].strftime('%B %d, %Y')
                    )
                    await self._mark_warning_sent(trial['email'], 'trial_expiring_1d')
                    logger.info(f"Sent 1-day expiration warning to {trial['email']}")
                
        except Exception as e:
            logger.error(f"Error sending expiration warnings: {e}", exc_info=True)
    
    async def _warning_sent(self, email: str, warning_type: str) -> bool:
        """Check if a specific warning was already sent"""
        from database import get_db_pool
        
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT COUNT(*) FROM email_logs
                    WHERE to_email = $1 
                    AND metadata->>'type' = $2
                    AND success = true
                    AND sent_at > NOW() - INTERVAL '7 days'
                """, email, warning_type)
                return result > 0
        except Exception as e:
            logger.error(f"Error checking warning sent: {e}")
            return False  # Assume not sent on error
    
    async def _mark_warning_sent(self, email: str, warning_type: str):
        """Mark that a warning was sent (this happens automatically via email_logs)"""
        # The email_service._log_email() method already logs with metadata
        # This is just a placeholder for clarity
        pass


# Global singleton
trial_scheduler = TrialScheduler()
