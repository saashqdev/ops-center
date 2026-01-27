"""
Advanced RBAC API Endpoints - Epic 17
RESTful API for role and permission management
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from auth_dependencies import require_authenticated_user, require_admin_user
from rbac_manager import get_rbac_manager, RBACManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC"])


def get_current_user_email(user: dict = Depends(require_authenticated_user)) -> str:
    """Extract email from authenticated user"""
    return user.get("email")


def require_admin(user: dict = Depends(require_admin_user)) -> str:
    """Require admin user and return email"""
    return user.get("email")


# ==================== REQUEST MODELS ====================

class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    organization_id: Optional[str] = None


class AssignPermissionRequest(BaseModel):
    permission_name: str = Field(..., pattern=r'^[a-z_]+:[a-z_]+$')


class AssignRoleRequest(BaseModel):
    user_email: str
    organization_id: Optional[str] = None
    expires_in_days: Optional[int] = None


class CheckPermissionRequest(BaseModel):
    user_email: str
    permission_name: str
    organization_id: Optional[str] = None


# ==================== PERMISSION CHECKING ====================

@router.post("/check-permission")
async def check_permission(
    req: CheckPermissionRequest,
    current_user: str = Depends(get_current_user_email)
):
    """
    Check if a user has a specific permission
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Only super_admin can check other users' permissions
    if req.user_email != current_user:
        has_admin = await rbac.has_permission(current_user, "users:read")
        if not has_admin:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    has_perm = await rbac.has_permission(
        req.user_email,
        req.permission_name,
        req.organization_id
    )
    
    return {
        "user_email": req.user_email,
        "permission": req.permission_name,
        "organization_id": req.organization_id,
        "has_permission": has_perm
    }


