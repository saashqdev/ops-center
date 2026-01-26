"""
Epic 16: Kubernetes Integration - Cluster Manager

Core business logic for Kubernetes cluster management.
Handles cluster registration, synchronization, and operations.
"""

import os
import json
import base64
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from cryptography.fernet import Fernet
import yaml

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesClusterManager:
    """
    Manages Kubernetes cluster operations.
    
    Features:
    - Cluster registration with encrypted kubeconfig storage
    - Cluster health monitoring
    - Namespace, node, deployment, pod synchronization
    - Resource metrics collection
    - Cost attribution support
    """
    
    def __init__(self, db_pool):
        """Initialize with database connection pool"""
        self.db_pool = db_pool
        
        # Get encryption key from environment
        self.encryption_key = os.getenv('BYOK_ENCRYPTION_KEY')
        if not self.encryption_key:
            logger.warning("BYOK_ENCRYPTION_KEY not set - using default (INSECURE)")
            self.encryption_key = 'IbK1FMAifmKLomWWd4qRNdfg8P6ZOJFhdMwuHXtjFoc='
        
        self.cipher = Fernet(self.encryption_key.encode())
    
    # =====================================================================
    # CLUSTER MANAGEMENT
    # =====================================================================
    
    async def register_cluster(
        self,
        organization_id: str,
        name: str,
        kubeconfig_content: str,
        description: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new Kubernetes cluster.
        
        Args:
            organization_id: Organization owning the cluster
            name: Cluster name
            kubeconfig_content: Raw kubeconfig YAML content
            description: Optional cluster description
            environment: production, staging, development
            tags: Optional tags for filtering
            created_by: User ID who registered the cluster
        
        Returns:
            Cluster record
        """
        try:
            # Parse kubeconfig to extract metadata
            kubeconfig = yaml.safe_load(kubeconfig_content)
            
            # Get current context
            current_context = kubeconfig.get('current-context')
            if not current_context:
                raise ValueError("No current-context in kubeconfig")
            
            # Find context details
            context_obj = next(
                (ctx for ctx in kubeconfig.get('contexts', []) 
                 if ctx['name'] == current_context),
                None
            )
            if not context_obj:
                raise ValueError(f"Context '{current_context}' not found in kubeconfig")
            
            # Get cluster details
            cluster_name = context_obj['context']['cluster']
            cluster_obj = next(
                (cls for cls in kubeconfig.get('clusters', []) 
                 if cls['name'] == cluster_name),
                None
            )
            if not cluster_obj:
                raise ValueError(f"Cluster '{cluster_name}' not found in kubeconfig")
            
            api_server_url = cluster_obj['cluster']['server']
            
            # Encrypt kubeconfig
            kubeconfig_encrypted = self.cipher.encrypt(kubeconfig_content.encode()).decode()
            
            # Test connection to get cluster version
            cluster_version, provider = await self._detect_cluster_info(kubeconfig_content)
            
            # Insert cluster record
            async with self.db_pool.acquire() as conn:
                cluster = await conn.fetchrow("""
                    INSERT INTO k8s_clusters (
                        organization_id, name, description,
                        kubeconfig_encrypted, context_name, api_server_url,
                        cluster_version, provider, environment,
                        tags, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING *
                """, 
                    organization_id, name, description,
                    kubeconfig_encrypted, current_context, api_server_url,
                    cluster_version, provider, environment,
                    json.dumps(tags or []), created_by
                )
                
                logger.info(f"Registered cluster '{name}' for org {organization_id}")
                
                # Trigger initial sync
                asyncio.create_task(self.sync_cluster(cluster['id']))
                
                return dict(cluster)
        
        except Exception as e:
            logger.error(f"Failed to register cluster: {e}")
            raise
    
    async def _detect_cluster_info(self, kubeconfig_content: str) -> tuple:
        """Detect cluster version and provider from kubeconfig"""
        try:
            # Create temporary kubeconfig file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(kubeconfig_content)
                kubeconfig_path = f.name
            
            try:
                # Load kubeconfig
                config.load_kube_config(config_file=kubeconfig_path)
                
                # Create API client
                v1 = client.CoreV1Api()
                
                # Get cluster version
                version_info = await asyncio.to_thread(v1.get_api_resources)
                version = version_info.group_version if hasattr(version_info, 'group_version') else 'unknown'
                
                # Detect provider from node labels
                try:
                    nodes = await asyncio.to_thread(v1.list_node)
                    if nodes.items:
                        labels = nodes.items[0].metadata.labels
                        
                        # Detect provider
                        if 'eks.amazonaws.com' in str(labels):
                            provider = 'eks'
                        elif 'cloud.google.com/gke' in str(labels):
                            provider = 'gke'
                        elif 'kubernetes.azure.com' in str(labels):
                            provider = 'aks'
                        elif 'node.kubernetes.io/instance-type' in labels and 'k3s' in str(labels):
                            provider = 'k3s'
                        else:
                            provider = 'vanilla'
                        
                        # Get actual version
                        version = nodes.items[0].status.node_info.kubelet_version
                    else:
                        provider = 'unknown'
                
                except Exception as e:
                    logger.warning(f"Could not detect provider: {e}")
                    provider = 'unknown'
                
                return version, provider
            
            finally:
                # Clean up temp file
                os.unlink(kubeconfig_path)
        
        except Exception as e:
            logger.warning(f"Could not detect cluster info: {e}")
            return 'unknown', 'unknown'
    
    async def get_cluster(self, cluster_id: str, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get cluster by ID"""
        async with self.db_pool.acquire() as conn:
            cluster = await conn.fetchrow("""
                SELECT * FROM k8s_clusters
                WHERE id = $1 AND organization_id = $2
            """, cluster_id, organization_id)
            
            if not cluster:
                return None
            
            # Don't return encrypted kubeconfig
            result = dict(cluster)
            result.pop('kubeconfig_encrypted', None)
            return result
    
    async def list_clusters(
        self,
        organization_id: str,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List clusters with optional filters"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT * FROM k8s_clusters
                WHERE organization_id = $1
            """
            params = [organization_id]
            param_count = 1
            
            if status:
                param_count += 1
                query += f" AND status = ${param_count}"
                params.append(status)
            
            if environment:
                param_count += 1
                query += f" AND environment = ${param_count}"
                params.append(environment)
            
            if provider:
                param_count += 1
                query += f" AND provider = ${param_count}"
                params.append(provider)
            
            query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
            params.extend([limit, offset])
            
            clusters = await conn.fetch(query, *params)
            
            # Remove encrypted kubeconfig from results
            results = []
            for cluster in clusters:
                result = dict(cluster)
                result.pop('kubeconfig_encrypted', None)
                results.append(result)
            
            return results
    
    async def update_cluster(
        self,
        cluster_id: str,
        organization_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update cluster configuration"""
        allowed_fields = ['name', 'description', 'environment', 'tags', 'status']
        
        set_clauses = []
        params = []
        param_count = 0
        
        for field, value in updates.items():
            if field in allowed_fields:
                param_count += 1
                set_clauses.append(f"{field} = ${param_count}")
                params.append(json.dumps(value) if field == 'tags' else value)
        
        if not set_clauses:
            raise ValueError("No valid fields to update")
        
        params.extend([cluster_id, organization_id])
        param_count += 2
        
        async with self.db_pool.acquire() as conn:
            cluster = await conn.fetchrow(f"""
                UPDATE k8s_clusters
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE id = ${param_count - 1} AND organization_id = ${param_count}
                RETURNING *
            """, *params)
            
            if not cluster:
                raise ValueError("Cluster not found")
            
            logger.info(f"Updated cluster {cluster_id}")
            result = dict(cluster)
            result.pop('kubeconfig_encrypted', None)
            return result
    
    async def delete_cluster(self, cluster_id: str, organization_id: str):
        """Delete a cluster (cascades to all related data)"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM k8s_clusters
                WHERE id = $1 AND organization_id = $2
            """, cluster_id, organization_id)
            
            if result == 'DELETE 0':
                raise ValueError("Cluster not found")
            
            logger.info(f"Deleted cluster {cluster_id}")
    
    # =====================================================================
    # CLUSTER SYNCHRONIZATION
    # =====================================================================
    
    async def sync_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """
        Full cluster synchronization.
        
        Syncs:
        - Cluster health
        - Namespaces
        - Nodes
        - Deployments
        - Pods (summary)
        """
        try:
            # Get cluster
            async with self.db_pool.acquire() as conn:
                cluster = await conn.fetchrow("""
                    SELECT * FROM k8s_clusters WHERE id = $1
                """, cluster_id)
                
                if not cluster:
                    raise ValueError("Cluster not found")
                
                # Decrypt kubeconfig
                kubeconfig_content = self.cipher.decrypt(
                    cluster['kubeconfig_encrypted'].encode()
                ).decode()
                
                # Create K8s client
                k8s_client = await self._get_k8s_client(kubeconfig_content)
                
                # Sync components
                health_status = await self._sync_cluster_health(k8s_client, cluster_id, conn)
                await self._sync_namespaces(k8s_client, cluster_id, cluster['organization_id'], conn)
                await self._sync_nodes(k8s_client, cluster_id, conn)
                await self._sync_deployments(k8s_client, cluster_id, conn)
                
                # Update cluster sync timestamp
                await conn.execute("""
                    UPDATE k8s_clusters
                    SET last_sync_at = NOW(),
                        health_status = $2,
                        last_error = NULL,
                        updated_at = NOW()
                    WHERE id = $1
                """, cluster_id, health_status)
                
                logger.info(f"✅ Synced cluster {cluster['name']} ({cluster_id})")
                
                return {
                    'cluster_id': cluster_id,
                    'synced_at': datetime.utcnow().isoformat(),
                    'health_status': health_status
                }
        
        except Exception as e:
            logger.error(f"❌ Failed to sync cluster {cluster_id}: {e}")
            
            # Update error status
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE k8s_clusters
                    SET last_error = $2,
                        health_status = 'critical',
                        updated_at = NOW()
                    WHERE id = $1
                """, cluster_id, str(e))
            
            raise
    
    async def _get_k8s_client(self, kubeconfig_content: str):
        """Create Kubernetes API client from kubeconfig"""
        import tempfile
        
        # Create temporary kubeconfig file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(kubeconfig_content)
            kubeconfig_path = f.name
        
        try:
            # Load kubeconfig
            config.load_kube_config(config_file=kubeconfig_path)
            return client
        finally:
            os.unlink(kubeconfig_path)
    
    async def _sync_cluster_health(self, k8s_client, cluster_id: str, conn) -> str:
        """Check cluster health"""
        try:
            v1 = k8s_client.CoreV1Api()
            
            # Get component statuses
            components = await asyncio.to_thread(v1.list_component_status)
            
            # Check if all components are healthy
            all_healthy = all(
                c.conditions and any(cond.type == 'Healthy' and cond.status == 'True' 
                                   for cond in c.conditions)
                for c in components.items
            )
            
            # Get node health
            nodes = await asyncio.to_thread(v1.list_node)
            healthy_nodes = sum(
                1 for node in nodes.items
                if any(cond.type == 'Ready' and cond.status == 'True' 
                      for cond in node.status.conditions)
            )
            total_nodes = len(nodes.items)
            
            # Determine health status
            if all_healthy and healthy_nodes == total_nodes:
                health_status = 'healthy'
            elif healthy_nodes >= total_nodes * 0.8:
                health_status = 'degraded'
            else:
                health_status = 'critical'
            
            # Update cluster counts
            await conn.execute("""
                UPDATE k8s_clusters
                SET total_nodes = $2
                WHERE id = $1
            """, cluster_id, total_nodes)
            
            return health_status
        
        except Exception as e:
            logger.error(f"Failed to check cluster health: {e}")
            return 'unknown'
    
    async def _sync_namespaces(self, k8s_client, cluster_id: str, organization_id: str, conn):
        """Sync namespaces"""
        try:
            v1 = k8s_client.CoreV1Api()
            namespaces = await asyncio.to_thread(v1.list_namespace)
            
            for ns in namespaces.items:
                # Extract team and cost center from labels
                labels = ns.metadata.labels or {}
                team_name = labels.get('team', labels.get('owner'))
                cost_center = labels.get('cost-center', labels.get('costCenter'))
                
                # Upsert namespace
                await conn.execute("""
                    INSERT INTO k8s_namespaces (
                        cluster_id, organization_id, name, namespace_uid, status,
                        team_name, cost_center, labels, last_sync_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    ON CONFLICT (cluster_id, name) DO UPDATE
                    SET status = EXCLUDED.status,
                        team_name = EXCLUDED.team_name,
                        cost_center = EXCLUDED.cost_center,
                        labels = EXCLUDED.labels,
                        last_sync_at = NOW(),
                        updated_at = NOW()
                """, cluster_id, organization_id, ns.metadata.name, ns.metadata.uid,
                    ns.status.phase, team_name, cost_center, json.dumps(labels))
            
            # Update cluster namespace count
            count = len(namespaces.items)
            await conn.execute("""
                UPDATE k8s_clusters SET total_namespaces = $2 WHERE id = $1
            """, cluster_id, count)
            
            logger.debug(f"Synced {count} namespaces for cluster {cluster_id}")
        
        except Exception as e:
            logger.error(f"Failed to sync namespaces: {e}")
    
    async def _sync_nodes(self, k8s_client, cluster_id: str, conn):
        """Sync nodes"""
        try:
            v1 = k8s_client.CoreV1Api()
            nodes = await asyncio.to_thread(v1.list_node)
            
            for node in nodes.items:
                # Get node status
                ready_condition = next(
                    (c for c in node.status.conditions if c.type == 'Ready'),
                    None
                )
                status = 'Ready' if ready_condition and ready_condition.status == 'True' else 'NotReady'
                
                # Get capacity
                capacity = node.status.capacity
                allocatable = node.status.allocatable
                
                # Determine node type
                labels = node.metadata.labels or {}
                node_type = 'master' if 'node-role.kubernetes.io/master' in labels else 'worker'
                
                # Get instance type
                instance_type = labels.get('node.kubernetes.io/instance-type', 
                                         labels.get('beta.kubernetes.io/instance-type', 'unknown'))
                
                # Upsert node
                await conn.execute("""
                    INSERT INTO k8s_nodes (
                        cluster_id, name, node_uid, node_type, instance_type,
                        cpu_capacity, memory_capacity, pod_capacity,
                        cpu_allocatable, memory_allocatable,
                        status, conditions, labels, last_sync_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
                    ON CONFLICT (cluster_id, name) DO UPDATE
                    SET status = EXCLUDED.status,
                        cpu_capacity = EXCLUDED.cpu_capacity,
                        memory_capacity = EXCLUDED.memory_capacity,
                        pod_capacity = EXCLUDED.pod_capacity,
                        cpu_allocatable = EXCLUDED.cpu_allocatable,
                        memory_allocatable = EXCLUDED.memory_allocatable,
                        conditions = EXCLUDED.conditions,
                        labels = EXCLUDED.labels,
                        last_sync_at = NOW(),
                        updated_at = NOW()
                """, cluster_id, node.metadata.name, node.metadata.uid, node_type, instance_type,
                    capacity.get('cpu'), capacity.get('memory'), capacity.get('pods'),
                    allocatable.get('cpu'), allocatable.get('memory'),
                    status, json.dumps([c.to_dict() for c in node.status.conditions]),
                    json.dumps(labels))
            
            logger.debug(f"Synced {len(nodes.items)} nodes for cluster {cluster_id}")
        
        except Exception as e:
            logger.error(f"Failed to sync nodes: {e}")
    
    async def _sync_deployments(self, k8s_client, cluster_id: str, conn):
        """Sync deployments across all namespaces"""
        try:
            apps_v1 = k8s_client.AppsV1Api()
            deployments = await asyncio.to_thread(apps_v1.list_deployment_for_all_namespaces)
            
            total_pods = 0
            
            for deploy in deployments.items:
                # Get namespace ID
                namespace_id = await conn.fetchval("""
                    SELECT id FROM k8s_namespaces
                    WHERE cluster_id = $1 AND name = $2
                """, cluster_id, deploy.metadata.namespace)
                
                if not namespace_id:
                    continue
                
                # Get organization from namespace
                org_id = await conn.fetchval("""
                    SELECT organization_id FROM k8s_namespaces WHERE id = $1
                """, namespace_id)
                
                # Extract container info
                containers = [
                    {
                        'name': c.name,
                        'image': c.image,
                        'resources': {
                            'requests': c.resources.requests if c.resources and c.resources.requests else {},
                            'limits': c.resources.limits if c.resources and c.resources.limits else {}
                        }
                    }
                    for c in deploy.spec.template.spec.containers
                ]
                
                # Determine health status
                ready = deploy.status.ready_replicas or 0
                desired = deploy.spec.replicas or 0
                
                if ready == desired and ready > 0:
                    health_status = 'healthy'
                elif ready >= desired * 0.5:
                    health_status = 'degraded'
                else:
                    health_status = 'failed'
                
                # Upsert deployment
                await conn.execute("""
                    INSERT INTO k8s_deployments (
                        cluster_id, namespace_id, organization_id,
                        name, deployment_uid,
                        replicas_desired, replicas_current, replicas_ready,
                        replicas_available, replicas_unavailable,
                        containers, status, health_status,
                        strategy, labels, annotations, last_sync_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW())
                    ON CONFLICT (namespace_id, name) DO UPDATE
                    SET replicas_desired = EXCLUDED.replicas_desired,
                        replicas_current = EXCLUDED.replicas_current,
                        replicas_ready = EXCLUDED.replicas_ready,
                        replicas_available = EXCLUDED.replicas_available,
                        replicas_unavailable = EXCLUDED.replicas_unavailable,
                        containers = EXCLUDED.containers,
                        status = EXCLUDED.status,
                        health_status = EXCLUDED.health_status,
                        labels = EXCLUDED.labels,
                        annotations = EXCLUDED.annotations,
                        last_sync_at = NOW(),
                        updated_at = NOW()
                """, cluster_id, namespace_id, org_id,
                    deploy.metadata.name, deploy.metadata.uid,
                    desired, deploy.status.replicas, ready,
                    deploy.status.available_replicas, deploy.status.unavailable_replicas,
                    json.dumps(containers), 'Running', health_status,
                    deploy.spec.strategy.type if deploy.spec.strategy else None,
                    json.dumps(deploy.metadata.labels or {}),
                    json.dumps(deploy.metadata.annotations or {}))
                
                total_pods += ready
            
            # Update cluster deployment and pod counts
            await conn.execute("""
                UPDATE k8s_clusters
                SET total_deployments = $2, total_pods = $3
                WHERE id = $1
            """, cluster_id, len(deployments.items), total_pods)
            
            logger.debug(f"Synced {len(deployments.items)} deployments for cluster {cluster_id}")
        
        except Exception as e:
            logger.error(f"Failed to sync deployments: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        pass
