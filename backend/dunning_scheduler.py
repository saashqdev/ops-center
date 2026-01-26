"""
Dunning Scheduler
Background task to process payment retries and check grace periods
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DunningScheduler:
    """Background scheduler for payment retry and dunning management"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 3600  # Check every hour (1 hour)
        self.retry_interval = 21600  # Process retries every 6 hours
        self.grace_check_interval = 86400  # Check grace periods daily
        
        self._last_retry_check = None
        self._last_grace_check = None
    
    async def start(self):
        """Start the dunning scheduler"""
        if self.running:
            logger.warning("Dunning scheduler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Dunning scheduler started")
    
    async def stop(self):
        """Stop the dunning scheduler"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Dunning scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        from dunning_manager import dunning_manager
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Process payment retries every 6 hours
                if (self._last_retry_check is None or 
                    (now - self._last_retry_check).total_seconds() >= self.retry_interval):
                    
                    logger.info("Processing payment retries...")
                    await self._process_retries()
                    self._last_retry_check = now
                
                # Check grace periods daily
                if (self._last_grace_check is None or 
                    (now - self._last_grace_check).total_seconds() >= self.grace_check_interval):
                    
                    logger.info("Checking grace periods...")
                    await self._check_grace_periods()
                    self._last_grace_check = now
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dunning scheduler: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _process_retries(self):
        """Process pending payment retries"""
        from dunning_manager import dunning_manager
        
        try:
            # Get campaigns ready for retry
            pending = await dunning_manager.get_pending_retries()
            
            if not pending:
                logger.info("No pending payment retries")
                return
            
            logger.info(f"Processing {len(pending)} payment retries")
            
            success_count = 0
            failed_count = 0
            
            for campaign in pending:
                try:
                    result = await dunning_manager.process_retry_attempt(campaign['id'])
                    
                    if result.get('status') == 'resolved':
                        success_count += 1
                        logger.info(f"Payment succeeded for subscription {campaign['subscription_id']}")
                    elif result.get('status') == 'retry_scheduled':
                        logger.info(f"Retry scheduled for subscription {campaign['subscription_id']}")
                    else:
                        failed_count += 1
                        logger.warning(f"Retry failed for subscription {campaign['subscription_id']}: {result.get('reason')}")
                    
                    # Small delay between retries to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing retry for campaign {campaign['id']}: {e}")
            
            logger.info(f"Retry processing complete: {success_count} succeeded, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error in _process_retries: {e}", exc_info=True)
    
    async def _check_grace_periods(self):
        """Check for expired grace periods and suspend subscriptions"""
        from dunning_manager import dunning_manager
        
        try:
            suspended = await dunning_manager.check_grace_periods()
            
            if not suspended:
                logger.info("No grace periods expired")
                return
            
            logger.warning(f"Suspended {len(suspended)} subscriptions due to expired grace periods")
            
            for sub in suspended:
                logger.warning(f"Suspended subscription {sub['subscription_id']} for {sub['email']}")
            
        except Exception as e:
            logger.error(f"Error checking grace periods: {e}", exc_info=True)


# Global singleton
dunning_scheduler = DunningScheduler()
