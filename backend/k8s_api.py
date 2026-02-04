"""
Epic 16: Kubernetes Integration - REST API

Complete REST API for Kubernetes cluster management.
Provides 19 endpoints for cluster operations, monitoring, and cost tracking.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_dependencies import require_authenticated_user, require_admin_user
from database import get_db_pool
from k8s_cluster_manager import KubernetesClusterManager
from k8s_sync_worker import get_k8s_sync_worker
from k8s_cost_calculator import get_k8s_cost_calculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/k8s", tags=["Kubernetes"])


# =====================================================================
# REQUEST/RESPONSE MODELS
# =====================================================================

class ClusterRegisterRequest(BaseModel):
    """Register a new Kubernetes cluster"""
    name: str = Field(..., description="Cluster name")
    kubeconfig: str = Field(..., description="Kubeconfig YAML content")
    description: Optional[str] = Field(None, description="Cluster description")
    environment: Optional[str] = Field(None, description="Environment: production, staging, development")
    tags: Optional[List[str]] = Field(None, description="Tags for filtering")


class ClusterUpdateRequest(BaseModel):
    """Update cluster configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    environment: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class ClusterResponse(BaseModel):
    """Cluster response"""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    api_server_url: str
    cluster_version: Optional[str]
    provider: Optional[str]
    environment: Optional[str]
    status: str
    health_status: Optional[str]
    total_nodes: Optional[int]
    total_namespaces: Optional[int]
    total_deployments: Optional[int]
    total_pods: Optional[int]
    tags: Optional[List[str]]
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class SyncTriggerResponse(BaseModel):
    """Sync trigger response"""
    cluster_id: str
    message: str
    triggered_at: datetime


class NamespaceResponse(BaseModel):
    """Namespace response"""
    id: str
    cluster_id: str
    name: str
    status: str
    team_name: Optional[str]
    cost_center: Optional[str]
    cpu_request: Optional[str]
    memory_request: Optional[str]
    cpu_limit: Optional[str]
    memory_limit: Optional[str]
    total_cost: Optional[float]
    pod_count: Optional[int]
    deployment_count: Optional[int]
    last_sync_at: Optional[datetime]


class NodeResponse(BaseModel):
    """Node response"""
    id: str
    cluster_id: str
    name: str
    node_type: str
    instance_type: Optional[str]
    cpu_capacity: Optional[str]
    memory_capacity: Optional[str]
    pod_capacity: Optional[str]
    cpu_allocatable: Optional[str]
    memory_allocatable: Optional[str]
    status: str
    last_sync_at: Optional[datetime]


class DeploymentResponse(BaseModel):
    """Deployment response"""
    id: str
    cluster_id: str
    namespace_id: str
    name: str
    replicas_desired: int
    replicas_current: Optional[int]
    replicas_ready: Optional[int]
    replicas_available: Optional[int]
    health_status: Optional[str]
    status: str
    strategy: Optional[str]
    last_sync_at: Optional[datetime]


class PodResponse(BaseModel):
    """Pod response"""
    id: str
    namespace_id: str
    name: str
    status: str
    phase: str
    node_name: Optional[str]
    host_ip: Optional[str]
    pod_ip: Optional[str]
    container_count: Optional[int]
    restart_count: Optional[int]
    cpu_request: Optional[str]
    memory_request: Optional[str]
    started_at: Optional[datetime]


class CostResponse(BaseModel):
    """Cost attribution response"""
    namespace_id: str
    namespace_name: str
    cluster_name: str
    team_name: Optional[str]
    cost_center: Optional[str]
    period_start: datetime
    period_end: datetime
    period_type: str
    cpu_cost: float
    memory_cost: float
    storage_cost: float
    network_cost: float
    total_cost: float
    cpu_hours: float
    memory_gb_hours: float


class HelmReleaseResponse(BaseModel):
    """Helm release response"""
    id: str
    namespace_id: str
    release_name: str
    chart_name: str
    chart_version: str
    app_version: Optional[str]
    status: str
    revision: int


# =====================================================================
# CLUSTER ENDPOINTS
# =====================================================================

@router.post("/clusters", response_model=ClusterResponse)
async def register_cluster(
    request: ClusterRegisterRequest,
    user=Depends(require_admin_user)
):
    """
    Register a new Kubernetes cluster.
    
    Requires admin access.
    """
    try:
        org_id = user.get('organization_id')
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        cluster = await manager.register_cluster(
            organization_id=org_id,
            name=request.name,
            kubeconfig_content=request.kubeconfig,
            description=request.description,
            environment=request.environment,
            tags=request.tags,
            created_by=user.get('user_id')
        )
        
        return cluster
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register cluster: {e}")
        raise HTTPException(status_code=500, detail="Failed to register cluster")


