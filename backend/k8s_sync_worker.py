"""
Epic 16: Kubernetes Integration - Sync Worker

Background worker to synchronize Kubernetes clusters.
Runs every 30 seconds to keep cluster state up-to-date.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from k8s_cluster_manager import KubernetesClusterManager

logger = logging.getLogger(__name__)


class KubernetesSyncWorker:
    """
    Background worker for Kubernetes cluster synchronization.
    
    Features:
    - Runs every 30 seconds
    - Batch processes multiple clusters (5 at a time)
    - Per-cluster error handling (doesn't fail entire batch)
    - Health status tracking
    - Graceful shutdown
    """
    
    def __init__(self, db_pool, interval: int = 30):
        """
        Initialize sync worker.
        
        Args:
            db_pool: Database connection pool
            interval: Sync interval in seconds (default: 30)
        """
        self.db_pool = db_pool
        self.interval = interval
        self.k8s_manager = KubernetesClusterManager(db_pool)
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_sync_at': None,
            'last_error': None
        }
    
    async def start(self):
        """Start the sync worker"""
        if self.running:
            logger.warning("K8s sync worker already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"🚀 Started K8s sync worker (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the sync worker gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping K8s sync worker...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ K8s sync worker stopped")
    
    async def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                await self._sync_all_clusters()
                await asyncio.sleep(self.interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"Error in K8s sync worker: {e}")
                self.stats['last_error'] = str(e)
                await asyncio.sleep(self.interval)
    
    async def _sync_all_clusters(self):
        """Sync all active clusters"""
        try:
            # Get all active clusters
            async with self.db_pool.acquire() as conn:
                clusters = await conn.fetch("""
                    SELECT id, name, organization_id
                    FROM k8s_clusters
                    WHERE status = 'active'
                    ORDER BY last_sync_at NULLS FIRST, id
                """)
            
            if not clusters:
                logger.debug("No active K8s clusters to sync")
                return
            
            logger.info(f"📊 Syncing {len(clusters)} K8s clusters...")
            
            # Process in batches of 5
            batch_size = 5
            for i in range(0, len(clusters), batch_size):
                batch = clusters[i:i + batch_size]
                
                # Sync batch concurrently
                tasks = [
                    self._sync_cluster_safe(cluster)
                    for cluster in batch
                ]
                await asyncio.gather(*tasks)
            
            # Update stats
            self.stats['last_sync_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"✅ Completed K8s cluster sync (total: {self.stats['total_syncs']}, "
                       f"successful: {self.stats['successful_syncs']}, "
                       f"failed: {self.stats['failed_syncs']})")
        
        except Exception as e:
            logger.error(f"Failed to sync K8s clusters: {e}")
            self.stats['last_error'] = str(e)
    
    async def _sync_cluster_safe(self, cluster):
        """Sync a single cluster with error handling"""
        cluster_id = cluster['id']
        cluster_name = cluster['name']
        
        try:
            self.stats['total_syncs'] += 1
            
            # Sync cluster
            await self.k8s_manager.sync_cluster(cluster_id)
            
            self.stats['successful_syncs'] += 1
            logger.debug(f"✅ Synced K8s cluster: {cluster_name}")
        
        except Exception as e:
            self.stats['failed_syncs'] += 1
            logger.error(f"❌ Failed to sync K8s cluster {cluster_name}: {e}")
            
            # Update cluster error status
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE k8s_clusters
                        SET last_error = $2,
                            health_status = 'critical',
                            updated_at = NOW()
                        WHERE id = $1
                    """, cluster_id, str(e))
            except Exception as update_error:
                logger.error(f"Failed to update cluster error status: {update_error}")
    
    def get_stats(self) -> dict:
        """Get worker statistics"""
        return {
            **self.stats,
            'running': self.running,
            'interval': self.interval
        }


# Global worker instance
_worker: Optional[KubernetesSyncWorker] = None


async def start_k8s_sync_worker(db_pool, interval: int = 30):
    """Start the global K8s sync worker"""
    global _worker
    
    if _worker is not None:
        logger.warning("K8s sync worker already started")
        return _worker
    
    _worker = KubernetesSyncWorker(db_pool, interval)
    await _worker.start()
    return _worker


async def stop_k8s_sync_worker():
    """Stop the global K8s sync worker"""
    global _worker
    
    if _worker is not None:
        await _worker.stop()
        _worker = None


def get_k8s_sync_worker() -> Optional[KubernetesSyncWorker]:
    """Get the global K8s sync worker"""
    return _worker
