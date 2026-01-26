"""
Database Models for Edge Device Management
Epic 7.1: Edge Device Management

SQLAlchemy ORM models for edge device tables.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class EdgeDevice(Base):
    """Edge Device Registry"""
    __tablename__ = "edge_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)  # 'uc1-pro', 'gateway', 'custom'
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    registration_token = Column(String(255), unique=True, nullable=True)
    device_id = Column(String(255), unique=True, nullable=False)  # Hardware ID
    ip_address = Column(INET, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default='offline', nullable=False)
    firmware_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    configurations = relationship("DeviceConfiguration", back_populates="device", cascade="all, delete-orphan")
    metrics = relationship("DeviceMetric", back_populates="device", cascade="all, delete-orphan")
    logs = relationship("DeviceLog", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EdgeDevice(id={self.id}, name={self.device_name}, status={self.status})>"


class DeviceConfiguration(Base):
    """Device Configuration History"""
    __tablename__ = "device_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey('edge_devices.id', ondelete='CASCADE'), nullable=False)
    config_version = Column(Integer, nullable=False, default=1)
    config_data = Column(JSONB, nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('keycloak_users.id'), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    device = relationship("EdgeDevice", back_populates="configurations")
    
    def __repr__(self):
        return f"<DeviceConfiguration(id={self.id}, device={self.device_id}, version={self.config_version})>"


class DeviceMetric(Base):
    """Device Metrics (Time-Series Data)"""
    __tablename__ = "device_metrics"
    __table_args__ = {'postgresql_partition_by': 'RANGE (timestamp)'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('edge_devices.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, primary_key=True)
    metric_type = Column(String(50), nullable=False)  # 'cpu', 'memory', 'disk', 'network', 'gpu'
    metric_value = Column(JSONB, nullable=False)
    
    # Relationships
    device = relationship("EdgeDevice", back_populates="metrics")
    
    def __repr__(self):
        return f"<DeviceMetric(device={self.device_id}, type={self.metric_type}, time={self.timestamp})>"


class DeviceLog(Base):
    """Device Logs (Time-Series Data)"""
    __tablename__ = "device_logs"
    __table_args__ = {'postgresql_partition_by': 'RANGE (timestamp)'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('edge_devices.id', ondelete='CASCADE'), nullable=False, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, primary_key=True)
    log_level = Column(String(20), nullable=False)  # 'debug', 'info', 'warning', 'error', 'critical'
    service_name = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    device = relationship("EdgeDevice", back_populates="logs")
    
    def __repr__(self):
        return f"<DeviceLog(device={self.device_id}, level={self.log_level}, time={self.timestamp})>"


class OTADeployment(Base):
    """OTA Update Deployments"""
    __tablename__ = "ota_deployments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_name = Column(String(255), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    target_version = Column(String(50), nullable=False)
    rollout_strategy = Column(String(50), default='manual', nullable=False)
    rollout_percentage = Column(Integer, default=100, nullable=False)
    status = Column(String(20), default='pending', nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('keycloak_users.id'), nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    deployment_devices = relationship("OTADeploymentDevice", back_populates="deployment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<OTADeployment(id={self.id}, name={self.deployment_name}, version={self.target_version})>"


class OTADeploymentDevice(Base):
    """OTA Deployment per Device Status"""
    __tablename__ = "ota_deployment_devices"
    
    deployment_id = Column(UUID(as_uuid=True), ForeignKey('ota_deployments.id', ondelete='CASCADE'), primary_key=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('edge_devices.id', ondelete='CASCADE'), primary_key=True)
    status = Column(String(20), default='pending', nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    deployment = relationship("OTADeployment", back_populates="deployment_devices")
    
    def __repr__(self):
        return f"<OTADeploymentDevice(deployment={self.deployment_id}, device={self.device_id}, status={self.status})>"
