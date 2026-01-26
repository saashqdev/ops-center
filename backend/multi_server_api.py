"""
Epic 15: Multi-Server Management - REST API
FastAPI endpoints for fleet dashboard
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query
from auth_dependencies import require_authenticated_user, require_admin_user
from multi_server_manager import MultiServerManager
from database import get_db_pool
from fleet_health_worker import get_health_worker
from fleet_metrics_worker import get_metrics_worker

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet-management"])


# ========== PYDANTIC MODELS ==========

class ServerRegistrationRequest(BaseModel):
    name: str = Field(..., description="Server name")
    hostname: str = Field(..., description="Server hostname")
    api_url: str = Field(..., description="Server API URL")
    api_token: str = Field(..., description="API token for authentication")
    description: Optional[str] = None
    region: Optional[str] = None
    environment: Optional[str] = Field(None, description="e.g., production, staging, development")
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


class ServerUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    environment: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, description="active, inactive, maintenance")


class ServerGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = Field(None, description="Hex color code, e.g., #3B82F6")
    tags: Optional[List[str]] = []
    regions: Optional[List[str]] = []
    environments: Optional[List[str]] = []


class GroupMembershipRequest(BaseModel):
    server_id: str
    group_id: str


class FleetOperationRequest(BaseModel):
    operation_type: str = Field(..., description="e.g., restart, update, backup")
    server_ids: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = {}


class HealthCheckResponse(BaseModel):
    server_id: str
    status: str
    response_time_ms: Optional[int] = None
    timestamp: str
    error: Optional[str] = None


class ServerResponse(BaseModel):
    id: str
    name: str
    hostname: str
    api_url: str
    status: str
    health_status: Optional[str] = None
    region: Optional[str] = None
    environment: Optional[str] = None
    tags: List[str]
    metadata: Dict[str, Any]
    last_seen_at: Optional[datetime] = None
    last_health_check_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class FleetSummaryResponse(BaseModel):
    organization_id: str
    total_servers: int
    active_servers: int
    inactive_servers: int
    maintenance_servers: int
    healthy_servers: int
    degraded_servers: int
    critical_servers: int
    unreachable_servers: int
    regions_count: int
    environments_count: int


# ========== HELPER FUNCTIONS ==========

async def get_fleet_manager() -> MultiServerManager:
    """Dependency to get fleet manager instance"""
    db_pool = await get_db_pool()
    manager = MultiServerManager(db_pool)
    await manager.initialize()
    try:
        yield manager
    finally:
        await manager.cleanup()


# ========== SERVER MANAGEMENT ENDPOINTS ==========

@router.post("/servers", status_code=201)
async def register_server(
    request: ServerRegistrationRequest,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Register a new managed server
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    try:
        server = await manager.register_server(
            organization_id=org_id,
            name=request.name,
            hostname=request.hostname,
            api_url=request.api_url,
            api_token=request.api_token,
            description=request.description,
            region=request.region,
            environment=request.environment,
            tags=request.tags,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "server": server,
            "message": f"Server {request.name} registered successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/servers")
async def list_servers(
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, maintenance"),
    health_status: Optional[str] = Query(None, description="Filter by health: healthy, degraded, critical, unreachable"),
    region: Optional[str] = None,
    environment: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    List all managed servers in organization
    
    Supports filtering by status, health, region, environment, and tags
    """
    org_id = user.get('organization_id')
    
    tag_list = tags.split(',') if tags else None
    
    servers = await manager.list_servers(
        organization_id=org_id,
        status=status,
        health_status=health_status,
        region=region,
        environment=environment,
        tags=tag_list,
        limit=limit,
        offset=offset
    )
    
    return {
        "servers": servers,
        "count": len(servers),
        "limit": limit,
        "offset": offset
    }


