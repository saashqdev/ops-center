"""Create Claude Agent Flows tables

Revision ID: 20260210_1600
Revises: 20260126_2100
Create Date: 2026-02-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260210_1600'
down_revision = '20260126_2100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agent_flows table
    op.create_table(
        'agent_flows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('org_id', sa.String(255), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('flow_config', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_executed_at', sa.TIMESTAMP, nullable=True),
    )
    
    # Create indexes for agent_flows
    op.create_index('idx_agent_flows_user', 'agent_flows', ['user_id'])
    op.create_index('idx_agent_flows_org', 'agent_flows', ['org_id'])
    op.create_index('idx_agent_flows_status', 'agent_flows', ['status'])
    
    # Create agent_flow_executions table
    op.create_table(
        'agent_flow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('flow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('input_data', postgresql.JSONB, nullable=True),
        sa.Column('output_data', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('tokens_used', postgresql.JSONB, nullable=True),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP, nullable=True),
        sa.ForeignKeyConstraint(['flow_id'], ['agent_flows.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for agent_flow_executions
    op.create_index('idx_executions_flow', 'agent_flow_executions', ['flow_id'])
    op.create_index('idx_executions_user', 'agent_flow_executions', ['user_id'])
    op.create_index('idx_executions_status', 'agent_flow_executions', ['status'])
    
    # Create agent_api_keys table
    op.create_table(
        'agent_api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('org_id', sa.String(255), nullable=True),
        sa.Column('key_name', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('encrypted_api_key', sa.Text, nullable=False),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_used_at', sa.TIMESTAMP, nullable=True),
        sa.UniqueConstraint('user_id', 'key_name', name='uq_user_key_name'),
    )
    
    # Create indexes for agent_api_keys
    op.create_index('idx_agent_api_keys_user', 'agent_api_keys', ['user_id'])
    op.create_index('idx_agent_api_keys_org', 'agent_api_keys', ['org_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('agent_api_keys')
    op.drop_table('agent_flow_executions')
    op.drop_table('agent_flows')