@router.get("/clusters", response_model=List[ClusterResponse])
async def list_clusters(
    status: Optional[str] = Query(None, description="Filter by status"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_authenticated_user)
):
    """
    List all Kubernetes clusters.
    
    Supports filtering by status, environment, and provider.
    """
    try:
        org_id = user.get('organization_id')
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        clusters = await manager.list_clusters(
            organization_id=org_id,
            status=status,
            environment=environment,
            provider=provider,
            limit=limit,
            offset=offset
        )
        
        return clusters
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list clusters: {e}")
        raise HTTPException(status_code=500, detail="Failed to list clusters")


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    user=Depends(require_authenticated_user)
):
    """Get cluster details by ID"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        cluster = await manager.get_cluster(cluster_id, org_id)
        
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        return cluster
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cluster: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cluster")


@router.patch("/clusters/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: str,
    request: ClusterUpdateRequest,
    user=Depends(require_admin_user)
):
    """
    Update cluster configuration.
    
    Requires admin access.
    """
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        # Build update dict
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.description is not None:
            updates['description'] = request.description
        if request.environment is not None:
            updates['environment'] = request.environment
        if request.tags is not None:
            updates['tags'] = request.tags
        if request.status is not None:
            updates['status'] = request.status
        
        cluster = await manager.update_cluster(cluster_id, org_id, **updates)
        
        return cluster
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update cluster: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cluster")


@router.delete("/clusters/{cluster_id}")
async def delete_cluster(
    cluster_id: str,
    user=Depends(require_admin_user)
):
    """
    Delete a cluster.
    
    Cascades to all related data (namespaces, nodes, etc.).
    Requires admin access.
    """
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        await manager.delete_cluster(cluster_id, org_id)
        
        return {"message": "Cluster deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete cluster: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete cluster")


@router.post("/clusters/{cluster_id}/sync", response_model=SyncTriggerResponse)
async def trigger_cluster_sync(
    cluster_id: str,
    user=Depends(require_admin_user)
):
    """
    Trigger immediate cluster synchronization.
    
    Requires admin access.
    """
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        manager = KubernetesClusterManager(db_pool)
        
        # Verify cluster exists and belongs to org
        cluster = await manager.get_cluster(cluster_id, org_id)
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Trigger sync asynchronously
        import asyncio
        asyncio.create_task(manager.sync_cluster(cluster_id))
        
        return {
            "cluster_id": cluster_id,
            "message": "Sync triggered successfully",
            "triggered_at": datetime.utcnow()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger sync")


@router.get("/clusters/{cluster_id}/health")
async def get_cluster_health(
    cluster_id: str,
    user=Depends(require_authenticated_user)
):
    """Get cluster health status"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            health = await conn.fetchrow("""
                SELECT * FROM v_k8s_cluster_health
                WHERE cluster_id = $1 AND organization_id = $2
            """, cluster_id, org_id)
            
            if not health:
                raise HTTPException(status_code=404, detail="Cluster not found")
            
            return dict(health)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cluster health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cluster health")


# =====================================================================
# NAMESPACE ENDPOINTS
# =====================================================================

@router.get("/clusters/{cluster_id}/namespaces", response_model=List[NamespaceResponse])
async def list_namespaces(
    cluster_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_authenticated_user)
):
    """List namespaces in a cluster"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            namespaces = await conn.fetch("""
                SELECT 
                    ns.*,
                    COUNT(DISTINCT d.id) as deployment_count,
                    COUNT(DISTINCT p.id) as pod_count
                FROM k8s_namespaces ns
                LEFT JOIN k8s_deployments d ON d.namespace_id = ns.id
                LEFT JOIN k8s_pods p ON p.namespace_id = ns.id
                WHERE ns.cluster_id = $1 AND ns.organization_id = $2
                GROUP BY ns.id
                ORDER BY ns.name
                LIMIT $3 OFFSET $4
            """, cluster_id, org_id, limit, offset)
            
            return [dict(ns) for ns in namespaces]
    
    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(status_code=500, detail="Failed to list namespaces")


@router.get("/namespaces/{namespace_id}/costs", response_model=List[CostResponse])
async def get_namespace_costs(
    namespace_id: str,
    period_type: str = Query("hourly", description="hourly, daily, or monthly"),
    days: int = Query(7, ge=1, le=90, description="Number of days to fetch"),
    user=Depends(require_authenticated_user)
):
    """Get cost breakdown for a namespace"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            costs = await conn.fetch("""
                SELECT 
                    c.*,
                    ns.name as namespace_name,
                    cl.name as cluster_name
                FROM k8s_cost_attribution c
                JOIN k8s_namespaces ns ON ns.id = c.namespace_id
                JOIN k8s_clusters cl ON cl.id = c.cluster_id
                WHERE c.namespace_id = $1 
                AND c.organization_id = $2
                AND c.period_type = $3
                AND c.period_start >= $4
                ORDER BY c.period_start DESC
            """, namespace_id, org_id, period_type, start_date)
            
            return [dict(cost) for cost in costs]
    
    except Exception as e:
        logger.error(f"Failed to get namespace costs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get namespace costs")


# =====================================================================
# NODE ENDPOINTS
# =====================================================================

@router.get("/clusters/{cluster_id}/nodes", response_model=List[NodeResponse])
async def list_nodes(
    cluster_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    user=Depends(require_authenticated_user)
):
    """List nodes in a cluster"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            query = """
                SELECT n.*
                FROM k8s_nodes n
                JOIN k8s_clusters c ON c.id = n.cluster_id
                WHERE n.cluster_id = $1 AND c.organization_id = $2
            """
            params = [cluster_id, org_id]
            
            if status:
                query += " AND n.status = $3"
                params.append(status)
            
            query += " ORDER BY n.name"
            
            nodes = await conn.fetch(query, *params)
            
            return [dict(node) for node in nodes]
    
    except Exception as e:
        logger.error(f"Failed to list nodes: {e}")
        raise HTTPException(status_code=500, detail="Failed to list nodes")


# =====================================================================
# DEPLOYMENT ENDPOINTS
# =====================================================================

@router.get("/namespaces/{namespace_id}/deployments", response_model=List[DeploymentResponse])
async def list_deployments(
    namespace_id: str,
    user=Depends(require_authenticated_user)
):
    """List deployments in a namespace"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            deployments = await conn.fetch("""
                SELECT d.*
                FROM k8s_deployments d
                WHERE d.namespace_id = $1 AND d.organization_id = $2
                ORDER BY d.name
            """, namespace_id, org_id)
            
            return [dict(deploy) for deploy in deployments]
    
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        raise HTTPException(status_code=500, detail="Failed to list deployments")


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    user=Depends(require_authenticated_user)
):
    """Get deployment details"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            deployment = await conn.fetchrow("""
                SELECT * FROM k8s_deployments
                WHERE id = $1 AND organization_id = $2
            """, deployment_id, org_id)
            
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            return dict(deployment)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deployment")


@router.get("/deployments/{deployment_id}/pods", response_model=List[PodResponse])
async def get_deployment_pods(
    deployment_id: str,
    user=Depends(require_authenticated_user)
):
    """Get pods for a deployment"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            # Get deployment namespace
            deployment = await conn.fetchrow("""
                SELECT namespace_id, name FROM k8s_deployments
                WHERE id = $1 AND organization_id = $2
            """, deployment_id, org_id)
            
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            # Get pods matching deployment name pattern
            pods = await conn.fetch("""
                SELECT * FROM k8s_pods
                WHERE namespace_id = $1
                AND name LIKE $2
                ORDER BY started_at DESC
            """, deployment['namespace_id'], f"{deployment['name']}-%")
            
            return [dict(pod) for pod in pods]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment pods: {e}")
        raise HTTPException(status_code=500, detail="Failed to get deployment pods")


