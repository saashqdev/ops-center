"""
Epic 15: Multi-Server Management - Metrics Collection Background Worker
Runs every 60 seconds to collect metrics from all active managed servers
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import asyncpg
from multi_server_manager import MultiServerManager

logger = logging.getLogger(__name__)


class FleetMetricsWorker:
    """Background worker for automated metrics collection"""
    
    def __init__(self, db_pool: asyncpg.Pool, interval: int = 60):
        """
        Initialize metrics collection worker
        
        Args:
            db_pool: Database connection pool
            interval: Collection interval in seconds (default: 60)
        """
        self.db_pool = db_pool
        self.interval = interval
        self.manager: Optional[MultiServerManager] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Statistics
        self.collections_performed = 0
        self.collections_successful = 0
        self.collections_failed = 0
        self.last_run = None
        self.last_duration = None
        self.total_metrics_collected = 0
    
    async def initialize(self):
        """Initialize the manager"""
        self.manager = MultiServerManager(self.db_pool)
        await self.manager.initialize()
        logger.info(f"Fleet metrics worker initialized (interval: {self.interval}s)")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.manager:
            await self.manager.cleanup()
            self.manager = None
    
    async def _collect_server_metrics(
        self,
        server_id: str,
        api_url: str,
        api_token_hash: str,
        server_name: str
    ) -> dict:
        """
        Collect metrics from a single server
        
        Note: In production, retrieve actual API token from secure storage
        """
        try:
            # TODO: Retrieve actual API token from secure storage
            result = await self.manager.collect_server_metrics(
                server_id=server_id,
                api_url=api_url,
                api_token="SECURE_TOKEN_PLACEHOLDER"  # From secrets manager
            )
            
            if result.get("status") == "success":
                self.total_metrics_collected += 1
                return {
                    "server_id": server_id,
                    "server_name": server_name,
                    "status": "success"
                }
            else:
                return {
                    "server_id": server_id,
                    "server_name": server_name,
                    "status": "error",
                    "error": result.get("error")
                }
        
        except Exception as e:
            logger.error(f"Metrics collection failed for server {server_name} ({server_id}): {e}")
            return {
                "server_id": server_id,
                "server_name": server_name,
                "status": "error",
                "error": str(e)
            }
    
    async def _perform_metrics_collection(self):
        """Collect metrics from all active servers across all organizations"""
        start_time = datetime.utcnow()
        
        try:
            # Get all active servers from all organizations
            # Only collect from servers that are healthy or degraded (skip critical/unreachable)
            async with self.db_pool.acquire() as conn:
                servers = await conn.fetch(
                    """
                    SELECT 
                        id, 
                        api_url, 
                        api_token_hash,
                        organization_id,
                        name,
                        health_status
                    FROM managed_servers
                    WHERE status = 'active'
                      AND health_status IN ('healthy', 'degraded')
                    ORDER BY last_seen_at DESC NULLS LAST
                    """
                )
            
            server_count = len(servers)
            
            if server_count == 0:
                logger.debug("No active healthy servers to collect metrics from")
                return
            
            logger.info(f"Starting metrics collection for {server_count} servers")
            
            # Collect metrics in batches to manage load
            batch_size = 5  # Smaller batches than health checks (metrics are heavier)
            results = []
            
            for i in range(0, server_count, batch_size):
                batch = servers[i:i + batch_size]
                
                # Run metrics collection concurrently within the batch
                batch_tasks = [
                    self._collect_server_metrics(
                        server['id'],
                        server['api_url'],
                        server['api_token_hash'],
                        server['name']
                    )
                    for server in batch
                ]
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Metrics collection exception: {result}")
                        self.collections_failed += 1
                    else:
                        results.append(result)
                        if result.get('status') == 'success':
                            self.collections_successful += 1
                        else:
                            self.collections_failed += 1
                
                # Delay between batches to avoid overwhelming servers
                if i + batch_size < server_count:
                    await asyncio.sleep(1.0)
            
            self.collections_performed += server_count
            
            # Calculate statistics
            successful = len([r for r in results if r.get('status') == 'success'])
            failed = len([r for r in results if r.get('status') == 'error'])
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.last_duration = duration
            
            logger.info(
                f"Metrics collection complete: {server_count} servers in {duration:.2f}s "
                f"(✓{successful} ❌{failed})"
            )
            
            # Log failed collections for investigation
            if failed > 0:
                failed_servers = [r['server_name'] for r in results if r.get('status') == 'error']
                logger.warning(f"Failed to collect metrics from: {', '.join(failed_servers[:5])}")
            
            # Check for partition health (ensure current month partition exists)
            await self._check_partition_health()
        
        except Exception as e:
            logger.error(f"Metrics collection worker error: {e}", exc_info=True)
    
    async def _check_partition_health(self):
        """Check if current month partition exists, log warning if not"""
        try:
            current_month = datetime.utcnow().strftime('%Y_%m')
            partition_name = f"server_metrics_aggregated_{current_month}"
            
            async with self.db_pool.acquire() as conn:
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_tables 
                        WHERE tablename = $1
                    )
                    """,
                    partition_name
                )
            
            if not exists:
                logger.error(
                    f"⚠️ PARTITION MISSING: {partition_name} does not exist! "
                    f"Metrics collection will fail. Create partition immediately."
                )
        
        except Exception as e:
            logger.error(f"Partition health check failed: {e}")
    
    async def _worker_loop(self):
        """Main worker loop"""
        logger.info(f"📊 Fleet metrics worker started (collecting every {self.interval}s)")
        
        while self.running:
            try:
                self.last_run = datetime.utcnow()
                await self._perform_metrics_collection()
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
            
            except asyncio.CancelledError:
                logger.info("Metrics worker received cancellation signal")
                break
            
            except Exception as e:
                logger.error(f"Metrics worker loop error: {e}", exc_info=True)
                # Continue after error, wait a bit longer
                await asyncio.sleep(self.interval * 2)
        
        logger.info("📊 Fleet metrics worker stopped")
    
    def start(self):
        """Start the background worker"""
        if self.running:
            logger.warning("Metrics worker already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._worker_loop())
        logger.info("Fleet metrics worker task created")
    
    async def stop(self):
        """Stop the background worker"""
        if not self.running:
            return
        
        logger.info("Stopping fleet metrics worker...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        
        await self.cleanup()
        logger.info("Fleet metrics worker stopped")
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "collections_performed": self.collections_performed,
            "collections_successful": self.collections_successful,
            "collections_failed": self.collections_failed,
            "success_rate": (
                self.collections_successful / self.collections_performed * 100 
                if self.collections_performed > 0 else 0
            ),
            "total_metrics_collected": self.total_metrics_collected,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_duration_seconds": self.last_duration
        }


# Global worker instance (initialized in server.py)
metrics_worker: Optional[FleetMetricsWorker] = None


async def start_metrics_worker(db_pool: asyncpg.Pool, interval: int = 60):
    """Start the global metrics worker"""
    global metrics_worker
    
    if metrics_worker and metrics_worker.running:
        logger.warning("Metrics worker already running")
        return metrics_worker
    
    metrics_worker = FleetMetricsWorker(db_pool, interval)
    await metrics_worker.initialize()
    metrics_worker.start()
    
    return metrics_worker


async def stop_metrics_worker():
    """Stop the global metrics worker"""
    global metrics_worker
    
    if metrics_worker:
        await metrics_worker.stop()
        metrics_worker = None


def get_metrics_worker() -> Optional[FleetMetricsWorker]:
    """Get the global metrics worker instance"""
    return metrics_worker
