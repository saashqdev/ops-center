"""
Epic 15: Multi-Server Management - Health Check Background Worker
Runs every 30 seconds to check health of all active managed servers
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import asyncpg
from multi_server_manager import MultiServerManager

logger = logging.getLogger(__name__)


class FleetHealthWorker:
    """Background worker for automated health checks"""
    
    def __init__(self, db_pool: asyncpg.Pool, interval: int = 30):
        """
        Initialize health check worker
        
        Args:
            db_pool: Database connection pool
            interval: Check interval in seconds (default: 30)
        """
        self.db_pool = db_pool
        self.interval = interval
        self.manager: Optional[MultiServerManager] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Statistics
        self.checks_performed = 0
        self.checks_successful = 0
        self.checks_failed = 0
        self.last_run = None
        self.last_duration = None
    
    async def initialize(self):
        """Initialize the manager"""
        self.manager = MultiServerManager(self.db_pool)
        await self.manager.initialize()
        logger.info(f"Fleet health worker initialized (interval: {self.interval}s)")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.manager:
            await self.manager.cleanup()
            self.manager = None
    
    async def _check_server_health(
        self,
        server_id: str,
        api_url: str,
        api_token_hash: str,
        organization_id: str
    ) -> dict:
        """
        Check health of a single server
        
        Note: In production, you'd retrieve the actual API token from secure storage
        using the token_hash as a key. For now, we'll attempt to check if possible.
        """
        try:
            # TODO: Retrieve actual API token from secure storage using token_hash
            # For now, we'll attempt a basic health check
            
            result = await self.manager._perform_health_check(
                server_id=server_id,
                api_url=api_url,
                api_token="SECURE_TOKEN_PLACEHOLDER"  # Would come from secrets manager
            )
            
            return {
                "server_id": server_id,
                "status": "success",
                "health_status": result.get("status"),
                "response_time_ms": result.get("response_time_ms")
            }
        
        except Exception as e:
            logger.error(f"Health check failed for server {server_id}: {e}")
            return {
                "server_id": server_id,
                "status": "error",
                "error": str(e)
            }
    
    async def _perform_health_checks(self):
        """Perform health checks on all active servers across all organizations"""
        start_time = datetime.utcnow()
        
        try:
            # Get all active servers from all organizations
            async with self.db_pool.acquire() as conn:
                servers = await conn.fetch(
                    """
                    SELECT 
                        id, 
                        api_url, 
                        api_token_hash,
                        organization_id,
                        name
                    FROM managed_servers
                    WHERE status = 'active'
                    ORDER BY last_health_check_at ASC NULLS FIRST
                    """
                )
            
            server_count = len(servers)
            
            if server_count == 0:
                logger.debug("No active servers to check")
                return
            
            logger.info(f"Starting health checks for {server_count} servers")
            
            # Check servers in batches to avoid overwhelming the system
            batch_size = 10
            results = []
            
            for i in range(0, server_count, batch_size):
                batch = servers[i:i + batch_size]
                
                # Run health checks concurrently within the batch
                batch_tasks = [
                    self._check_server_health(
                        server['id'],
                        server['api_url'],
                        server['api_token_hash'],
                        server['organization_id']
                    )
                    for server in batch
                ]
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Health check exception: {result}")
                        self.checks_failed += 1
                    else:
                        results.append(result)
                        if result.get('status') == 'success':
                            self.checks_successful += 1
                        else:
                            self.checks_failed += 1
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < server_count:
                    await asyncio.sleep(0.5)
            
            self.checks_performed += server_count
            
            # Calculate statistics
            healthy = len([r for r in results if r.get('health_status') == 'healthy'])
            degraded = len([r for r in results if r.get('health_status') == 'degraded'])
            critical = len([r for r in results if r.get('health_status') == 'critical'])
            unreachable = len([r for r in results if r.get('health_status') == 'unreachable'])
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.last_duration = duration
            
            logger.info(
                f"Health checks complete: {server_count} servers checked in {duration:.2f}s "
                f"(✓{healthy} 🔶{degraded} ⚠️{critical} ❌{unreachable})"
            )
            
            # Alert on critical issues (integrate with Epic 13: Smart Alerts in future)
            if critical > 0 or unreachable > 0:
                logger.warning(
                    f"Fleet health alert: {critical} critical, {unreachable} unreachable servers"
                )
        
        except Exception as e:
            logger.error(f"Health check worker error: {e}", exc_info=True)
    
    async def _worker_loop(self):
        """Main worker loop"""
        logger.info(f"🏥 Fleet health worker started (checking every {self.interval}s)")
        
        while self.running:
            try:
                self.last_run = datetime.utcnow()
                await self._perform_health_checks()
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
            
            except asyncio.CancelledError:
                logger.info("Health worker received cancellation signal")
                break
            
            except Exception as e:
                logger.error(f"Health worker loop error: {e}", exc_info=True)
                # Continue after error, wait a bit longer
                await asyncio.sleep(self.interval * 2)
        
        logger.info("🏥 Fleet health worker stopped")
    
    def start(self):
        """Start the background worker"""
        if self.running:
            logger.warning("Health worker already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._worker_loop())
        logger.info("Fleet health worker task created")
    
    async def stop(self):
        """Stop the background worker"""
        if not self.running:
            return
        
        logger.info("Stopping fleet health worker...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        await self.cleanup()
        logger.info("Fleet health worker stopped")
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "checks_performed": self.checks_performed,
            "checks_successful": self.checks_successful,
            "checks_failed": self.checks_failed,
            "success_rate": (
                self.checks_successful / self.checks_performed * 100 
                if self.checks_performed > 0 else 0
            ),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_duration_seconds": self.last_duration
        }


# Global worker instance (initialized in server.py)
health_worker: Optional[FleetHealthWorker] = None


async def start_health_worker(db_pool: asyncpg.Pool, interval: int = 30):
    """Start the global health worker"""
    global health_worker
    
    if health_worker and health_worker.running:
        logger.warning("Health worker already running")
        return health_worker
    
    health_worker = FleetHealthWorker(db_pool, interval)
    await health_worker.initialize()
    health_worker.start()
    
    return health_worker


async def stop_health_worker():
    """Stop the global health worker"""
    global health_worker
    
    if health_worker:
        await health_worker.stop()
        health_worker = None


def get_health_worker() -> Optional[FleetHealthWorker]:
    """Get the global health worker instance"""
    return health_worker