# =====================================================================
# POD ENDPOINTS
# =====================================================================

@router.get("/namespaces/{namespace_id}/pods", response_model=List[PodResponse])
async def list_pods(
    namespace_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_authenticated_user)
):
    """List pods in a namespace"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            query = """
                SELECT p.*
                FROM k8s_pods p
                JOIN k8s_namespaces ns ON ns.id = p.namespace_id
                WHERE p.namespace_id = $1 AND ns.organization_id = $2
            """
            params = [namespace_id, org_id]
            
            if status:
                query += " AND p.status = $3"
                params.append(status)
            
            query += f" ORDER BY p.started_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
            params.extend([limit, offset])
            
            pods = await conn.fetch(query, *params)
            
            return [dict(pod) for pod in pods]
    
    except Exception as e:
        logger.error(f"Failed to list pods: {e}")
        raise HTTPException(status_code=500, detail="Failed to list pods")


@router.get("/pods/{pod_id}", response_model=PodResponse)
async def get_pod(
    pod_id: str,
    user=Depends(require_authenticated_user)
):
    """Get pod details"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            pod = await conn.fetchrow("""
                SELECT p.*
                FROM k8s_pods p
                JOIN k8s_namespaces ns ON ns.id = p.namespace_id
                WHERE p.id = $1 AND ns.organization_id = $2
            """, pod_id, org_id)
            
            if not pod:
                raise HTTPException(status_code=404, detail="Pod not found")
            
            return dict(pod)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pod: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pod")


# =====================================================================
# HELM ENDPOINTS
# =====================================================================

@router.get("/helm/releases", response_model=List[HelmReleaseResponse])
async def list_helm_releases(
    namespace_id: Optional[str] = Query(None, description="Filter by namespace"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_authenticated_user)
):
    """List Helm releases"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        async with db_pool.acquire() as conn:
            query = """
                SELECT h.*
                FROM k8s_helm_releases h
                JOIN k8s_namespaces ns ON ns.id = h.namespace_id
                WHERE ns.organization_id = $1
            """
            params = [org_id]
            
            if namespace_id:
                params.append(namespace_id)
                query += f" AND h.namespace_id = ${len(params)}"
            
            query += f" ORDER BY h.updated_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
            params.extend([limit, offset])
            
            releases = await conn.fetch(query, *params)
            
            return [dict(release) for release in releases]
    
    except Exception as e:
        logger.error(f"Failed to list Helm releases: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Helm releases")


