"""
Edge Device Management Core Module
Epic 7.1: Edge Device Management

Provides device registration, authentication, heartbeat monitoring,
configuration management, and device lifecycle management.
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EdgeDeviceManager:
    """Manages edge device lifecycle and operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Device Registration ====================
    
    async def generate_registration_token(
        self,
        organization_id: UUID,
        device_name: str,
        device_type: str = "uc1-pro",
        expires_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate a one-time registration token for a new device.
        
        Args:
            organization_id: Organization owning the device
            device_name: Friendly name for the device
            device_type: Type of device (uc1-pro, gateway, custom)
            expires_hours: Token expiration in hours
            
        Returns:
            Registration token and metadata
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Create pre-registered device record
        from database import EdgeDevice
        
        device = EdgeDevice(
            device_name=device_name,
            device_type=device_type,
            organization_id=organization_id,
            registration_token=token,
            device_id=f"pending-{uuid4()}",  # Temporary until actual registration
            status="pending",
            metadata={
                "token_expires_at": (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat(),
                "pre_registered": True
            }
        )
        
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        
        logger.info(f"Generated registration token for device: {device_name} (org: {organization_id})")
        
        return {
            "device_id": str(device.id),
            "registration_token": token,
            "expires_at": device.metadata["token_expires_at"],
            "installation_command": self._generate_install_command(token)
        }
    
    def _generate_install_command(self, token: str) -> str:
        """Generate the installation command for edge agents"""
        return f"curl -fsSL https://your-domain.com/install.sh | bash -s {token}"
    
    async def register_device(
        self,
        hardware_id: str,
        registration_token: str,
        firmware_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a device using a registration token.
        
        Args:
            hardware_id: Unique hardware identifier (MAC, UUID, etc.)
            registration_token: Pre-generated registration token
            firmware_version: Current firmware version
            metadata: Additional device metadata
            
        Returns:
            Device credentials and authentication token
        """
        from database import EdgeDevice
        
        # Find device by registration token
        result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.registration_token == registration_token)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=401, detail="Invalid registration token")
        
        # Check if token is expired
        if device.metadata and "token_expires_at" in device.metadata:
            expires_at = datetime.fromisoformat(device.metadata["token_expires_at"])
            if datetime.utcnow() > expires_at:
                raise HTTPException(status_code=401, detail="Registration token expired")
        
        # Update device with actual hardware ID
        device.device_id = hardware_id
        device.firmware_version = firmware_version
        device.status = "online"
        device.last_seen = datetime.utcnow()
        device.registration_token = None  # Clear token after use
        
        if metadata:
            device.metadata = {**(device.metadata or {}), **metadata}
        
        await self.db.commit()
        await self.db.refresh(device)
        
        # Generate JWT authentication token
        auth_token = self._generate_device_token(device.id)
        
        logger.info(f"Device registered successfully: {device.device_name} ({hardware_id})")
        
        return {
            "device_id": str(device.id),
            "device_name": device.device_name,
            "organization_id": str(device.organization_id),
            "auth_token": auth_token,
            "heartbeat_interval": 30,  # seconds
            "config_version": 1
        }
    
    def _generate_device_token(self, device_id: UUID, expires_hours: int = 24) -> str:
        """Generate JWT token for device authentication"""
        # In production, use proper JWT library
        # This is a simplified version
        token_data = f"{device_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(token_data.encode()).hexdigest()
    
    # ==================== Device Heartbeat ====================
    
    async def process_heartbeat(
        self,
        device_id: UUID,
        status: str,
        uptime: Optional[int] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process device heartbeat and update status.
        
        Args:
            device_id: Device UUID
            status: Current status (online, error, maintenance)
            uptime: Device uptime in seconds
            services: List of running services
            metrics: Current device metrics (CPU, memory, etc.)
            ip_address: Device IP address
            
        Returns:
            Response with pending config updates or commands
        """
        from database import EdgeDevice
        
        result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Update device status
        device.status = status
        device.last_seen = datetime.utcnow()
        
        if ip_address:
            device.ip_address = ip_address
        
        if uptime or services:
            device.metadata = device.metadata or {}
            if uptime:
                device.metadata["uptime"] = uptime
            if services:
                device.metadata["services"] = services
        
        # Store metrics if provided
        if metrics:
            await self._store_metrics(device_id, metrics)
        
        await self.db.commit()
        
        # Check for pending configuration updates
        pending_config = await self._get_pending_config(device_id)
        
        response = {
            "ack": True,
            "timestamp": datetime.utcnow().isoformat(),
            "next_heartbeat": 30
        }
        
        if pending_config:
            response["pending_config"] = pending_config
        
        return response
    
    async def _store_metrics(self, device_id: UUID, metrics: Dict[str, Any]):
        """Store device metrics in time-series table"""
        from database import DeviceMetric
        
        timestamp = datetime.utcnow()
        
        # Store each metric type separately
        for metric_type, value in metrics.items():
            metric = DeviceMetric(
                device_id=device_id,
                timestamp=timestamp,
                metric_type=metric_type,
                metric_value=value if isinstance(value, dict) else {"value": value}
            )
            self.db.add(metric)
        
        await self.db.commit()
    
    async def _get_pending_config(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        """Check if there's a pending configuration update for the device"""
        from database import DeviceConfiguration
        
        result = await self.db.execute(
            select(DeviceConfiguration)
            .where(
                and_(
                    DeviceConfiguration.device_id == device_id,
                    DeviceConfiguration.is_active == True,
                    DeviceConfiguration.applied_at.is_(None)
                )
            )
            .order_by(desc(DeviceConfiguration.created_at))
            .limit(1)
        )
        
        config = result.scalar_one_or_none()
        
        if config:
            return {
                "config_id": str(config.id),
                "version": config.config_version,
                "data": config.config_data
            }
        
        return None
    
    # ==================== Device Listing & Queries ====================
    
    async def list_devices(
        self,
        organization_id: Optional[UUID] = None,
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List devices with filtering and pagination.
        
        Args:
            organization_id: Filter by organization
            status: Filter by status
            device_type: Filter by device type
            search: Search in device name
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Paginated list of devices
        """
        from database import EdgeDevice
        
        # Build query with filters
        query = select(EdgeDevice)
        
        filters = []
        if organization_id:
            filters.append(EdgeDevice.organization_id == organization_id)
        if status:
            filters.append(EdgeDevice.status == status)
        if device_type:
            filters.append(EdgeDevice.device_type == device_type)
        if search:
            filters.append(EdgeDevice.device_name.ilike(f"%{search}%"))
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(EdgeDevice)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(EdgeDevice.last_seen)).offset(offset).limit(page_size)
        
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        return {
            "devices": [self._device_to_dict(d) for d in devices],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
    
    async def get_device(self, device_id: UUID) -> Dict[str, Any]:
        """Get detailed device information"""
        from database import EdgeDevice
        
        result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        device_dict = self._device_to_dict(device)
        
        # Add current configuration
        device_dict["current_config"] = await self._get_current_config(device_id)
        
        # Add recent metrics summary
        device_dict["recent_metrics"] = await self._get_recent_metrics(device_id)
        
        return device_dict
    
    async def _get_current_config(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the currently active configuration"""
        from database import DeviceConfiguration
        
        result = await self.db.execute(
            select(DeviceConfiguration)
            .where(
                and_(
                    DeviceConfiguration.device_id == device_id,
                    DeviceConfiguration.is_active == True
                )
            )
            .order_by(desc(DeviceConfiguration.config_version))
            .limit(1)
        )
        
        config = result.scalar_one_or_none()
        
        if config:
            return {
                "version": config.config_version,
                "data": config.config_data,
                "applied_at": config.applied_at.isoformat() if config.applied_at else None,
                "created_at": config.created_at.isoformat()
            }
        
        return None
    
    async def _get_recent_metrics(self, device_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics for the device"""
        from database import DeviceMetric
        
        result = await self.db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device_id)
            .order_by(desc(DeviceMetric.timestamp))
            .limit(limit)
        )
        
        metrics = result.scalars().all()
        
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "type": m.metric_type,
                "value": m.metric_value
            }
            for m in metrics
        ]
    
    def _device_to_dict(self, device) -> Dict[str, Any]:
        """Convert device model to dictionary"""
        return {
            "id": str(device.id),
            "device_name": device.device_name,
            "device_type": device.device_type,
            "organization_id": str(device.organization_id),
            "device_id": device.device_id,
            "ip_address": str(device.ip_address) if device.ip_address else None,
            "status": device.status,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "firmware_version": device.firmware_version,
            "created_at": device.created_at.isoformat(),
            "uptime": device.metadata.get("uptime") if device.metadata else None,
            "services": device.metadata.get("services") if device.metadata else None
        }
    
    # ==================== Device Configuration ====================
    
    async def push_configuration(
        self,
        device_id: UUID,
        config_data: Dict[str, Any],
        created_by: UUID,
        apply_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        Push new configuration to a device.
        
        Args:
            device_id: Target device UUID
            config_data: Configuration data (JSON)
            created_by: User who created the configuration
            apply_immediately: Whether to apply immediately or wait for next heartbeat
            
        Returns:
            Configuration metadata
        """
        from database import DeviceConfiguration, EdgeDevice
        
        # Verify device exists
        device_result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.id == device_id)
        )
        device = device_result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Get current max version
        version_result = await self.db.execute(
            select(func.max(DeviceConfiguration.config_version))
            .where(DeviceConfiguration.device_id == device_id)
        )
        max_version = version_result.scalar() or 0
        
        # Create new configuration
        config = DeviceConfiguration(
            device_id=device_id,
            config_version=max_version + 1,
            config_data=config_data,
            created_by=created_by,
            is_active=True
        )
        
        # Deactivate previous configs
        await self.db.execute(
            f"""
            UPDATE device_configurations 
            SET is_active = false 
            WHERE device_id = '{device_id}' AND is_active = true
            """
        )
        
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        
        logger.info(f"Configuration pushed to device {device_id}: version {config.config_version}")
        
        return {
            "config_id": str(config.id),
            "version": config.config_version,
            "status": "pending" if not apply_immediately else "pending_apply",
            "created_at": config.created_at.isoformat()
        }
    
    async def mark_config_applied(self, device_id: UUID, config_id: UUID):
        """Mark configuration as applied by the device"""
        from database import DeviceConfiguration
        
        result = await self.db.execute(
            select(DeviceConfiguration)
            .where(
                and_(
                    DeviceConfiguration.id == config_id,
                    DeviceConfiguration.device_id == device_id
                )
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            config.applied_at = datetime.utcnow()
            await self.db.commit()
            logger.info(f"Configuration {config_id} marked as applied for device {device_id}")
    
    # ==================== Device Logs ====================
    
    async def add_device_log(
        self,
        device_id: UUID,
        log_level: str,
        message: str,
        service_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store device log entry"""
        from database import DeviceLog
        
        log = DeviceLog(
            device_id=device_id,
            timestamp=datetime.utcnow(),
            log_level=log_level,
            service_name=service_name,
            message=message,
            metadata=metadata
        )
        
        self.db.add(log)
        await self.db.commit()
    
    async def get_device_logs(
        self,
        device_id: UUID,
        log_level: Optional[str] = None,
        service_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve device logs with filtering"""
        from database import DeviceLog
        
        query = select(DeviceLog).where(DeviceLog.device_id == device_id)
        
        if log_level:
            query = query.where(DeviceLog.log_level == log_level)
        if service_name:
            query = query.where(DeviceLog.service_name == service_name)
        
        query = query.order_by(desc(DeviceLog.timestamp)).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.log_level,
                "service": log.service_name,
                "message": log.message,
                "metadata": log.metadata
            }
            for log in logs
        ]
    
    # ==================== Device Management ====================
    
    async def update_device(
        self,
        device_id: UUID,
        device_name: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update device properties"""
        from database import EdgeDevice
        
        result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        if device_name is not None:
            device.device_name = device_name
        if status is not None:
            device.status = status
        if metadata is not None:
            device.metadata = {**(device.metadata or {}), **metadata}
        
        device.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(device)
        
        logger.info(f"Device updated: {device_id}")
        
        return self._device_to_dict(device)
    
    async def delete_device(self, device_id: UUID) -> bool:
        """Delete a device and all associated data"""
        from database import EdgeDevice
        
        result = await self.db.execute(
            select(EdgeDevice).where(EdgeDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        await self.db.delete(device)
        await self.db.commit()
        
        logger.info(f"Device deleted: {device_id}")
        
        return True
    
    # ==================== Health Monitoring ====================
    
    async def get_offline_devices(self, threshold_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get devices that haven't sent heartbeat in threshold_minutes"""
        from database import EdgeDevice
        
        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        
        result = await self.db.execute(
            select(EdgeDevice)
            .where(
                or_(
                    EdgeDevice.last_seen < threshold_time,
                    EdgeDevice.last_seen.is_(None)
                )
            )
            .where(EdgeDevice.status != "offline")
        )
        
        devices = result.scalars().all()
        
        return [self._device_to_dict(d) for d in devices]
    
    async def get_device_statistics(self, organization_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get device statistics and health summary"""
        from database import EdgeDevice
        
        query = select(
            EdgeDevice.status,
            func.count(EdgeDevice.id).label("count")
        )
        
        if organization_id:
            query = query.where(EdgeDevice.organization_id == organization_id)
        
        query = query.group_by(EdgeDevice.status)
        
        result = await self.db.execute(query)
        status_counts = {row[0]: row[1] for row in result.all()}
        
        total_devices = sum(status_counts.values())
        
        return {
            "total_devices": total_devices,
            "online": status_counts.get("online", 0),
            "offline": status_counts.get("offline", 0),
            "error": status_counts.get("error", 0),
            "maintenance": status_counts.get("maintenance", 0),
            "health_percentage": (status_counts.get("online", 0) / total_devices * 100) if total_devices > 0 else 0
        }