@router.get("/my-permissions")
async def get_my_permissions(
    organization_id: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get all permissions for the current user
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    permissions = await rbac.get_user_permissions(current_user, organization_id)
    
    return {
        "user_email": current_user,
        "organization_id": organization_id,
        "permissions": permissions,
        "count": len(permissions)
    }


@router.get("/users/{user_email}/permissions")
async def get_user_permissions(
    user_email: str,
    organization_id: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get all permissions for a specific user (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check admin permission
    has_admin = await rbac.has_permission(current_user, "users:read")
    if not has_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    permissions = await rbac.get_user_permissions(user_email, organization_id)
    
    return {
        "user_email": user_email,
        "organization_id": organization_id,
        "permissions": permissions,
        "count": len(permissions)
    }


# ==================== ROLES ====================

@router.get("/roles")
async def list_roles(
    organization_id: Optional[str] = None,
    include_system: bool = True,
    current_user: str = Depends(get_current_user_email)
):
    """
    List all roles
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    roles = await rbac.list_roles(organization_id, include_system)
    
    return {
        "roles": roles,
        "count": len(roles)
    }


@router.get("/roles/{role_id}")
async def get_role(
    role_id: int,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get role details
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    role = await rbac.get_role(role_id)
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role


@router.post("/roles")
async def create_role(
    req: CreateRoleRequest,
    current_user: str = Depends(require_admin)
):
    """
    Create a new custom role (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "settings:write", req.organization_id)
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions to create roles")
    
    role_id = await rbac.create_role(
        name=req.name,
        description=req.description,
        organization_id=req.organization_id,
        created_by=current_user
    )
    
    if not role_id:
        raise HTTPException(status_code=500, detail="Failed to create role")
    
    role = await rbac.get_role(role_id)
    
    return {
        "message": "Role created successfully",
        "role": role
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: str = Depends(require_admin)
):
    """
    Delete a custom role (admin only, cannot delete system roles)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Get role first to check organization
    role = await rbac.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "settings:write", role.get('organization_id'))
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete roles")
    
    success = await rbac.delete_role(role_id, current_user)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete system role or role not found")
    
    return {"message": "Role deleted successfully"}


# ==================== ROLE PERMISSIONS ====================

@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    role_id: int,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get all permissions for a role
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    permissions = await rbac.get_role_permissions(role_id)
    
    return {
        "role_id": role_id,
        "permissions": permissions,
        "count": len(permissions)
    }


@router.post("/roles/{role_id}/permissions")
async def assign_permission_to_role(
    role_id: int,
    req: AssignPermissionRequest,
    current_user: str = Depends(require_admin)
):
    """
    Assign a permission to a role (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Get role to check organization
    role = await rbac.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "settings:write", role.get('organization_id'))
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    success = await rbac.assign_permission_to_role(
        role_id,
        req.permission_name,
        current_user
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Permission not found or already assigned")
    
    return {"message": "Permission assigned successfully"}


@router.delete("/roles/{role_id}/permissions/{permission_name}")
async def revoke_permission_from_role(
    role_id: int,
    permission_name: str,
    current_user: str = Depends(require_admin)
):
    """
    Revoke a permission from a role (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Get role to check organization
    role = await rbac.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "settings:write", role.get('organization_id'))
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    success = await rbac.revoke_permission_from_role(
        role_id,
        permission_name,
        current_user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Permission assignment not found")
    
    return {"message": "Permission revoked successfully"}


# ==================== USER ROLE ASSIGNMENTS ====================

@router.get("/my-roles")
async def get_my_roles(
    organization_id: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get all roles for the current user
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    roles = await rbac.get_user_roles(current_user, organization_id)
    
    return {
        "user_email": current_user,
        "organization_id": organization_id,
        "roles": roles,
        "count": len(roles)
    }


@router.get("/users/{user_email}/roles")
async def get_user_roles(
    user_email: str,
    organization_id: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """
    Get all roles for a specific user (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check admin permission
    has_admin = await rbac.has_permission(current_user, "users:read")
    if not has_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    roles = await rbac.get_user_roles(user_email, organization_id)
    
    return {
        "user_email": user_email,
        "organization_id": organization_id,
        "roles": roles,
        "count": len(roles)
    }


@router.post("/roles/{role_id}/users")
async def assign_role_to_user(
    role_id: int,
    req: AssignRoleRequest,
    current_user: str = Depends(require_admin)
):
    """
    Assign a role to a user (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "users:update", req.organization_id)
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)
    
    success = await rbac.assign_role_to_user(
        user_email=req.user_email,
        role_id=role_id,
        organization_id=req.organization_id,
        assigned_by=current_user,
        expires_at=expires_at
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role")
    
    return {
        "message": "Role assigned successfully",
        "user_email": req.user_email,
        "role_id": role_id,
        "expires_at": expires_at.isoformat() if expires_at else None
    }


@router.delete("/roles/{role_id}/users/{user_email}")
async def revoke_role_from_user(
    role_id: int,
    user_email: str,
    organization_id: Optional[str] = None,
    current_user: str = Depends(require_admin)
):
    """
    Revoke a role from a user (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "users:update", organization_id)
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    success = await rbac.revoke_role_from_user(
        user_email,
        role_id,
        organization_id,
        current_user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    
    return {"message": "Role revoked successfully"}


# ==================== PERMISSIONS CATALOG ====================

@router.get("/permissions")
async def list_permissions(
    resource: Optional[str] = None,
    current_user: str = Depends(get_current_user_email)
):
    """
    List all available permissions
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    permissions = await rbac.list_all_permissions(resource)
    
    # Group by resource
    by_resource = {}
    for perm in permissions:
        res = perm['resource']
        if res not in by_resource:
            by_resource[res] = []
        by_resource[res].append(perm)
    
    return {
        "permissions": permissions,
        "by_resource": by_resource,
        "count": len(permissions)
    }


# ==================== AUDIT LOG ====================

@router.get("/audit-log")
async def get_audit_log(
    event_type: Optional[str] = None,
    actor_email: Optional[str] = None,
    target_user_email: Optional[str] = None,
    limit: int = 100,
    current_user: str = Depends(require_admin)
):
    """
    Get RBAC audit log (admin only)
    """
    rbac = get_rbac_manager()
    if not rbac:
        raise HTTPException(status_code=500, detail="RBAC manager not initialized")
    
    # Check permission
    has_perm = await rbac.has_permission(current_user, "settings:read")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    logs = await rbac.get_audit_log(event_type, actor_email, target_user_email, limit)
    
    return {
        "logs": logs,
        "count": len(logs)
    }
