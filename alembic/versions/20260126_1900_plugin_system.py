"""Create plugin system tables

Revision ID: 20260126_1900
Revises: 20260126_1700
Create Date: 2026-01-26 19:00:00.000000

Epic 11: Plugin/Extension Architecture
Creates comprehensive plugin registry system with marketplace support
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1900'
down_revision = '20260126_1700'
branch_labels = None
depends_on = None


def upgrade():
    # Core plugin metadata table
    op.create_table(
        'plugins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('slug', sa.String(100), nullable=False, unique=True, comment='URL-safe identifier'),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('author', sa.String(200), nullable=False),
        sa.Column('author_email', sa.String(255)),
        sa.Column('author_url', sa.String(500)),
        sa.Column('icon_url', sa.String(500)),
        sa.Column('category', sa.String(50), nullable=False, comment='ai, monitoring, integration, analytics, etc.'),
        sa.Column('type', sa.String(50), nullable=False, comment='backend, frontend, hybrid, container, theme'),
        sa.Column('license', sa.String(100), comment='MIT, Apache-2.0, GPL-3.0, Commercial'),
        sa.Column('homepage_url', sa.String(500)),
        sa.Column('repository_url', sa.String(500)),
        sa.Column('documentation_url', sa.String(500)),
        sa.Column('is_official', sa.Boolean, default=False, comment='Official Ops-Center plugin'),
        sa.Column('is_verified', sa.Boolean, default=False, comment='Verified by platform team'),
        sa.Column('is_published', sa.Boolean, default=False, comment='Published to marketplace'),
        sa.Column('min_platform_version', sa.String(20), comment='Minimum Ops-Center version'),
        sa.Column('max_platform_version', sa.String(20), comment='Maximum compatible version'),
        sa.Column('total_installs', sa.Integer, default=0),
        sa.Column('total_downloads', sa.Integer, default=0),
        sa.Column('rating_average', sa.Numeric(3, 2), comment='0.00 to 5.00'),
        sa.Column('rating_count', sa.Integer, default=0),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        
        # Array columns for metadata
        sa.Column('tags', postgresql.ARRAY(sa.Text), comment='Array of tags for search'),
        sa.Column('keywords', postgresql.ARRAY(sa.Text), comment='SEO keywords'),
        sa.Column('screenshots', postgresql.ARRAY(sa.Text), comment='Array of screenshot URLs'),
        
        # Pricing
        sa.Column('is_free', sa.Boolean, default=True),
        sa.Column('price_monthly', sa.Numeric(10, 2)),
        sa.Column('price_yearly', sa.Numeric(10, 2)),
        sa.Column('price_lifetime', sa.Numeric(10, 2)),
        
        # Constraints
        sa.CheckConstraint("slug ~ '^[a-z0-9-]+$'", name='valid_slug'),
        sa.CheckConstraint('rating_average >= 0 AND rating_average <= 5', name='valid_rating')
    )
    
    # Plugin versions table
    op.create_table(
        'plugin_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False, comment='Semantic version: 1.2.3'),
        sa.Column('changelog', sa.Text),
        sa.Column('download_url', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger, comment='File size in bytes'),
        sa.Column('checksum', sa.String(64), comment='SHA-256 hash'),
        sa.Column('is_stable', sa.Boolean, default=True),
        sa.Column('is_deprecated', sa.Boolean, default=False),
        
        # Compatibility
        sa.Column('min_platform_version', sa.String(20)),
        sa.Column('max_platform_version', sa.String(20)),
        sa.Column('python_version', sa.String(20), comment='e.g., ">=3.9,<4.0"'),
        sa.Column('node_version', sa.String(20)),
        
        # Requirements (JSONB for flexible storage)
        sa.Column('python_dependencies', postgresql.JSONB, comment='{"requests": ">=2.28.0", "pydantic": "^2.0"}'),
        sa.Column('npm_dependencies', postgresql.JSONB),
        sa.Column('docker_image', sa.String(500)),
        
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('downloads', sa.Integer, default=0),
        
        sa.UniqueConstraint('plugin_id', 'version', name='unique_plugin_version')
    )
    
    # Plugin installations per tenant
    op.create_table(
        'plugin_installations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugin_versions.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('status', sa.String(50), nullable=False, default='installed', comment='installed, enabled, disabled, error, updating'),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('auto_update', sa.Boolean, default=True),
        
        # Configuration
        sa.Column('config', postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), comment='Plugin configuration'),
        sa.Column('permissions', postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), comment='Granted permissions'),
        
        # Lifecycle tracking
        sa.Column('installed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('installed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_enabled_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_disabled_at', sa.TIMESTAMP(timezone=True)),
        
        # Health monitoring
        sa.Column('error_message', sa.Text),
        sa.Column('last_health_check', sa.TIMESTAMP(timezone=True)),
        sa.Column('health_status', sa.String(50), comment='healthy, degraded, unhealthy'),
        
        sa.UniqueConstraint('tenant_id', 'plugin_id', name='unique_tenant_plugin')
    )
    
    # Plugin dependencies
    op.create_table(
        'plugin_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('depends_on_plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_constraint', sa.String(100), comment='e.g., ">=1.0.0,<2.0.0"'),
        sa.Column('is_optional', sa.Boolean, default=False),
        
        sa.UniqueConstraint('plugin_id', 'depends_on_plugin_id', name='unique_plugin_dependency')
    )
    
    # Plugin permissions
    op.create_table(
        'plugin_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_type', sa.String(100), nullable=False, comment='api:read, api:write, storage:read, etc.'),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('is_required', sa.Boolean, default=True),
        
        sa.UniqueConstraint('plugin_id', 'permission_type', name='unique_plugin_permission')
    )
    
    # Plugin hooks (event registration)
    op.create_table(
        'plugin_hooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hook_name', sa.String(200), nullable=False, comment='e.g., "device.created", "user.login"'),
        sa.Column('handler_function', sa.String(200), nullable=False, comment='Python function path'),
        sa.Column('priority', sa.Integer, default=10, comment='Lower priority runs first'),
        sa.Column('is_active', sa.Boolean, default=True),
        
        sa.UniqueConstraint('plugin_id', 'hook_name', 'handler_function', name='unique_plugin_hook')
    )
    
    # Plugin reviews
    op.create_table(
        'plugin_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE')),
        
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('title', sa.String(200)),
        sa.Column('review_text', sa.Text),
        
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='valid_review_rating'),
        sa.UniqueConstraint('plugin_id', 'user_id', name='unique_plugin_review')
    )
    
    # Plugin analytics
    op.create_table(
        'plugin_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='SET NULL')),
        sa.Column('event_type', sa.String(100), nullable=False, comment='download, install, uninstall, enable, disable, error'),
        sa.Column('event_data', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text)
    )
    
    # Create indexes for performance
    op.create_index('idx_plugins_slug', 'plugins', ['slug'])
    op.create_index('idx_plugins_category', 'plugins', ['category'])
    op.create_index('idx_plugins_type', 'plugins', ['type'])
    op.create_index('idx_plugins_published', 'plugins', ['is_published', 'is_official', 'is_verified'])
    op.create_index('idx_plugins_rating', 'plugins', [sa.text('rating_average DESC'), sa.text('rating_count DESC')])
    
    op.create_index('idx_plugin_versions_plugin_id', 'plugin_versions', ['plugin_id', 'version'])
    
    op.create_index('idx_plugin_installations_tenant', 'plugin_installations', ['tenant_id', 'enabled'])
    op.create_index('idx_plugin_installations_status', 'plugin_installations', ['status', 'health_status'])
    
    op.create_index('idx_plugin_analytics_plugin', 'plugin_analytics', ['plugin_id', sa.text('timestamp DESC')])
    op.create_index('idx_plugin_analytics_tenant', 'plugin_analytics', ['tenant_id', 'event_type', sa.text('timestamp DESC')])
    
    # Full-text search index for plugins
    op.execute("""
        CREATE INDEX idx_plugins_search ON plugins 
        USING gin(to_tsvector('english', 
            name || ' ' || 
            COALESCE(description, '') || ' ' || 
            COALESCE(array_to_string(tags, ' '), '')
        ))
    """)
    
    print("✅ Epic 11: Plugin system tables created successfully")


def downgrade():
    # Drop indexes
    op.drop_index('idx_plugins_search', table_name='plugins')
    op.drop_index('idx_plugin_analytics_tenant', table_name='plugin_analytics')
    op.drop_index('idx_plugin_analytics_plugin', table_name='plugin_analytics')
    op.drop_index('idx_plugin_installations_status', table_name='plugin_installations')
    op.drop_index('idx_plugin_installations_tenant', table_name='plugin_installations')
    op.drop_index('idx_plugin_versions_plugin_id', table_name='plugin_versions')
    op.drop_index('idx_plugins_rating', table_name='plugins')
    op.drop_index('idx_plugins_published', table_name='plugins')
    op.drop_index('idx_plugins_type', table_name='plugins')
    op.drop_index('idx_plugins_category', table_name='plugins')
    op.drop_index('idx_plugins_slug', table_name='plugins')
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('plugin_analytics')
    op.drop_table('plugin_reviews')
    op.drop_table('plugin_hooks')
    op.drop_table('plugin_permissions')
    op.drop_table('plugin_dependencies')
    op.drop_table('plugin_installations')
    op.drop_table('plugin_versions')
    op.drop_table('plugins')
    
    print("✅ Epic 11: Plugin system tables removed")
