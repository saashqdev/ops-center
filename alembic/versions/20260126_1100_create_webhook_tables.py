"""Create webhook tables

Revision ID: 20260126_1100_create_webhook_tables
Revises: 20260126_1000_create_edge_device_tables
Create Date: 2026-01-26 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_1100_create_webhook_tables'
down_revision = '20260126_1000_create_edge_device_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('events', postgresql.ARRAY(sa.String(100)), nullable=False),
        sa.Column('secret', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=True),
        sa.Column('last_triggered_at', sa.TIMESTAMP, nullable=True),
        sa.Column('success_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer, nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.Index('idx_webhooks_org_id', 'organization_id'),
        sa.Index('idx_webhooks_enabled', 'enabled'),
    )
    
    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('attempt', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(50), nullable=False),  # pending, success, failed
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('delivered_at', sa.TIMESTAMP, nullable=True),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.Index('idx_webhook_deliveries_webhook_id', 'webhook_id'),
        sa.Index('idx_webhook_deliveries_status', 'status'),
        sa.Index('idx_webhook_deliveries_created_at', 'created_at'),
    )
    
    # Create webhook_events view for analytics
    op.execute("""
        CREATE VIEW webhook_event_stats AS
        SELECT 
            webhook_id,
            event_type,
            status,
            COUNT(*) as count,
            AVG(duration_ms) as avg_duration_ms,
            MAX(created_at) as last_delivery
        FROM webhook_deliveries
        GROUP BY webhook_id, event_type, status
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS webhook_event_stats")
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