# =====================================================================
# METRICS ENDPOINTS
# =====================================================================

@router.get("/metrics/cluster/{cluster_id}")
async def get_cluster_metrics(
    cluster_id: str,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to fetch"),
    user=Depends(require_authenticated_user)
):
    """Get cluster resource metrics"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with db_pool.acquire() as conn:
            metrics = await conn.fetch("""
                SELECT 
                    date_trunc('hour', m.timestamp) as hour,
                    AVG(m.cpu_usage_cores) as avg_cpu,
                    AVG(m.memory_usage_bytes / 1073741824.0) as avg_memory_gb,
                    SUM(m.network_rx_bytes + m.network_tx_bytes) / 1073741824.0 as network_gb
                FROM k8s_resource_metrics m
                JOIN k8s_namespaces ns ON ns.id = m.namespace_id
                WHERE ns.cluster_id = $1 
                AND ns.organization_id = $2
                AND m.timestamp >= $3
                GROUP BY hour
                ORDER BY hour DESC
            """, cluster_id, org_id, start_time)
            
            return [dict(metric) for metric in metrics]
    
    except Exception as e:
        logger.error(f"Failed to get cluster metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cluster metrics")


@router.get("/metrics/namespace/{namespace_id}")
async def get_namespace_metrics(
    namespace_id: str,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to fetch"),
    user=Depends(require_authenticated_user)
):
    """Get namespace resource metrics"""
    try:
        org_id = user.get('organization_id')
        if not org_id:
            raise HTTPException(status_code=400, detail="User must belong to an organization")
        
        db_pool = await get_db_pool()
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with db_pool.acquire() as conn:
            metrics = await conn.fetch("""
                SELECT 
                    date_trunc('hour', m.timestamp) as hour,
                    AVG(m.cpu_usage_cores) as avg_cpu,
                    AVG(m.memory_usage_bytes / 1073741824.0) as avg_memory_gb,
                    SUM(m.network_rx_bytes + m.network_tx_bytes) / 1073741824.0 as network_gb
                FROM k8s_resource_metrics m
                JOIN k8s_namespaces ns ON ns.id = m.namespace_id
                WHERE m.namespace_id = $1 
                AND ns.organization_id = $2
                AND m.timestamp >= $3
                GROUP BY hour
                ORDER BY hour DESC
            """, namespace_id, org_id, start_time)
            
            return [dict(metric) for metric in metrics]
    
    except Exception as e:
        logger.error(f"Failed to get namespace metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get namespace metrics")


# =====================================================================
# WORKER STATUS ENDPOINT (ADMIN ONLY)
# =====================================================================

@router.get("/workers/status")
async def get_workers_status(user=Depends(require_admin_user)):
    """
    Get status of K8s background workers.
    
    Requires admin access.
    """
    sync_worker = get_k8s_sync_worker()
    cost_calculator = get_k8s_cost_calculator()
    
    return {
        "sync_worker": sync_worker.get_stats() if sync_worker else {"running": False},
        "cost_calculator": cost_calculator.get_stats() if cost_calculator else {"running": False}
    }
