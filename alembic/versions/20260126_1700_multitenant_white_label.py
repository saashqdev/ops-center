"""Add white-label configurations and multi-tenant enhancements

Revision ID: 20260126_1700_multitenant_white_label
Revises: 20260126_1100_create_webhook_tables
Create Date: 2026-01-26 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1700_multitenant_white_label'
down_revision = '20260126_1100_create_webhook_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add subdomain and custom_domain columns to organizations table
    op.add_column('organizations', sa.Column('subdomain', sa.String(length=63), nullable=True))
    op.add_column('organizations', sa.Column('custom_domain', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('organizations', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create unique index on subdomain
    op.create_index('idx_organizations_subdomain', 'organizations', ['subdomain'], unique=True)
    op.create_index('idx_organizations_custom_domain', 'organizations', ['custom_domain'], unique=False)
    op.create_index('idx_organizations_is_active', 'organizations', ['is_active'], unique=False)
    
    # Create white_label_configs table
    op.create_table(
        'white_label_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('theme', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Color theme configuration'),
        sa.Column('branding', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Branding assets (logo, company name, etc.)'),
        sa.Column('domain', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Custom domain configuration'),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Feature toggles for white-labeling'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional custom metadata'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.organization_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', name='uq_white_label_org')
    )
    
    # Create indexes
    op.create_index('idx_white_label_org_id', 'white_label_configs', ['organization_id'], unique=False)
    op.create_index('idx_white_label_enabled', 'white_label_configs', ['enabled'], unique=False)
    
    # Create tenant_quotas table for managing resource limits
    op.create_table(
        'tenant_quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False, comment='users, devices, webhooks, etc.'),
        sa.Column('max_allowed', sa.Integer(), nullable=False, comment='-1 for unlimited'),
        sa.Column('current_usage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.organization_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'resource_type', name='uq_tenant_quota_org_resource')
    )
    
    op.create_index('idx_tenant_quota_org_id', 'tenant_quotas', ['organization_id'], unique=False)
    op.create_index('idx_tenant_quota_resource_type', 'tenant_quotas', ['resource_type'], unique=False)
    
    # Create tenant_analytics table for cross-tenant analytics
    op.create_table(
        'tenant_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.String(length=255), nullable=False),
        sa.Column('metric_type', sa.String(length=100), nullable=False, comment='api_calls, storage_used, active_users, etc.'),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.organization_id'], ondelete='CASCADE')
    )
    
    op.create_index('idx_tenant_analytics_org_id', 'tenant_analytics', ['organization_id'], unique=False)
    op.create_index('idx_tenant_analytics_metric_type', 'tenant_analytics', ['metric_type'], unique=False)
    op.create_index('idx_tenant_analytics_timestamp', 'tenant_analytics', ['timestamp'], unique=False)
    op.create_index('idx_tenant_analytics_org_timestamp', 'tenant_analytics', ['organization_id', 'timestamp'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index('idx_tenant_analytics_org_timestamp', table_name='tenant_analytics')
    op.drop_index('idx_tenant_analytics_timestamp', table_name='tenant_analytics')
    op.drop_index('idx_tenant_analytics_metric_type', table_name='tenant_analytics')
    op.drop_index('idx_tenant_analytics_org_id', table_name='tenant_analytics')
    op.drop_table('tenant_analytics')
    
    op.drop_index('idx_tenant_quota_resource_type', table_name='tenant_quotas')
    op.drop_index('idx_tenant_quota_org_id', table_name='tenant_quotas')
    op.drop_table('tenant_quotas')
    
    op.drop_index('idx_white_label_enabled', table_name='white_label_configs')
    op.drop_index('idx_white_label_org_id', table_name='white_label_configs')
    op.drop_table('white_label_configs')
    
    # Drop columns from organizations
    op.drop_index('idx_organizations_is_active', table_name='organizations')
    op.drop_index('idx_organizations_custom_domain', table_name='organizations')
    op.drop_index('idx_organizations_subdomain', table_name='organizations')
    op.drop_column('organizations', 'metadata')
    op.drop_column('organizations', 'is_active')
    op.drop_column('organizations', 'custom_domain')
    op.drop_column('organizations', 'subdomain')