@router.get("/servers/{server_id}")
async def get_server(
    server_id: str,
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get details for a specific server"""
    org_id = user.get('organization_id')
    
    server = await manager.get_server(server_id)
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Verify server belongs to user's organization
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"server": server}


@router.patch("/servers/{server_id}")
async def update_server(
    server_id: str,
    request: ServerUpdateRequest,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Update server configuration
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    # Verify server exists and belongs to org
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated_server = await manager.update_server(
        server_id=server_id,
        name=request.name,
        description=request.description,
        region=request.region,
        environment=request.environment,
        tags=request.tags,
        metadata=request.metadata,
        status=request.status
    )
    
    return {
        "success": True,
        "server": updated_server,
        "message": "Server updated successfully"
    }


@router.delete("/servers/{server_id}", status_code=204)
async def delete_server(
    server_id: str,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Remove a server from management
    
    Requires: Admin role
    Cascades to health checks and metrics
    """
    org_id = user.get('organization_id')
    
    # Verify server exists and belongs to org
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await manager.delete_server(server_id)


# ========== HEALTH CHECK ENDPOINTS ==========

@router.post("/servers/{server_id}/health-check")
async def trigger_health_check(
    server_id: str,
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Trigger immediate health check for a server"""
    org_id = user.get('organization_id')
    
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Note: In production, you'd retrieve the actual API token from secure storage
    result = await manager._perform_health_check(
        server_id,
        server['api_url'],
        "PLACEHOLDER_TOKEN"
    )
    
    return result


@router.post("/health-check/all")
async def check_all_servers(
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Trigger health checks for all active servers"""
    org_id = user.get('organization_id')
    
    results = await manager.check_all_servers_health(org_id)
    
    return {
        "results": results,
        "total": len(results),
        "healthy": len([r for r in results if r.get('status') == 'healthy']),
        "degraded": len([r for r in results if r.get('status') == 'degraded']),
        "critical": len([r for r in results if r.get('status') == 'critical']),
        "unreachable": len([r for r in results if r.get('status') == 'unreachable'])
    }


@router.get("/servers/{server_id}/health-history")
async def get_health_history(
    server_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get historical health check data for a server"""
    org_id = user.get('organization_id')
    
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    history = await manager.get_server_health_history(
        server_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return {
        "server_id": server_id,
        "health_checks": history,
        "count": len(history)
    }


# ========== METRICS ENDPOINTS ==========

@router.get("/servers/{server_id}/metrics")
async def get_server_metrics(
    server_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    period: str = Query("1m", description="1m, 5m, 1h, 1d"),
    limit: int = Query(1000, ge=1, le=10000),
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get historical metrics for a server"""
    org_id = user.get('organization_id')
    
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    metrics = await manager.get_server_metrics(
        server_id,
        start_time=start_time,
        end_time=end_time,
        period=period,
        limit=limit
    )
    
    return {
        "server_id": server_id,
        "period": period,
        "metrics": metrics,
        "count": len(metrics)
    }


@router.post("/servers/{server_id}/metrics/collect")
async def collect_metrics(
    server_id: str,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Trigger immediate metrics collection for a server
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    server = await manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if server['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await manager.collect_server_metrics(
        server_id,
        server['api_url'],
        "PLACEHOLDER_TOKEN"
    )
    
    return result


# ========== SERVER GROUPS ENDPOINTS ==========

@router.post("/groups", status_code=201)
async def create_group(
    request: ServerGroupRequest,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Create a new server group
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    group = await manager.create_group(
        organization_id=org_id,
        name=request.name,
        description=request.description,
        color=request.color,
        tags=request.tags,
        regions=request.regions,
        environments=request.environments
    )
    
    return {
        "success": True,
        "group": group,
        "message": f"Group {request.name} created successfully"
    }


@router.get("/groups")
async def list_groups(
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """List all server groups in organization"""
    org_id = user.get('organization_id')
    
    groups = await manager.list_groups(org_id)
    
    return {
        "groups": groups,
        "count": len(groups)
    }


@router.get("/groups/{group_id}")
async def get_group(
    group_id: str,
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get group details"""
    org_id = user.get('organization_id')
    
    group = await manager.get_group(group_id)
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"group": group}


@router.get("/groups/{group_id}/servers")
async def get_group_servers(
    group_id: str,
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get all servers in a group"""
    org_id = user.get('organization_id')
    
    group = await manager.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    servers = await manager.get_group_servers(group_id)
    
    return {
        "group_id": group_id,
        "servers": servers,
        "count": len(servers)
    }


@router.post("/groups/members")
async def add_server_to_group(
    request: GroupMembershipRequest,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Add a server to a group
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    # Verify both server and group belong to org
    server = await manager.get_server(request.server_id)
    group = await manager.get_group(request.group_id)
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if server['organization_id'] != org_id or group['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await manager.add_server_to_group(request.server_id, request.group_id)
    
    return {
        "success": True,
        "message": f"Server added to group"
    }


@router.delete("/groups/members")
async def remove_server_from_group(
    server_id: str = Query(...),
    group_id: str = Query(...),
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Remove a server from a group
    
    Requires: Admin role
    """
    org_id = user.get('organization_id')
    
    # Verify both server and group belong to org
    server = await manager.get_server(server_id)
    group = await manager.get_group(group_id)
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if server['organization_id'] != org_id or group['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await manager.remove_server_from_group(server_id, group_id)
    
    return {
        "success": True,
        "message": "Server removed from group"
    }


# ========== FLEET OPERATIONS ENDPOINTS ==========

@router.post("/operations", status_code=201)
async def create_fleet_operation(
    request: FleetOperationRequest,
    user=Depends(require_admin_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Create a fleet-wide operation (bulk action)
    
    Requires: Admin role
    Examples: restart, update, backup, configuration change
    """
    org_id = user.get('organization_id')
    
    operation_id = await manager.create_fleet_operation(
        operation_type=request.operation_type,
        initiated_by=user['id'],
        server_ids=request.server_ids,
        group_ids=request.group_ids,
        filter_criteria=request.filter_criteria,
        parameters=request.parameters
    )
    
    return {
        "success": True,
        "operation_id": operation_id,
        "message": f"Fleet operation {request.operation_type} created"
    }


@router.get("/operations/{operation_id}")
async def get_fleet_operation(
    operation_id: str,
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """Get fleet operation details and status"""
    org_id = user.get('organization_id')
    
    operation = await manager.get_fleet_operation(operation_id)
    
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    return {"operation": operation}


# ========== FLEET SUMMARY ENDPOINT ==========

@router.get("/summary")
async def get_fleet_summary(
    user=Depends(require_authenticated_user),
    manager: MultiServerManager = Depends(get_fleet_manager)
):
    """
    Get fleet summary for organization
    
    Provides high-level overview of all managed servers
    """
    org_id = user.get('organization_id')
    
    summary = await manager.get_fleet_summary(org_id)
    
    return {"summary": summary}


# ========== WORKER STATUS ENDPOINTS ==========

@router.get("/workers/status")
async def get_worker_status(
    user=Depends(require_admin_user)
):
    """
    Get status of background workers
    
    Requires: Admin role
    Shows health check and metrics collection worker statistics
    """
    org_id = user.get('organization_id')
    
    health_worker = get_health_worker()
    metrics_worker = get_metrics_worker()
    
    return {
        "health_worker": health_worker.get_stats() if health_worker else {"running": False},
        "metrics_worker": metrics_worker.get_stats() if metrics_worker else {"running": False},
        "timestamp": datetime.utcnow().isoformat()
    }
