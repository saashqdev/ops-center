"""
Edge Device Management API Endpoints
Epic 7.1: Edge Device Management

REST API for device registration, heartbeat, configuration, monitoring, and OTA updates.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from auth_dependencies import require_authenticated_user, require_admin_user
from database import get_db_connection

logger = logging.getLogger(__name__)

# Create routers
device_router = APIRouter(prefix="/api/v1/edge/devices", tags=["Edge Devices"])
admin_router = APIRouter(prefix="/api/v1/admin/edge", tags=["Admin - Edge Management"])


# ==================== Pydantic Models ====================

class DeviceRegistrationRequest(BaseModel):
    """Device registration request"""
    hardware_id: str = Field(..., description="Unique hardware identifier")
    registration_token: str = Field(..., description="Pre-generated registration token")
    firmware_version: Optional[str] = Field(None, description="Current firmware version")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional device metadata")


class DeviceHeartbeatRequest(BaseModel):
    """Device heartbeat request"""
    status: str = Field(..., description="Device status: online, error, maintenance")
    uptime: Optional[int] = Field(None, description="Device uptime in seconds")
    services: Optional[List[Dict[str, Any]]] = Field(None, description="Running services status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Current metrics")
    ip_address: Optional[str] = Field(None, description="Device IP address")


class GenerateTokenRequest(BaseModel):
    """Request to generate a registration token"""
    device_name: str = Field(..., description="Friendly name for the device")
    device_type: str = Field("uc1-pro", description="Device type")
    organization_id: UUID = Field(..., description="Organization owning the device")
    expires_hours: int = Field(24, description="Token expiration in hours")


class PushConfigRequest(BaseModel):
    """Request to push configuration to device"""
    config_data: Dict[str, Any] = Field(..., description="Configuration data")
    apply_immediately: bool = Field(True, description="Apply immediately vs wait for heartbeat")


class UpdateDeviceRequest(BaseModel):
    """Request to update device properties"""
    device_name: Optional[str] = Field(None, description="New device name")
    status: Optional[str] = Field(None, description="New status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DeviceLogRequest(BaseModel):
    """Device log entry"""
    log_level: str = Field(..., description="Log level: debug, info, warning, error, critical")
    message: str = Field(..., description="Log message")
    service_name: Optional[str] = Field(None, description="Service name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional log metadata")


class MetricsRequest(BaseModel):
    """Batch metrics submission"""
    metrics: List[Dict[str, Any]] = Field(..., description="List of metric entries")


class ConfigAppliedRequest(BaseModel):
    """Notification that config was applied"""
    config_id: UUID = Field(..., description="Configuration ID that was applied")
    success: bool = Field(..., description="Whether application was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# ==================== Device Endpoints (Device → Cloud) ====================

@device_router.post("/register")
async def register_device(request: DeviceRegistrationRequest):
    """
    Register a new edge device using a registration token.
    
    This endpoint is called by the edge agent during initial setup.
    """
    try:
        from edge_device_manager import EdgeDeviceManager
        
        conn = await get_db_connection()
        try:
            # Create manager (note: we'll need to adapt this for asyncpg)
            # For now, we'll use raw SQL
            
            # Find device by registration token
            device_record = await conn.fetchrow(
                """
                SELECT id, device_name, organization_id, metadata 
                FROM edge_devices 
                WHERE registration_token = $1
                """,
                request.registration_token
            )
            
            if not device_record:
                raise HTTPException(status_code=401, detail="Invalid registration token")
            
            # Check token expiration
            if device_record['metadata'] and 'token_expires_at' in device_record['metadata']:
                expires_at = datetime.fromisoformat(device_record['metadata']['token_expires_at'])
                if datetime.utcnow() > expires_at:
                    raise HTTPException(status_code=401, detail="Registration token expired")
            
            # Update device with hardware ID
            await conn.execute(
                """
                UPDATE edge_devices 
                SET device_id = $1, 
                    firmware_version = $2, 
                    status = 'online',
                    last_seen = NOW(),
                    registration_token = NULL,
                    metadata = $3
                WHERE id = $4
                """,
                request.hardware_id,
                request.firmware_version,
                request.metadata or {},
                device_record['id']
            )
            
            # Generate auth token (simplified - use JWT in production)
            import secrets
            auth_token = secrets.token_urlsafe(32)
            
            logger.info(f"Device registered: {device_record['device_name']} ({request.hardware_id})")
            
            return {
                "device_id": str(device_record['id']),
                "device_name": device_record['device_name'],
                "organization_id": str(device_record['organization_id']),
                "auth_token": auth_token,
                "heartbeat_interval": 30,
                "config_version": 1
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/heartbeat")
async def device_heartbeat(device_id: UUID, request: DeviceHeartbeatRequest):
    """
    Process device heartbeat and update status.
    
    Devices should send heartbeats every 30 seconds.
    Response may include pending configuration updates.
    """
    try:
        conn = await get_db_connection()
        try:
            # Update device status
            await conn.execute(
                """
                UPDATE edge_devices 
                SET status = $1, 
                    last_seen = NOW(),
                    ip_address = $2,
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{uptime}',
                        $3::text::jsonb
                    )
                WHERE id = $4
                """,
                request.status,
                request.ip_address,
                request.uptime or 0,
                device_id
            )
            
            # Store metrics if provided
            if request.metrics:
                for metric_type, value in request.metrics.items():
                    await conn.execute(
                        """
                        INSERT INTO device_metrics (device_id, metric_type, metric_value, timestamp)
                        VALUES ($1, $2, $3, NOW())
                        """,
                        device_id,
                        metric_type,
                        value if isinstance(value, dict) else {"value": value}
                    )
            
            # Check for pending config
            pending_config = await conn.fetchrow(
                """
                SELECT id, config_version, config_data
                FROM device_configurations
                WHERE device_id = $1 
                  AND is_active = true 
                  AND applied_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                device_id
            )
            
            response = {
                "ack": True,
                "timestamp": datetime.utcnow().isoformat(),
                "next_heartbeat": 30
            }
            
            if pending_config:
                response["pending_config"] = {
                    "config_id": str(pending_config['id']),
                    "version": pending_config['config_version'],
                    "data": pending_config['config_data']
                }
            
            return response
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Heartbeat processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@device_router.get("/{device_id}/config")
async def get_device_config(device_id: UUID):
    """Get current active configuration for device"""
    try:
        conn = await get_db_connection()
        try:
            config = await conn.fetchrow(
                """
                SELECT config_version, config_data, applied_at
                FROM device_configurations
                WHERE device_id = $1 AND is_active = true
                ORDER BY config_version DESC
                LIMIT 1
                """,
                device_id
            )
            
            if not config:
                return {"version": 0, "data": {}}
            
            return {
                "version": config['config_version'],
                "data": config['config_data'],
                "applied_at": config['applied_at'].isoformat() if config['applied_at'] else None
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to get device config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/config/applied")
async def mark_config_applied(device_id: UUID, request: ConfigAppliedRequest):
    """Device notifies that configuration was applied"""
    try:
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                UPDATE device_configurations
                SET applied_at = NOW()
                WHERE id = $1 AND device_id = $2
                """,
                request.config_id,
                device_id
            )
            
            logger.info(f"Config {request.config_id} applied on device {device_id}")
            
            return {"status": "acknowledged"}
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to mark config applied: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/logs")
async def submit_device_logs(device_id: UUID, request: DeviceLogRequest):
    """Device submits log entries"""
    try:
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT INTO device_logs (device_id, log_level, service_name, message, metadata, timestamp)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                device_id,
                request.log_level,
                request.service_name,
                request.message,
                request.metadata or {}
            )
            
            return {"status": "logged"}
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to store device logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/metrics")
async def submit_metrics(device_id: UUID, request: MetricsRequest):
    """Device submits batch metrics"""
    try:
        conn = await get_db_connection()
        try:
            for metric in request.metrics:
                await conn.execute(
                    """
                    INSERT INTO device_metrics (device_id, metric_type, metric_value, timestamp)
                    VALUES ($1, $2, $3, $4)
                    """,
                    device_id,
                    metric.get('metric_type', 'unknown'),
                    metric.get('value', {}),
                    metric.get('timestamp', datetime.utcnow())
                )
            
            return {"status": "stored", "count": len(request.metrics)}
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to store metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin Endpoints ====================

@admin_router.post("/devices/generate-token")
async def generate_registration_token(
    request: GenerateTokenRequest,
    current_user: dict = Depends(require_admin_user)
):
    """
    Generate a registration token for a new device.
    
    Admin endpoint to create pre-registered devices with tokens.
    """
    try:
        conn = await get_db_connection()
        try:
            import secrets
            
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Calculate expiration
            from datetime import timedelta
            expires_at = datetime.utcnow() + timedelta(hours=request.expires_hours)
            
            # Create pre-registered device
            device_id = await conn.fetchval(
                """
                INSERT INTO edge_devices (
                    device_name, device_type, organization_id, 
                    registration_token, device_id, status, metadata
                )
                VALUES ($1, $2, $3, $4, $5, 'pending', $6)
                RETURNING id
                """,
                request.device_name,
                request.device_type,
                request.organization_id,
                token,
                f"pending-{secrets.token_hex(8)}",
                {
                    "token_expires_at": expires_at.isoformat(),
                    "pre_registered": True
                }
            )
            
            logger.info(f"Registration token generated for {request.device_name} by user {current_user.get('sub')}")
            
            return {
                "device_id": str(device_id),
                "registration_token": token,
                "expires_at": expires_at.isoformat(),
                "installation_command": f"curl -fsSL https://your-domain.com/install.sh | bash -s {token}"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/devices")
async def list_devices(
    organization_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin_user)
):
    """List devices with filtering and pagination"""
    try:
        conn = await get_db_connection()
        try:
            # Build query filters
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
            
            if device_type:
                filters.append(f"device_type = ${param_idx}")
                params.append(device_type)
                param_idx += 1
            
            if search:
                filters.append(f"device_name ILIKE ${param_idx}")
                params.append(f"%{search}%")
                param_idx += 1
            
            where_clause = " AND ".join(filters) if filters else "TRUE"
            
            # Get total count
            total_count = await conn.fetchval(
                f"SELECT COUNT(*) FROM edge_devices WHERE {where_clause}",
                *params
            )
            
            # Get paginated results
            offset = (page - 1) * page_size
            devices = await conn.fetch(
                f"""
                SELECT id, device_name, device_type, organization_id, device_id,
                       ip_address, status, last_seen, firmware_version, created_at,
                       metadata
                FROM edge_devices
                WHERE {where_clause}
                ORDER BY last_seen DESC NULLS LAST
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params, page_size, offset
            )
            
            return {
                "devices": [
                    {
                        "id": str(d['id']),
                        "device_name": d['device_name'],
                        "device_type": d['device_type'],
                        "organization_id": str(d['organization_id']),
                        "device_id": d['device_id'],
                        "ip_address": str(d['ip_address']) if d['ip_address'] else None,
                        "status": d['status'],
                        "last_seen": d['last_seen'].isoformat() if d['last_seen'] else None,
                        "firmware_version": d['firmware_version'],
                        "created_at": d['created_at'].isoformat(),
                        "uptime": d['metadata'].get('uptime') if d['metadata'] else None
                    }
                    for d in devices
                ],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/devices/{device_id}")
async def get_device_detail(
    device_id: UUID,
    current_user: dict = Depends(require_admin_user)
):
    """Get detailed device information"""
    try:
        conn = await get_db_connection()
        try:
            device = await conn.fetchrow(
                """
                SELECT id, device_name, device_type, organization_id, device_id,
                       ip_address, status, last_seen, firmware_version, created_at,
                       updated_at, metadata
                FROM edge_devices
                WHERE id = $1
                """,
                device_id
            )
            
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
            
            # Get current config
            current_config = await conn.fetchrow(
                """
                SELECT config_version, config_data, applied_at, created_at
                FROM device_configurations
                WHERE device_id = $1 AND is_active = true
                ORDER BY config_version DESC
                LIMIT 1
                """,
                device_id
            )
            
            # Get recent metrics
            recent_metrics = await conn.fetch(
                """
                SELECT timestamp, metric_type, metric_value
                FROM device_metrics
                WHERE device_id = $1
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                device_id
            )
            
            return {
                "id": str(device['id']),
                "device_name": device['device_name'],
                "device_type": device['device_type'],
                "organization_id": str(device['organization_id']),
                "device_id": device['device_id'],
                "ip_address": str(device['ip_address']) if device['ip_address'] else None,
                "status": device['status'],
                "last_seen": device['last_seen'].isoformat() if device['last_seen'] else None,
                "firmware_version": device['firmware_version'],
                "created_at": device['created_at'].isoformat(),
                "updated_at": device['updated_at'].isoformat(),
                "metadata": device['metadata'],
                "current_config": {
                    "version": current_config['config_version'],
                    "data": current_config['config_data'],
                    "applied_at": current_config['applied_at'].isoformat() if current_config['applied_at'] else None
                } if current_config else None,
                "recent_metrics": [
                    {
                        "timestamp": m['timestamp'].isoformat(),
                        "type": m['metric_type'],
                        "value": m['metric_value']
                    }
                    for m in recent_metrics
                ]
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/devices/{device_id}/config")
async def push_device_config(
    device_id: UUID,
    request: PushConfigRequest,
    current_user: dict = Depends(require_admin_user)
):
    """Push new configuration to a device"""
    try:
        conn = await get_db_connection()
        try:
            # Get current max version
            max_version = await conn.fetchval(
                "SELECT COALESCE(MAX(config_version), 0) FROM device_configurations WHERE device_id = $1",
                device_id
            ) or 0
            
            # Deactivate previous configs
            await conn.execute(
                "UPDATE device_configurations SET is_active = false WHERE device_id = $1",
                device_id
            )
            
            # Create new config
            config_id = await conn.fetchval(
                """
                INSERT INTO device_configurations (
                    device_id, config_version, config_data, created_by, is_active
                )
                VALUES ($1, $2, $3, $4, true)
                RETURNING id
                """,
                device_id,
                max_version + 1,
                request.config_data,
                UUID(current_user.get('sub'))
            )
            
            logger.info(f"Configuration v{max_version + 1} pushed to device {device_id}")
            
            return {
                "config_id": str(config_id),
                "version": max_version + 1,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to push config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.put("/devices/{device_id}")
async def update_device(
    device_id: UUID,
    request: UpdateDeviceRequest,
    current_user: dict = Depends(require_admin_user)
):
    """Update device properties"""
    try:
        conn = await get_db_connection()
        try:
            updates = []
            params = []
            param_idx = 1
            
            if request.device_name is not None:
                updates.append(f"device_name = ${param_idx}")
                params.append(request.device_name)
                param_idx += 1
            
            if request.status is not None:
                updates.append(f"status = ${param_idx}")
                params.append(request.status)
                param_idx += 1
            
            if request.metadata is not None:
                updates.append(f"metadata = metadata || ${param_idx}::jsonb")
                params.append(request.metadata)
                param_idx += 1
            
            if not updates:
                raise HTTPException(status_code=400, detail="No updates provided")
            
            updates.append("updated_at = NOW()")
            params.append(device_id)
            
            await conn.execute(
                f"""
                UPDATE edge_devices
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
                """,
                *params
            )
            
            return {"status": "updated"}
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.delete("/devices/{device_id}")
async def delete_device(
    device_id: UUID,
    current_user: dict = Depends(require_admin_user)
):
    """Delete a device and all associated data"""
    try:
        conn = await get_db_connection()
        try:
            result = await conn.execute(
                "DELETE FROM edge_devices WHERE id = $1",
                device_id
            )
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Device not found")
            
            logger.info(f"Device deleted: {device_id}")
            
            return {"status": "deleted"}
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/devices/{device_id}/logs")
async def get_device_logs(
    device_id: UUID,
    log_level: Optional[str] = Query(None),
    service_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_admin_user)
):
    """Get device logs with filtering"""
    try:
        conn = await get_db_connection()
        try:
            filters = ["device_id = $1"]
            params = [device_id]
            param_idx = 2
            
            if log_level:
                filters.append(f"log_level = ${param_idx}")
                params.append(log_level)
                param_idx += 1
            
            if service_name:
                filters.append(f"service_name = ${param_idx}")
                params.append(service_name)
                param_idx += 1
            
            params.append(limit)
            
            logs = await conn.fetch(
                f"""
                SELECT timestamp, log_level, service_name, message, metadata
                FROM device_logs
                WHERE {' AND '.join(filters)}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
                """,
                *params
            )
            
            return {
                "logs": [
                    {
                        "timestamp": log['timestamp'].isoformat(),
                        "level": log['log_level'],
                        "service": log['service_name'],
                        "message": log['message'],
                        "metadata": log['metadata']
                    }
                    for log in logs
                ]
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/statistics")
async def get_device_statistics(
    organization_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(require_admin_user)
):
    """Get device statistics and health summary"""
    try:
        conn = await get_db_connection()
        try:
            where_clause = "WHERE organization_id = $1" if organization_id else ""
            params = [organization_id] if organization_id else []
            
            stats = await conn.fetch(
                f"""
                SELECT status, COUNT(*) as count
                FROM edge_devices
                {where_clause}
                GROUP BY status
                """,
                *params
            )
            
            status_counts = {row['status']: row['count'] for row in stats}
            total = sum(status_counts.values())
            
            return {
                "total_devices": total,
                "online": status_counts.get('online', 0),
                "offline": status_counts.get('offline', 0),
                "error": status_counts.get('error', 0),
                "maintenance": status_counts.get('maintenance', 0),
                "pending": status_counts.get('pending', 0),
                "health_percentage": (status_counts.get('online', 0) / total * 100) if total > 0 else 0
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
