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
        
        try:
            # Get trials expiring in 7 days
            expiring_7d = await trial_manager.get_expiring_trials(days=7)
            for trial in expiring_7d:
                # TODO: Send 7-day warning email
                logger.info(f"Trial expiring in 7 days: {trial['email']}")
            
            # Get trials expiring in 3 days
            expiring_3d = await trial_manager.get_expiring_trials(days=3)
            for trial in expiring_3d:
                # TODO: Send 3-day warning email
                logger.info(f"Trial expiring in 3 days: {trial['email']}")
            
            # Get trials expiring in 1 day
            expiring_1d = await trial_manager.get_expiring_trials(days=1)
            for trial in expiring_1d:
                # TODO: Send 1-day warning email
                logger.info(f"Trial expiring in 1 day: {trial['email']}")
                
        except Exception as e:
            logger.error(f"Error sending expiration warnings: {e}", exc_info=True)


# Global singleton
trial_scheduler = TrialScheduler()
