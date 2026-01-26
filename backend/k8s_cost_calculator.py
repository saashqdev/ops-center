"""
Epic 16: Kubernetes Integration - Cost Calculator

Calculates namespace-level costs based on resource usage.
Runs hourly to attribute costs to teams and cost centers.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class KubernetesCostCalculator:
    """
    Calculates Kubernetes namespace costs.
    
    Cost Model:
    - vCPU-hour: $0.04 per hour per vCPU
    - GB-hour: $0.005 per hour per GB memory
    - Storage-GB-hour: $0.0001 per hour per GB
    - Network-GB: $0.05 per GB transferred
    
    Features:
    - Namespace-level cost attribution
    - Team and cost-center tagging
    - Hourly and daily aggregations
    - Resource-based allocation (requests + actual usage)
    """
    
    def __init__(self, db_pool):
        """Initialize with database connection pool"""
        self.db_pool = db_pool
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Pricing (per hour)
        self.pricing = {
            'vcpu_hour': Decimal('0.04'),      # $0.04 per vCPU-hour
            'memory_gb_hour': Decimal('0.005'), # $0.005 per GB-hour
            'storage_gb_hour': Decimal('0.0001'), # $0.0001 per GB-hour
            'network_gb': Decimal('0.05')       # $0.05 per GB
        }
        
        # Statistics
        self.stats = {
            'total_calculations': 0,
            'last_calculation_at': None,
            'last_error': None
        }
    
    async def start(self, interval: int = 3600):
        """
        Start the cost calculator worker.
        
        Args:
            interval: Calculation interval in seconds (default: 3600 = 1 hour)
        """
        if self.running:
            logger.warning("K8s cost calculator already running")
            return
        
        self.running = True
        self.interval = interval
        self.task = asyncio.create_task(self._run())
        logger.info(f"🚀 Started K8s cost calculator (interval: {interval}s)")
    
    async def stop(self):
        """Stop the cost calculator gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping K8s cost calculator...")
        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ K8s cost calculator stopped")
    
    async def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                await self._calculate_costs()
                await asyncio.sleep(self.interval)
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                logger.error(f"Error in K8s cost calculator: {e}")
                self.stats['last_error'] = str(e)
                await asyncio.sleep(self.interval)
    
    async def _calculate_costs(self):
        """Calculate costs for all namespaces"""
        try:
            logger.info("💰 Calculating K8s namespace costs...")
            
            # Get all namespaces with their clusters
            async with self.db_pool.acquire() as conn:
                namespaces = await conn.fetch("""
                    SELECT 
                        ns.id, ns.name, ns.cluster_id, ns.organization_id,
                        ns.team_name, ns.cost_center,
                        c.name as cluster_name, c.provider
                    FROM k8s_namespaces ns
                    JOIN k8s_clusters c ON c.id = ns.cluster_id
                    WHERE c.status = 'active'
                """)
            
            if not namespaces:
                logger.debug("No namespaces to calculate costs for")
                return
            
            # Calculate costs for each namespace
            for ns in namespaces:
                try:
                    await self._calculate_namespace_cost(ns)
                except Exception as e:
                    logger.error(f"Failed to calculate cost for namespace {ns['name']}: {e}")
            
            # Update stats
            self.stats['total_calculations'] += 1
            self.stats['last_calculation_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"✅ Completed K8s cost calculation for {len(namespaces)} namespaces")
        
        except Exception as e:
            logger.error(f"Failed to calculate K8s costs: {e}")
            self.stats['last_error'] = str(e)
    
    async def _calculate_namespace_cost(self, namespace: Dict[str, Any]):
        """Calculate cost for a single namespace"""
        namespace_id = namespace['id']
        
        async with self.db_pool.acquire() as conn:
            # Get resource requests from deployments
            deployments = await conn.fetch("""
                SELECT containers
                FROM k8s_deployments
                WHERE namespace_id = $1
            """, namespace_id)
            
            # Calculate total resource requests
            total_cpu_cores = Decimal('0')
            total_memory_gb = Decimal('0')
            
            for deploy in deployments:
                containers = deploy['containers']
                for container in containers:
                    resources = container.get('resources', {})
                    requests = resources.get('requests', {})
                    
                    # CPU (convert from millicores to cores)
                    cpu_str = requests.get('cpu', '0')
                    if cpu_str.endswith('m'):
                        cpu_cores = Decimal(cpu_str[:-1]) / 1000
                    else:
                        cpu_cores = Decimal(cpu_str) if cpu_str else Decimal('0')
                    total_cpu_cores += cpu_cores
                    
                    # Memory (convert to GB)
                    mem_str = requests.get('memory', '0')
                    memory_gb = self._parse_memory_to_gb(mem_str)
                    total_memory_gb += memory_gb
            
            # Get actual resource usage from metrics (last hour average)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            metrics = await conn.fetchrow("""
                SELECT 
                    AVG(cpu_usage_cores) as avg_cpu,
                    AVG(memory_usage_bytes / 1073741824.0) as avg_memory_gb,
                    AVG(network_rx_bytes + network_tx_bytes) / 1073741824.0 as network_gb
                FROM k8s_resource_metrics
                WHERE namespace_id = $1
                AND timestamp >= $2
            """, namespace_id, one_hour_ago)
            
            # Use greater of requests or actual usage
            actual_cpu = Decimal(str(metrics['avg_cpu'] or 0))
            actual_memory_gb = Decimal(str(metrics['avg_memory_gb'] or 0))
            network_gb = Decimal(str(metrics['network_gb'] or 0))
            
            cpu_for_cost = max(total_cpu_cores, actual_cpu)
            memory_for_cost = max(total_memory_gb, actual_memory_gb)
            
            # Calculate costs
            cpu_cost = cpu_for_cost * self.pricing['vcpu_hour']
            memory_cost = memory_for_cost * self.pricing['memory_gb_hour']
            network_cost = network_gb * self.pricing['network_gb']
            
            total_cost = cpu_cost + memory_cost + network_cost
            
            # Insert cost record
            await conn.execute("""
                INSERT INTO k8s_cost_attribution (
                    namespace_id, cluster_id, organization_id,
                    period_start, period_end, period_type,
                    cpu_cost, memory_cost, storage_cost, network_cost,
                    total_cost, cpu_hours, memory_gb_hours,
                    team_name, cost_center
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """, 
                namespace_id, namespace['cluster_id'], namespace['organization_id'],
                one_hour_ago, datetime.utcnow(), 'hourly',
                float(cpu_cost), float(memory_cost), 0.0, float(network_cost),
                float(total_cost), float(cpu_for_cost), float(memory_for_cost),
                namespace['team_name'], namespace['cost_center']
            )
            
            # Update namespace total cost
            await conn.execute("""
                UPDATE k8s_namespaces
                SET total_cost = COALESCE(total_cost, 0) + $2,
                    updated_at = NOW()
                WHERE id = $1
            """, namespace_id, float(total_cost))
            
            logger.debug(f"💰 Namespace {namespace['name']}: "
                        f"CPU=${cpu_cost:.4f}, "
                        f"Memory=${memory_cost:.4f}, "
                        f"Network=${network_cost:.4f}, "
                        f"Total=${total_cost:.4f}")
    
    def _parse_memory_to_gb(self, mem_str: str) -> Decimal:
        """Parse Kubernetes memory string to GB"""
        if not mem_str or mem_str == '0':
            return Decimal('0')
        
        mem_str = mem_str.upper()
        
        if mem_str.endswith('GI'):
            return Decimal(mem_str[:-2])
        elif mem_str.endswith('G'):
            return Decimal(mem_str[:-1])
        elif mem_str.endswith('MI'):
            return Decimal(mem_str[:-2]) / 1024
        elif mem_str.endswith('M'):
            return Decimal(mem_str[:-1]) / 1000
        elif mem_str.endswith('KI'):
            return Decimal(mem_str[:-2]) / (1024 * 1024)
        elif mem_str.endswith('K'):
            return Decimal(mem_str[:-1]) / (1000 * 1000)
        else:
            # Assume bytes
            return Decimal(mem_str) / 1073741824
    
    def get_stats(self) -> dict:
        """Get calculator statistics"""
        return {
            **self.stats,
            'running': self.running,
            'interval': getattr(self, 'interval', None),
            'pricing': {k: float(v) for k, v in self.pricing.items()}
        }


# Global calculator instance
_calculator: Optional[KubernetesCostCalculator] = None


async def start_k8s_cost_calculator(db_pool, interval: int = 3600):
    """Start the global K8s cost calculator"""
    global _calculator
    
    if _calculator is not None:
        logger.warning("K8s cost calculator already started")
        return _calculator
    
    _calculator = KubernetesCostCalculator(db_pool)
    await _calculator.start(interval)
    return _calculator


async def stop_k8s_cost_calculator():
    """Stop the global K8s cost calculator"""
    global _calculator
    
    if _calculator is not None:
        await _calculator.stop()
        _calculator = None


def get_k8s_cost_calculator() -> Optional[KubernetesCostCalculator]:
    """Get the global K8s cost calculator"""
    return _calculator
