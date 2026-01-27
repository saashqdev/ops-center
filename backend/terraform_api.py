"""
Terraform/IaC API Endpoints - Epic 19
REST API for Infrastructure as Code management

Provides:
- Workspace CRUD operations
- State file management
- Resource tracking
- Execution history
- Template library
- Variable management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from auth_dependencies import require_authenticated_user
from terraform_manager import get_terraform_manager, TerraformManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/terraform",
    tags=["terraform"]
)


# ==================== PYDANTIC MODELS ====================

class WorkspaceCreate(BaseModel):
    name: str
    cloud_provider: str = Field(..., pattern="^(aws|azure|gcp|digitalocean|kubernetes|multi)$")
    environment: str = Field(..., pattern="^(dev|staging|production|test)$")
    description: Optional[str] = None
    terraform_version: str = "1.6.0"
    auto_apply: bool = False


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    cloud_provider: str
    environment: str
    description: Optional[str]
    locked: bool
    locked_by: Optional[str]
    last_apply_at: Optional[datetime]
    resource_count: int
    active_resources: int
    drift_count: int
    state_version: int


class VariableCreate(BaseModel):
    key: str
    value: str
    is_sensitive: bool = False
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: Optional[str]
    category: str
    cloud_provider: str
    template_type: str
    source_code: str
    variables: Dict[str, Any]
    outputs: Dict[str, Any]
    version: str
    downloads_count: int
    tags: List[str]


# ==================== WORKSPACE ENDPOINTS ====================

@router.post("/workspaces")
async def create_workspace(
    workspace: WorkspaceCreate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Create a new Terraform workspace
    
    **Cloud Providers**: aws, azure, gcp, digitalocean, kubernetes, multi
    **Environments**: dev, staging, production, test
    """
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        workspace_id = await tm.create_workspace(
            name=workspace.name,
            cloud_provider=workspace.cloud_provider,
            environment=workspace.environment,
            description=workspace.description,
            created_by=user.get('email', 'unknown'),
            terraform_version=workspace.terraform_version,
            auto_apply=workspace.auto_apply
        )
        
        if not workspace_id:
            raise HTTPException(status_code=500, detail="Failed to create workspace")
        
        return {"workspace_id": workspace_id, "message": "Workspace created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces")
async def list_workspaces(
    cloud_provider: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    user: Dict = Depends(require_authenticated_user)
):
    """List all Terraform workspaces with filters"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        workspaces = await tm.list_workspaces(
            cloud_provider=cloud_provider,
            environment=environment
        )
        
        return workspaces
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Get workspace details"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        workspace = await tm.get_workspace(workspace_id)
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/lock")
async def lock_workspace(
    workspace_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Lock workspace to prevent concurrent modifications"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        success = await tm.lock_workspace(workspace_id, user.get('email', 'unknown'))
        
        if not success:
            raise HTTPException(status_code=409, detail="Workspace already locked")
        
        return {"message": "Workspace locked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error locking workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/unlock")
async def unlock_workspace(
    workspace_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Unlock workspace"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        success = await tm.unlock_workspace(workspace_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return {"message": "Workspace unlocked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlocking workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== STATE ENDPOINTS ====================

@router.get("/workspaces/{workspace_id}/state")
async def get_state(
    workspace_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Get current Terraform state"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        state = await tm.get_current_state(workspace_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RESOURCE ENDPOINTS ====================

@router.get("/workspaces/{workspace_id}/resources")
async def list_resources(
    workspace_id: str,
    resource_type: Optional[str] = Query(None),
    user: Dict = Depends(require_authenticated_user)
):
    """List workspace resources"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        resources = await tm.get_resources(
            workspace_id=workspace_id,
            resource_type=resource_type
        )
        
        return resources
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXECUTION ENDPOINTS ====================

@router.get("/workspaces/{workspace_id}/executions")
async def get_executions(
    workspace_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(require_authenticated_user)
):
    """Get execution history for workspace"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        executions = await tm.get_executions(
            workspace_id=workspace_id,
            limit=limit
        )
        
        return executions
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/recent")
async def get_recent_executions(
    limit: int = Query(50, ge=1, le=200),
    user: Dict = Depends(require_authenticated_user)
):
    """Get recent executions across all workspaces"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        executions = await tm.get_executions(limit=limit)
        
        return executions
    except Exception as e:
        logger.error(f"Error getting recent executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TEMPLATE ENDPOINTS ====================

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    cloud_provider: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user: Dict = Depends(require_authenticated_user)
):
    """
    List IaC templates
    
    **Cloud Providers**: aws, azure, gcp, digitalocean, kubernetes, multi
    **Categories**: compute, networking, storage, database, security, kubernetes, monitoring
    """
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        templates = await tm.get_templates(
            cloud_provider=cloud_provider,
            category=category
        )
        
        return templates
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Get template by ID"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        template = await tm.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VARIABLE ENDPOINTS ====================

@router.post("/workspaces/{workspace_id}/variables")
async def set_variable(
    workspace_id: str,
    variable: VariableCreate,
    user: Dict = Depends(require_authenticated_user)
):
    """Set workspace variable"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        success = await tm.set_variable(
            workspace_id=workspace_id,
            key=variable.key,
            value=variable.value,
            is_sensitive=variable.is_sensitive,
            description=variable.description
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set variable")
        
        return {"message": "Variable set successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting variable: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/variables")
async def list_variables(
    workspace_id: str,
    include_sensitive: bool = Query(False),
    user: Dict = Depends(require_authenticated_user)
):
    """List workspace variables"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        variables = await tm.get_variables(
            workspace_id=workspace_id,
            include_sensitive=include_sensitive
        )
        
        return variables
    except Exception as e:
        logger.error(f"Error listing variables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DRIFT ENDPOINTS ====================

@router.get("/workspaces/{workspace_id}/drifts")
async def get_drifts(
    workspace_id: str,
    resolved: bool = Query(False),
    user: Dict = Depends(require_authenticated_user)
):
    """Get drift detections for workspace"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        drifts = await tm.get_drifts(
            workspace_id=workspace_id,
            resolved=resolved
        )
        
        return drifts
    except Exception as e:
        logger.error(f"Error getting drifts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/statistics")
async def get_statistics(
    user: Dict = Depends(require_authenticated_user)
):
    """Get Terraform dashboard statistics"""
    try:
        tm = get_terraform_manager()
        if not tm:
            raise HTTPException(status_code=500, detail="Terraform manager not initialized")
        
        stats = await tm.get_statistics()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
