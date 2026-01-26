"""create fleet management tables

Revision ID: 20260126_1500
Revises: 
Create Date: 2026-01-26 15:00:00

Epic 15: Multi-Server Management - Fleet Dashboard
Creates tables for managing multiple Ops-Center servers from a single control plane.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1500'
down_revision = '20260126_2100'  # Points to smart_alerts migration
branch_labels = None
depends_on = None


def upgrade():
    """Create fleet management tables"""
    
    # =========================================================================
    # MANAGED SERVERS - Core server registry
    # =========================================================================
    op.create_table(
        'managed_servers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('hostname', sa.String(255), nullable=False),
        sa.Column('api_url', sa.String(512), nullable=False),
        sa.Column('api_token_hash', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('environment', sa.String(50), nullable=True),
        
        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('health_status', sa.String(50), nullable=True),
        sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_health_check_at', sa.TIMESTAMP(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        
        # Multi-tenant
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    # Indexes for managed_servers
    op.create_index('idx_managed_servers_org', 'managed_servers', ['organization_id'])
    op.create_index('idx_managed_servers_status', 'managed_servers', ['status'])
    op.create_index('idx_managed_servers_health', 'managed_servers', ['health_status'])
    op.create_index('idx_managed_servers_region', 'managed_servers', ['region'])
    op.create_index('idx_managed_servers_environment', 'managed_servers', ['environment'])
    op.create_index('idx_managed_servers_tags', 'managed_servers', ['tags'], postgresql_using='gin')
    op.create_index('idx_managed_servers_last_seen', 'managed_servers', ['last_seen_at'])
    
    # =========================================================================
    # SERVER GROUPS - Logical organization of servers
    # =========================================================================
    op.create_table(
        'server_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('color', sa.String(7), nullable=True),  # Hex color for UI
        
        # Filter criteria for dynamic groups
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('regions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('environments', postgresql.JSONB, nullable=False, server_default='[]'),
        
        # Multi-tenant
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    op.create_index('idx_server_groups_org', 'server_groups', ['organization_id'])
    op.create_index('idx_server_groups_name', 'server_groups', ['name'])
    
    # =========================================================================
    # SERVER GROUP MEMBERS - Many-to-many relationship
    # =========================================================================
    op.create_table(
        'server_group_members',
        sa.Column('server_id', sa.String(36), sa.ForeignKey('managed_servers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('server_groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('server_id', 'group_id')
    )
    
    op.create_index('idx_server_group_members_server', 'server_group_members', ['server_id'])
    op.create_index('idx_server_group_members_group', 'server_group_members', ['group_id'])
    
    # =========================================================================
    # SERVER METRICS AGGREGATED - Time-series metrics (PARTITIONED)
    # =========================================================================
    # Create parent table
    op.execute("""
        CREATE TABLE server_metrics_aggregated (
            id BIGSERIAL,
            server_id VARCHAR(36) NOT NULL REFERENCES managed_servers(id) ON DELETE CASCADE,
            
            timestamp TIMESTAMPTZ NOT NULL,
            period VARCHAR(20) NOT NULL,
            
            -- Resource metrics
            cpu_percent DECIMAL(5,2),
            memory_percent DECIMAL(5,2),
            disk_percent DECIMAL(5,2),
            network_rx_bytes BIGINT,
            network_tx_bytes BIGINT,
            
            -- Service metrics
            active_services INTEGER,
            failed_services INTEGER,
            total_services INTEGER,
            
            -- LLM metrics
            llm_requests BIGINT,
            llm_cost_usd DECIMAL(10,2),
            
            -- User metrics
            active_users INTEGER,
            total_users INTEGER,
            
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)
    
    # Create indexes on parent table (will be inherited by partitions)
    op.create_index('idx_server_metrics_server_time', 'server_metrics_aggregated', ['server_id', 'timestamp'])
    op.create_index('idx_server_metrics_period', 'server_metrics_aggregated', ['period', 'timestamp'])
    
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
    
    for month_suffix, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE server_metrics_aggregated_{month_suffix} 
            PARTITION OF server_metrics_aggregated
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    # =========================================================================
    # SERVER HEALTH CHECKS - Health check results (PARTITIONED)
    # =========================================================================
    # Create parent table
    op.execute("""
        CREATE TABLE server_health_checks (
            id BIGSERIAL,
            server_id VARCHAR(36) NOT NULL REFERENCES managed_servers(id) ON DELETE CASCADE,
            
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            -- Health status
            status VARCHAR(50),
            response_time_ms INTEGER,
            
            -- Component health
            database_healthy BOOLEAN,
            redis_healthy BOOLEAN,
            services_healthy BOOLEAN,
            
            -- Error details
            error_message TEXT,
            error_details JSONB,
            
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)
    
    # Create indexes
    op.create_index('idx_server_health_server_time', 'server_health_checks', ['server_id', 'timestamp'])
    op.create_index('idx_server_health_status', 'server_health_checks', ['status', 'timestamp'])
    
    # Create monthly partitions for 2026
    for month_suffix, start_date, end_date in months:
        op.execute(f"""
            CREATE TABLE server_health_checks_{month_suffix} 
            PARTITION OF server_health_checks
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    # =========================================================================
    # FLEET OPERATIONS - Audit log for bulk operations
    # =========================================================================
    op.create_table(
        'fleet_operations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('operation_type', sa.String(100), nullable=False),
        
        # Target scope
        sa.Column('server_ids', postgresql.JSONB, nullable=True),
        sa.Column('group_ids', postgresql.JSONB, nullable=True),
        sa.Column('filter_criteria', postgresql.JSONB, nullable=True),
        
        # Operation details
        sa.Column('parameters', postgresql.JSONB, nullable=True),
        sa.Column('initiated_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Status tracking
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('total_servers', sa.Integer, nullable=True),
        sa.Column('completed_servers', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_servers', sa.Integer, nullable=False, server_default='0'),
        
        # Results
        sa.Column('results', postgresql.JSONB, nullable=True),
        sa.Column('error_summary', sa.Text, nullable=True),
        
        # Timestamps
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )
    
    op.create_index('idx_fleet_ops_status', 'fleet_operations', ['status', 'created_at'])
    op.create_index('idx_fleet_ops_initiated_by', 'fleet_operations', ['initiated_by', 'created_at'])
    op.create_index('idx_fleet_ops_type', 'fleet_operations', ['operation_type'])
    
    # =========================================================================
    # VIEWS - Convenient aggregations
    # =========================================================================
    
    # Fleet summary view
    op.execute("""
        CREATE VIEW v_fleet_summary AS
        SELECT 
            organization_id,
            COUNT(*) as total_servers,
            COUNT(*) FILTER (WHERE status = 'active') as active_servers,
            COUNT(*) FILTER (WHERE status = 'inactive') as inactive_servers,
            COUNT(*) FILTER (WHERE status = 'maintenance') as maintenance_servers,
            COUNT(*) FILTER (WHERE health_status = 'healthy') as healthy_servers,
            COUNT(*) FILTER (WHERE health_status = 'degraded') as degraded_servers,
            COUNT(*) FILTER (WHERE health_status = 'critical') as critical_servers,
            COUNT(*) FILTER (WHERE last_seen_at < NOW() - INTERVAL '5 minutes') as unreachable_servers,
            COUNT(DISTINCT region) as regions_count,
            COUNT(DISTINCT environment) as environments_count
        FROM managed_servers
        GROUP BY organization_id;
    """)
    
    # Server health overview
    op.execute("""
        CREATE VIEW v_server_health_overview AS
        SELECT DISTINCT ON (server_id)
            server_id,
            timestamp,
            status,
            response_time_ms,
            database_healthy,
            redis_healthy,
            services_healthy,
            error_message
        FROM server_health_checks
        ORDER BY server_id, timestamp DESC;
    """)
    
    print("✅ Fleet management tables created successfully!")
    print("   - managed_servers (with 8 indexes)")
    print("   - server_groups")
    print("   - server_group_members")
    print("   - server_metrics_aggregated (partitioned, 12 months)")
    print("   - server_health_checks (partitioned, 12 months)")
    print("   - fleet_operations")
    print("   - 2 views (v_fleet_summary, v_server_health_overview)")


def downgrade():
    """Drop fleet management tables"""
    
    # Drop views first
    op.execute("DROP VIEW IF EXISTS v_server_health_overview;")
    op.execute("DROP VIEW IF EXISTS v_fleet_summary;")
    
    # Drop tables (cascading will handle partitions and foreign keys)
    op.drop_table('fleet_operations')
    op.drop_table('server_health_checks')  # Will drop all partitions
    op.drop_table('server_metrics_aggregated')  # Will drop all partitions
    op.drop_table('server_group_members')
    op.drop_table('server_groups')
    op.drop_table('managed_servers')
    
    print("✅ Fleet management tables dropped successfully!")
