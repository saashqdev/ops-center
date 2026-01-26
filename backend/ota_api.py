"""
OTA (Over-The-Air) Update API Endpoints
Epic 7.2: OTA Updates for Edge Devices

Provides REST API for managing OTA deployments:
- Create and manage deployments
- Control deployment lifecycle (start, pause, resume, cancel)
- Track deployment progress
- Monitor per-device update status
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from auth_dependencies import require_admin_user
from ota_manager import OTAManager, RolloutStrategy, DeploymentStatus, DeviceUpdateStatus

logger = logging.getLogger(__name__)

# Create routers
ota_admin_router = APIRouter(prefix="/api/v1/admin/ota", tags=["OTA Admin"])
ota_device_router = APIRouter(prefix="/api/v1/ota", tags=["OTA Device"])


# ==================== Request/Response Models ====================

class CreateDeploymentRequest(BaseModel):
    """Request to create OTA deployment"""
    deployment_name: str = Field(..., description="Human-readable deployment name")
    target_version: str = Field(..., description="Target firmware/software version")
    rollout_strategy: RolloutStrategy = Field(default=RolloutStrategy.MANUAL, description="Rollout strategy")
    rollout_percentage: int = Field(default=100, ge=1, le=100, description="Rollout percentage for canary")
    device_filters: Optional[Dict[str, Any]] = Field(default=None, description="Device selection filters")
    update_package_url: Optional[str] = Field(default=None, description="URL to update package")
    checksum: Optional[str] = Field(default=None, description="SHA256 checksum")
    release_notes: Optional[str] = Field(default=None, description="Release notes")


class DeploymentResponse(BaseModel):
    """OTA deployment response"""
    deployment_id: str
    deployment_name: str
    target_version: str
    target_devices: int
    rollout_strategy: str
    status: str
    created_at: str


class DeploymentStatusResponse(BaseModel):
    """Detailed deployment status"""
    deployment_id: str
    deployment_name: str
    target_version: str
    rollout_strategy: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    metadata: Dict[str, Any]
    progress: Dict[str, Any]
    status_breakdown: Dict[str, int]
    devices: List[Dict[str, Any]]


class DeviceUpdateStatusRequest(BaseModel):
    """Device update status update"""
    status: DeviceUpdateStatus = Field(..., description="Update status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class CheckUpdateResponse(BaseModel):
    """Device update check response"""
    update_available: bool
    deployment_id: Optional[str] = None
    target_version: Optional[str] = None
    update_package_url: Optional[str] = None
    checksum: Optional[str] = None
    release_notes: Optional[str] = None


# ==================== Admin Endpoints ====================

@ota_admin_router.post("/deployments", response_model=DeploymentResponse, dependencies=[Depends(require_admin_user)])
async def create_deployment(
    request: CreateDeploymentRequest,
    user: dict = Depends(require_admin_user)
) -> DeploymentResponse:
    """
    Create a new OTA deployment.
    
    Supports multiple rollout strategies:
    - manual: Admin manually selects devices
    - immediate: Deploy to all matching devices at once
    - canary: Deploy to small percentage first, then expand
    - rolling: Gradual rollout in batches
    
    Device filters support:
    - device_type: Filter by device type
    - current_version: Filter by current version (with operator)
    - status: Filter by device status
    """
    try:
        # Get database session
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            deployment = await manager.create_deployment(
                deployment_name=request.deployment_name,
                organization_id=UUID(user['organization_id']),
                target_version=request.target_version,
                created_by=UUID(user['user_id']),
                rollout_strategy=request.rollout_strategy,
                rollout_percentage=request.rollout_percentage,
                device_filters=request.device_filters,
                update_package_url=request.update_package_url,
                checksum=request.checksum,
                release_notes=request.release_notes
            )
            
            return DeploymentResponse(**deployment)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create deployment")


@ota_admin_router.get("/deployments", dependencies=[Depends(require_admin_user)])
async def list_deployments(
    user: dict = Depends(require_admin_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
) -> Dict[str, Any]:
    """
    List OTA deployments for the organization.
    
    Supports filtering by status and pagination.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            result = await manager.list_deployments(
                organization_id=UUID(user['organization_id']),
                status=status,
                page=page,
                page_size=page_size
            )
            
            return result
    
    except Exception as e:
        logger.error(f"Error listing deployments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list deployments")


