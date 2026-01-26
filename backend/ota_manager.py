"""
OTA (Over-The-Air) Update Manager
Epic 7.2: OTA Updates for Edge Devices

Manages firmware and software updates for edge devices with support for:
- Multiple rollout strategies (canary, rolling, immediate, manual)
- Update verification and automatic rollback
- Deployment progress tracking
- Per-device status monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from enum import Enum

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RolloutStrategy(str, Enum):
    """OTA deployment rollout strategies"""
    MANUAL = "manual"           # Admin manually selects devices
    IMMEDIATE = "immediate"     # All devices at once
    CANARY = "canary"          # Small percentage first, then all
    ROLLING = "rolling"        # Gradual rollout in batches


class DeploymentStatus(str, Enum):
    """OTA deployment status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class DeviceUpdateStatus(str, Enum):
    """Per-device update status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class OTAManager:
    """Manages OTA deployments and updates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Deployment Creation ====================
    
    async def create_deployment(
        self,
        deployment_name: str,
        organization_id: UUID,
        target_version: str,
        created_by: UUID,
        rollout_strategy: RolloutStrategy = RolloutStrategy.MANUAL,
        rollout_percentage: int = 100,
        device_filters: Optional[Dict[str, Any]] = None,
        update_package_url: Optional[str] = None,
        checksum: Optional[str] = None,
        release_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new OTA deployment.
        
        Args:
            deployment_name: Human-readable deployment name
            organization_id: Organization owning the deployment
            target_version: Target firmware/software version
            created_by: User creating the deployment
            rollout_strategy: How to roll out the update
            rollout_percentage: Percentage of devices (for canary)
            device_filters: Filters to select target devices
            update_package_url: URL to download update package
            checksum: SHA256 checksum for verification
            release_notes: Update release notes
            
        Returns:
            Deployment metadata
        """
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Create deployment record
            deployment_id = await conn.fetchval(
                """
                INSERT INTO ota_deployments (
                    deployment_name, organization_id, target_version,
                    rollout_strategy, rollout_percentage, status,
                    created_by, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                deployment_name,
                organization_id,
                target_version,
                rollout_strategy.value,
                rollout_percentage,
                DeploymentStatus.PENDING.value,
                created_by,
                {
                    "device_filters": device_filters or {},
                    "update_package_url": update_package_url,
                    "checksum": checksum,
                    "release_notes": release_notes
                }
            )
            
            # Select target devices based on filters
            target_devices = await self._select_target_devices(
                conn, organization_id, device_filters, rollout_strategy, rollout_percentage
            )
            
            # Create deployment-device records
            for device_id in target_devices:
                await conn.execute(
                    """
                    INSERT INTO ota_deployment_devices (
                        deployment_id, device_id, status
                    )
                    VALUES ($1, $2, $3)
                    """,
                    deployment_id,
                    device_id,
                    DeviceUpdateStatus.PENDING.value
                )
            
            logger.info(
                f"Created OTA deployment {deployment_id}: {deployment_name} "
                f"targeting {len(target_devices)} devices"
            )
            
            return {
                "deployment_id": str(deployment_id),
                "deployment_name": deployment_name,
                "target_version": target_version,
                "target_devices": len(target_devices),
                "rollout_strategy": rollout_strategy.value,
                "status": DeploymentStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat()
            }
            
        finally:
            await conn.close()
    
    async def _select_target_devices(
        self,
        conn,
        organization_id: UUID,
        device_filters: Optional[Dict[str, Any]],
        rollout_strategy: RolloutStrategy,
        rollout_percentage: int
    ) -> List[UUID]:
        """Select devices for deployment based on filters and strategy"""
        
        # Build query filters
        filters = ["organization_id = $1", "status != 'pending'"]
        params = [organization_id]
        param_idx = 2
        
        if device_filters:
            if "device_type" in device_filters:
                filters.append(f"device_type = ${param_idx}")
                params.append(device_filters["device_type"])
                param_idx += 1
            
            if "current_version" in device_filters:
                operator = device_filters.get("version_operator", "!=")
                if operator in ["<", "<=", "!=", "="]:
                    filters.append(f"firmware_version {operator} ${param_idx}")
                    params.append(device_filters["current_version"])
                    param_idx += 1
            
            if "status" in device_filters:
                filters.append(f"status = ${param_idx}")
                params.append(device_filters["status"])
                param_idx += 1
        
        where_clause = " AND ".join(filters)
        
        # Get matching devices
        query = f"""
            SELECT id FROM edge_devices
            WHERE {where_clause}
            ORDER BY created_at ASC
        """
        
        rows = await conn.fetch(query, *params)
        all_devices = [row['id'] for row in rows]
        
        # Apply rollout strategy
        if rollout_strategy == RolloutStrategy.CANARY and rollout_percentage < 100:
            # Select percentage of devices for canary
            canary_count = max(1, int(len(all_devices) * rollout_percentage / 100))
            return all_devices[:canary_count]
        elif rollout_strategy == RolloutStrategy.ROLLING:
            # Start with first batch (20% or min 5 devices)
            batch_size = max(5, int(len(all_devices) * 0.2))
            return all_devices[:batch_size]
        else:
            # Manual or immediate - select all matching devices
            return all_devices
    
    # ==================== Deployment Control ====================
    
    async def start_deployment(self, deployment_id: UUID) -> Dict[str, Any]:
        """Start an OTA deployment"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Update deployment status
            await conn.execute(
                """
                UPDATE ota_deployments
                SET status = $1, started_at = NOW()
                WHERE id = $2 AND status = $3
                """,
                DeploymentStatus.IN_PROGRESS.value,
                deployment_id,
                DeploymentStatus.PENDING.value
            )
            
            logger.info(f"Started OTA deployment {deployment_id}")
            
            return await self.get_deployment_status(deployment_id)
            
        finally:
            await conn.close()
    
    async def pause_deployment(self, deployment_id: UUID) -> Dict[str, Any]:
        """Pause an ongoing deployment"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE ota_deployments
                SET status = $1
                WHERE id = $2 AND status = $3
                """,
                DeploymentStatus.PAUSED.value,
                deployment_id,
                DeploymentStatus.IN_PROGRESS.value
            )
            
            logger.info(f"Paused OTA deployment {deployment_id}")
            
            return await self.get_deployment_status(deployment_id)
            
        finally:
            await conn.close()
    
    async def resume_deployment(self, deployment_id: UUID) -> Dict[str, Any]:
        """Resume a paused deployment"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE ota_deployments
                SET status = $1
                WHERE id = $2 AND status = $3
                """,
                DeploymentStatus.IN_PROGRESS.value,
                deployment_id,
                DeploymentStatus.PAUSED.value
            )
            
            logger.info(f"Resumed OTA deployment {deployment_id}")
            
            return await self.get_deployment_status(deployment_id)
            
        finally:
            await conn.close()
    
    async def cancel_deployment(self, deployment_id: UUID) -> Dict[str, Any]:
        """Cancel a deployment"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Cancel pending device updates
            await conn.execute(
                """
                UPDATE ota_deployment_devices
                SET status = $1
                WHERE deployment_id = $2 AND status = $3
                """,
                DeviceUpdateStatus.SKIPPED.value,
                deployment_id,
                DeviceUpdateStatus.PENDING.value
            )
            
            # Update deployment status
            await conn.execute(
                """
                UPDATE ota_deployments
                SET status = $1, completed_at = NOW()
                WHERE id = $2
                """,
                DeploymentStatus.CANCELLED.value,
                deployment_id
            )
            
            logger.info(f"Cancelled OTA deployment {deployment_id}")
            
            return await self.get_deployment_status(deployment_id)
            
        finally:
            await conn.close()
    
    # ==================== Progress Tracking ====================
    
    async def get_deployment_status(self, deployment_id: UUID) -> Dict[str, Any]:
        """Get detailed deployment status"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Get deployment info
            deployment = await conn.fetchrow(
                """
                SELECT id, deployment_name, organization_id, target_version,
                       rollout_strategy, rollout_percentage, status,
                       started_at, completed_at, created_at, metadata
                FROM ota_deployments
                WHERE id = $1
                """,
                deployment_id
            )
            
            if not deployment:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            # Get device status breakdown
            device_stats = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM ota_deployment_devices
                WHERE deployment_id = $1
                GROUP BY status
                """,
                deployment_id
            )
            
            status_counts = {row['status']: row['count'] for row in device_stats}
            total_devices = sum(status_counts.values())
            
            # Get device details
            devices = await conn.fetch(
                """
                SELECT 
                    dd.device_id,
                    dd.status,
                    dd.started_at,
                    dd.completed_at,
                    dd.error_message,
                    ed.device_name,
                    ed.firmware_version as current_version
                FROM ota_deployment_devices dd
                JOIN edge_devices ed ON dd.device_id = ed.id
                WHERE dd.deployment_id = $1
                ORDER BY dd.started_at DESC NULLS LAST
                """,
                deployment_id
            )
            
            # Calculate progress
            completed = status_counts.get(DeviceUpdateStatus.COMPLETED.value, 0)
            failed = status_counts.get(DeviceUpdateStatus.FAILED.value, 0)
            progress_percentage = (completed / total_devices * 100) if total_devices > 0 else 0
            
            return {
                "deployment_id": str(deployment['id']),
                "deployment_name": deployment['deployment_name'],
                "target_version": deployment['target_version'],
                "rollout_strategy": deployment['rollout_strategy'],
                "status": deployment['status'],
                "started_at": deployment['started_at'].isoformat() if deployment['started_at'] else None,
                "completed_at": deployment['completed_at'].isoformat() if deployment['completed_at'] else None,
                "created_at": deployment['created_at'].isoformat(),
                "metadata": deployment['metadata'],
                "progress": {
                    "total_devices": total_devices,
                    "completed": completed,
                    "failed": failed,
                    "in_progress": status_counts.get(DeviceUpdateStatus.INSTALLING.value, 0) +
                                  status_counts.get(DeviceUpdateStatus.DOWNLOADING.value, 0),
                    "pending": status_counts.get(DeviceUpdateStatus.PENDING.value, 0),
                    "percentage": round(progress_percentage, 1)
                },
                "status_breakdown": status_counts,
                "devices": [
                    {
                        "device_id": str(d['device_id']),
                        "device_name": d['device_name'],
                        "current_version": d['current_version'],
                        "status": d['status'],
                        "started_at": d['started_at'].isoformat() if d['started_at'] else None,
                        "completed_at": d['completed_at'].isoformat() if d['completed_at'] else None,
                        "error_message": d['error_message']
                    }
                    for d in devices
                ]
            }
            
        finally:
            await conn.close()
    
    async def list_deployments(
        self,
        organization_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List OTA deployments"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            filters = []
            params = []
            param_idx = 1
            
            if organization_id:
                filters.append(f"organization_id = ${param_idx}")
                params.append(organization_id)
                param_idx += 1
            
            if status:
                filters.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1
            
            where_clause = " AND ".join(filters) if filters else "TRUE"
            
            # Get total count
            total_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM ota_deployments WHERE {where_clause}",
                *params
            )
            
            # Get paginated results
            offset = (page - 1) * page_size
            deployments = await conn.fetch(
                f"""
                SELECT id, deployment_name, organization_id, target_version,
                       rollout_strategy, status, started_at, completed_at, created_at
                FROM ota_deployments
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params, page_size, offset
            )
            
            # Get device counts for each deployment
            deployment_list = []
            for dep in deployments:
                device_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM ota_deployment_devices WHERE deployment_id = $1",
                    dep['id']
                )
                
                completed_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM ota_deployment_devices 
                    WHERE deployment_id = $1 AND status = $2
                    """,
                    dep['id'],
                    DeviceUpdateStatus.COMPLETED.value
                )
                
                deployment_list.append({
                    "deployment_id": str(dep['id']),
                    "deployment_name": dep['deployment_name'],
                    "target_version": dep['target_version'],
                    "rollout_strategy": dep['rollout_strategy'],
                    "status": dep['status'],
                    "started_at": dep['started_at'].isoformat() if dep['started_at'] else None,
                    "completed_at": dep['completed_at'].isoformat() if dep['completed_at'] else None,
                    "created_at": dep['created_at'].isoformat(),
                    "total_devices": device_count,
                    "completed_devices": completed_count,
                    "progress_percentage": round((completed_count / device_count * 100), 1) if device_count > 0 else 0
                })
            
            return {
                "deployments": deployment_list,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
        finally:
            await conn.close()
    
    # ==================== Device Update Handling ====================
    
    async def check_device_updates(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        """Check if device has pending updates"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Find active deployment for this device
            update = await conn.fetchrow(
                """
                SELECT 
                    dd.deployment_id,
                    dd.status as device_status,
                    dep.target_version,
                    dep.status as deployment_status,
                    dep.metadata
                FROM ota_deployment_devices dd
                JOIN ota_deployments dep ON dd.deployment_id = dep.id
                WHERE dd.device_id = $1
                  AND dd.status = $2
                  AND dep.status = $3
                ORDER BY dep.created_at DESC
                LIMIT 1
                """,
                device_id,
                DeviceUpdateStatus.PENDING.value,
                DeploymentStatus.IN_PROGRESS.value
            )
            
            if not update:
                return None
            
            metadata = update['metadata'] or {}
            
            return {
                "deployment_id": str(update['deployment_id']),
                "target_version": update['target_version'],
                "update_package_url": metadata.get('update_package_url'),
                "checksum": metadata.get('checksum'),
                "release_notes": metadata.get('release_notes')
            }
            
        finally:
            await conn.close()
    
    async def update_device_status(
        self,
        deployment_id: UUID,
        device_id: UUID,
        status: DeviceUpdateStatus,
        error_message: Optional[str] = None
    ):
        """Update device update status"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Update device status
            if status == DeviceUpdateStatus.DOWNLOADING:
                await conn.execute(
                    """
                    UPDATE ota_deployment_devices
                    SET status = $1, started_at = NOW()
                    WHERE deployment_id = $2 AND device_id = $3
                    """,
                    status.value, deployment_id, device_id
                )
            elif status in [DeviceUpdateStatus.COMPLETED, DeviceUpdateStatus.FAILED, DeviceUpdateStatus.ROLLED_BACK]:
                await conn.execute(
                    """
                    UPDATE ota_deployment_devices
                    SET status = $1, completed_at = NOW(), error_message = $2
                    WHERE deployment_id = $3 AND device_id = $4
                    """,
                    status.value, error_message, deployment_id, device_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE ota_deployment_devices
                    SET status = $1, error_message = $2
                    WHERE deployment_id = $3 AND device_id = $4
                    """,
                    status.value, error_message, deployment_id, device_id
                )
            
            # Check if deployment is complete
            await self._check_deployment_completion(conn, deployment_id)
            
            logger.info(f"Device {device_id} update status: {status.value}")
            
        finally:
            await conn.close()
    
    async def _check_deployment_completion(self, conn, deployment_id: UUID):
        """Check if deployment is complete and update status"""
        
        # Count pending/in-progress devices
        pending_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM ota_deployment_devices
            WHERE deployment_id = $1
              AND status IN ($2, $3, $4, $5)
            """,
            deployment_id,
            DeviceUpdateStatus.PENDING.value,
            DeviceUpdateStatus.DOWNLOADING.value,
            DeviceUpdateStatus.INSTALLING.value,
            DeviceUpdateStatus.VERIFYING.value
        )
        
        if pending_count == 0:
            # All devices complete - check if any failed
            failed_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM ota_deployment_devices
                WHERE deployment_id = $1 AND status = $2
                """,
                deployment_id,
                DeviceUpdateStatus.FAILED.value
            )
            
            final_status = DeploymentStatus.FAILED if failed_count > 0 else DeploymentStatus.COMPLETED
            
            await conn.execute(
                """
                UPDATE ota_deployments
                SET status = $1, completed_at = NOW()
                WHERE id = $2
                """,
                final_status.value,
                deployment_id
            )
            
            logger.info(f"Deployment {deployment_id} completed with status: {final_status.value}")
    
    # ==================== Rollback ====================
    
    async def rollback_device(
        self,
        deployment_id: UUID,
        device_id: UUID,
        previous_version: str
    ) -> bool:
        """Rollback a device to previous version"""
        from database import get_db_connection
        
        conn = await get_db_connection()
        try:
            # Mark update as rolled back
            await self.update_device_status(
                deployment_id, device_id, DeviceUpdateStatus.ROLLED_BACK,
                f"Rolled back to version {previous_version}"
            )
            
            # Update device firmware version
            await conn.execute(
                """
                UPDATE edge_devices
                SET firmware_version = $1
                WHERE id = $2
                """,
                previous_version,
                device_id
            )
            
            logger.info(f"Rolled back device {device_id} to version {previous_version}")
            
            return True
            
        finally:
            await conn.close()
