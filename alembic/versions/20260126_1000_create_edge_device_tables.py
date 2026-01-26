"""Create edge device management tables

Revision ID: 20260126_1000
Revises: 20251101_extensions
Create Date: 2026-01-26 10:00:00.000000

Epic 7.1: Edge Device Management
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1000'
down_revision = '20251101_extensions'
branch_labels = None
depends_on = None


def upgrade():
    # Edge Devices Registry
    op.create_table('edge_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=False, comment='uc1-pro, gateway, custom'),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('registration_token', sa.String(length=255), nullable=True),
        sa.Column('device_id', sa.String(length=255), nullable=False, comment='Hardware ID'),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='offline', nullable=False, comment='online, offline, maintenance, error'),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registration_token'),
        sa.UniqueConstraint('device_id'),
        sa.UniqueConstraint('organization_id', 'device_name', name='uq_org_device_name')
    )
    op.create_index('idx_edge_devices_org', 'edge_devices', ['organization_id'])
    op.create_index('idx_edge_devices_status', 'edge_devices', ['status'])
    op.create_index('idx_edge_devices_last_seen', 'edge_devices', [sa.text('last_seen DESC')])

    # Device Configuration
    op.create_table('device_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('config_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['edge_devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['keycloak_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_device_config_device', 'device_configurations', ['device_id', sa.text('config_version DESC')])

    # Device Metrics (Time-Series Data) - Partitioned table
    op.execute("""
        CREATE TABLE device_metrics (
            id BIGSERIAL,
            device_id UUID NOT NULL REFERENCES edge_devices(id) ON DELETE CASCADE,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            metric_type VARCHAR(50) NOT NULL,
            metric_value JSONB NOT NULL,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)
    
    op.execute("""
        CREATE INDEX idx_device_metrics_device_time ON device_metrics(device_id, timestamp DESC);
    """)

    # Create monthly partitions for 2026
    months = [
        ('2026_01', '2026-01-01', '2026-02-01'),
        ('2026_02', '2026-02-01', '2026-03-01'),
        ('2026_03', '2026-03-01', '2026-04-01'),
        ('2026_04', '2026-04-01', '2026-05-01'),
        ('2026_05', '2026-05-01', '2026-06-01'),
        ('2026_06', '2026-06-01', '2026-07-01'),
        ('2026_07', '2026-07-01', '2026-08-01'),
        ('2026_08', '2026-08-01', '2026-09-01'),
        ('2026_09', '2026-09-01', '2026-10-01'),
        ('2026_10', '2026-10-01', '2026-11-01'),
        ('2026_11', '2026-11-01', '2026-12-01'),
        ('2026_12', '2026-12-01', '2027-01-01'),
    ]
    
    for month_name, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE device_metrics_{month_name} PARTITION OF device_metrics
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)

    # Device Logs (Time-Series Data) - Partitioned table
    op.execute("""
        CREATE TABLE device_logs (
            id BIGSERIAL,
            device_id UUID NOT NULL REFERENCES edge_devices(id) ON DELETE CASCADE,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            log_level VARCHAR(20) NOT NULL,
            service_name VARCHAR(100),
            message TEXT NOT NULL,
            metadata JSONB,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)
    
    op.execute("""
        CREATE INDEX idx_device_logs_device_time ON device_logs(device_id, timestamp DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_device_logs_level ON device_logs(log_level);
    """)

    # Create monthly partitions for device logs
    for month_name, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE device_logs_{month_name} PARTITION OF device_logs
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)

    # OTA Update Deployments
    op.create_table('ota_deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deployment_name', sa.String(length=255), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_version', sa.String(length=50), nullable=False),
        sa.Column('rollout_strategy', sa.String(length=50), server_default='manual', nullable=False, comment='manual, canary, rolling, immediate'),
        sa.Column('rollout_percentage', sa.Integer(), server_default='100', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False, comment='pending, in_progress, completed, failed, paused'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['keycloak_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # OTA Deployment Devices (tracking per-device deployment status)
    op.create_table('ota_deployment_devices',
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False, comment='pending, downloading, installing, completed, failed, skipped'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['ota_deployments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['edge_devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('deployment_id', 'device_id')
    )
    op.create_index('idx_ota_deployment_devices', 'ota_deployment_devices', ['deployment_id', 'status'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_ota_deployment_devices', table_name='ota_deployment_devices')
    op.drop_table('ota_deployment_devices')
    op.drop_table('ota_deployments')
    
    # Drop device logs partitions and table
    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    for month in months:
        op.execute(f"DROP TABLE IF EXISTS device_logs_2026_{month}")
    op.execute("DROP TABLE IF EXISTS device_logs")
    
    # Drop device metrics partitions and table
    for month in months:
        op.execute(f"DROP TABLE IF EXISTS device_metrics_2026_{month}")
    op.execute("DROP TABLE IF EXISTS device_metrics")
    
    op.drop_index('idx_device_config_device', table_name='device_configurations')
    op.drop_table('device_configurations')
    
    op.drop_index('idx_edge_devices_last_seen', table_name='edge_devices')
    op.drop_index('idx_edge_devices_status', table_name='edge_devices')
    op.drop_index('idx_edge_devices_org', table_name='edge_devices')
    op.drop_table('edge_devices')