@ota_admin_router.get("/deployments/{deployment_id}", response_model=DeploymentStatusResponse, dependencies=[Depends(require_admin_user)])
async def get_deployment_status(
    deployment_id: str,
    user: dict = Depends(require_admin_user)
) -> DeploymentStatusResponse:
    """
    Get detailed status of an OTA deployment.
    
    Includes:
    - Overall deployment progress
    - Per-device status
    - Status breakdown
    - Error messages
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            status = await manager.get_deployment_status(UUID(deployment_id))
            
            # Verify organization access
            if str(user['organization_id']) != str(status.get('organization_id', '')):
                deployment_org = await db.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            
            return DeploymentStatusResponse(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get deployment status")


@ota_admin_router.post("/deployments/{deployment_id}/start", dependencies=[Depends(require_admin_user)])
async def start_deployment(
    deployment_id: str,
    user: dict = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    Start an OTA deployment.
    
    Deployment must be in PENDING status.
    Once started, devices will begin receiving updates according to the rollout strategy.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            # Verify organization access
            from database import get_db_connection
            conn = await get_db_connection()
            try:
                deployment_org = await conn.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if not deployment_org or str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            finally:
                await conn.close()
            
            result = await manager.start_deployment(UUID(deployment_id))
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start deployment")


@ota_admin_router.post("/deployments/{deployment_id}/pause", dependencies=[Depends(require_admin_user)])
async def pause_deployment(
    deployment_id: str,
    user: dict = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    Pause an ongoing deployment.
    
    Devices currently updating will complete, but no new updates will start.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            # Verify organization access
            from database import get_db_connection
            conn = await get_db_connection()
            try:
                deployment_org = await conn.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if not deployment_org or str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            finally:
                await conn.close()
            
            result = await manager.pause_deployment(UUID(deployment_id))
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to pause deployment")


@ota_admin_router.post("/deployments/{deployment_id}/resume", dependencies=[Depends(require_admin_user)])
async def resume_deployment(
    deployment_id: str,
    user: dict = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    Resume a paused deployment.
    
    Updates will continue from where they left off.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            # Verify organization access
            from database import get_db_connection
            conn = await get_db_connection()
            try:
                deployment_org = await conn.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if not deployment_org or str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            finally:
                await conn.close()
            
            result = await manager.resume_deployment(UUID(deployment_id))
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resume deployment")


@ota_admin_router.post("/deployments/{deployment_id}/cancel", dependencies=[Depends(require_admin_user)])
async def cancel_deployment(
    deployment_id: str,
    user: dict = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    Cancel a deployment.
    
    All pending updates will be skipped. Devices already updated will not be affected.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            # Verify organization access
            from database import get_db_connection
            conn = await get_db_connection()
            try:
                deployment_org = await conn.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if not deployment_org or str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            finally:
                await conn.close()
            
            result = await manager.cancel_deployment(UUID(deployment_id))
            return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling deployment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel deployment")


@ota_admin_router.post("/deployments/{deployment_id}/devices/{device_id}/rollback", dependencies=[Depends(require_admin_user)])
async def rollback_device_update(
    deployment_id: str,
    device_id: str,
    user: dict = Depends(require_admin_user),
    previous_version: str = Body(..., embed=True, description="Version to rollback to")
) -> Dict[str, str]:
    """
    Rollback a device to a previous version.
    
    Marks the update as rolled back and reverts the device firmware version.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            # Verify organization access
            from database import get_db_connection
            conn = await get_db_connection()
            try:
                deployment_org = await conn.fetchval(
                    "SELECT organization_id FROM ota_deployments WHERE id = $1",
                    UUID(deployment_id)
                )
                if not deployment_org or str(user['organization_id']) != str(deployment_org):
                    raise HTTPException(status_code=403, detail="Access denied")
            finally:
                await conn.close()
            
            success = await manager.rollback_device(
                UUID(deployment_id),
                UUID(device_id),
                previous_version
            )
            
            if success:
                return {"status": "success", "message": f"Device rolled back to {previous_version}"}
            else:
                raise HTTPException(status_code=500, detail="Rollback failed")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back device: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rollback device")


# ==================== Device Endpoints ====================

@ota_device_router.get("/check-update", response_model=CheckUpdateResponse)
async def check_for_update(
    device_id: str = Query(..., description="Device ID from registration token")
) -> CheckUpdateResponse:
    """
    Check if device has pending OTA updates.
    
    Called periodically by edge devices to check for available updates.
    Returns update details if available.
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            update = await manager.check_device_updates(UUID(device_id))
            
            if update:
                return CheckUpdateResponse(
                    update_available=True,
                    **update
                )
            else:
                return CheckUpdateResponse(update_available=False)
    
    except Exception as e:
        logger.error(f"Error checking for updates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check for updates")


@ota_device_router.post("/deployments/{deployment_id}/status")
async def update_deployment_status(
    deployment_id: str,
    request: DeviceUpdateStatusRequest,
    device_id: str = Query(..., description="Device ID")
) -> Dict[str, str]:
    """
    Update device status during OTA update.
    
    Called by edge devices to report update progress:
    - downloading: Started downloading update package
    - installing: Installing update
    - verifying: Verifying installation
    - completed: Update successful
    - failed: Update failed
    """
    try:
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            manager = OTAManager(db)
            
            await manager.update_device_status(
                UUID(deployment_id),
                UUID(device_id),
                request.status,
                request.error_message
            )
            
            return {"status": "success", "message": f"Status updated to {request.status.value}"}
    
    except Exception as e:
        logger.error(f"Error updating device status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status")


# Export routers
__all__ = ['ota_admin_router', 'ota_device_router']
