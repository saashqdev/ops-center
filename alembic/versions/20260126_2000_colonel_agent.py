"""Add Colonel Agent tables

Revision ID: 20260126_2000
Revises: 20260126_1900
Create Date: 2026-01-26 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_2000'
down_revision = '20260126_1900'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== colonel_conversations ====================
    op.create_table(
        'colonel_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.Text, nullable=True, comment='Auto-generated from first message'),
        sa.Column('model_provider', sa.String(50), nullable=False, comment='anthropic, openai'),
        sa.Column('model_name', sa.String(100), nullable=False, comment='claude-3-sonnet, gpt-4'),
        sa.Column('system_prompt', sa.Text, nullable=True, comment='Custom system prompt'),
        sa.Column('context_window_tokens', sa.Integer, nullable=False, server_default='100000'),
        sa.Column('total_input_tokens', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('total_output_tokens', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('total_tool_calls', sa.Integer, nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', comment='active, archived, deleted'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_message_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    
    # Indexes for colonel_conversations
    op.create_index('idx_colonel_conversations_user', 'colonel_conversations', ['user_id'])
    op.create_index('idx_colonel_conversations_org', 'colonel_conversations', ['organization_id'])
    op.create_index('idx_colonel_conversations_status', 'colonel_conversations', ['status'])
    op.create_index('idx_colonel_conversations_last_message', 'colonel_conversations', [sa.text('last_message_at DESC')])
    
    # ==================== colonel_messages ====================
    op.create_table(
        'colonel_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colonel_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, comment='user, assistant, system, tool'),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Array of tool calls made by AI'),
        sa.Column('tool_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Results from tool executions'),
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('thinking_time_ms', sa.Integer, nullable=True, comment='Time spent in AI reasoning'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Indexes for colonel_messages
    op.create_index('idx_colonel_messages_conversation', 'colonel_messages', ['conversation_id', 'created_at'])
    op.create_index('idx_colonel_messages_role', 'colonel_messages', ['role'])
    op.create_index('idx_colonel_messages_created', 'colonel_messages', [sa.text('created_at DESC')])
    
    # ==================== colonel_tool_executions ====================
    op.create_table(
        'colonel_tool_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colonel_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colonel_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('tool_input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('tool_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_time_ms', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='success', comment='success, error, timeout'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('requires_approval', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Indexes for colonel_tool_executions
    op.create_index('idx_colonel_tool_executions_message', 'colonel_tool_executions', ['message_id'])
    op.create_index('idx_colonel_tool_executions_conversation', 'colonel_tool_executions', ['conversation_id'])
    op.create_index('idx_colonel_tool_executions_tool', 'colonel_tool_executions', ['tool_name'])
    op.create_index('idx_colonel_tool_executions_status', 'colonel_tool_executions', ['status'])
    op.create_index('idx_colonel_tool_executions_created', 'colonel_tool_executions', [sa.text('created_at DESC')])
    
    # ==================== colonel_audit_log ====================
    op.create_table(
        'colonel_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colonel_conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False, comment='query, tool_execution, approval, error'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Indexes for colonel_audit_log
    op.create_index('idx_colonel_audit_log_conversation', 'colonel_audit_log', ['conversation_id'])
    op.create_index('idx_colonel_audit_log_user', 'colonel_audit_log', ['user_id'])
    op.create_index('idx_colonel_audit_log_org', 'colonel_audit_log', ['organization_id'])
    op.create_index('idx_colonel_audit_log_action', 'colonel_audit_log', ['action'])
    op.create_index('idx_colonel_audit_log_created', 'colonel_audit_log', [sa.text('created_at DESC')])
    
    # ==================== colonel_system_prompts ====================
    op.create_table(
        'colonel_system_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('prompt_template', sa.Text, nullable=False),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]', comment='Template variables'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Indexes for colonel_system_prompts
    op.create_index('idx_colonel_system_prompts_name', 'colonel_system_prompts', ['name'])
    op.create_index('idx_colonel_system_prompts_org', 'colonel_system_prompts', ['organization_id'])
    op.create_index('idx_colonel_system_prompts_public', 'colonel_system_prompts', ['is_public'])
    
    # ==================== Insert Default System Prompt ====================
    op.execute("""
        INSERT INTO colonel_system_prompts (name, description, prompt_template, is_default, is_public, variables)
        VALUES (
            'default',
            'Default system prompt for The Colonel',
            'You are The Colonel, an AI infrastructure assistant for Ops-Center.

Your role is to help users understand, monitor, and troubleshoot their infrastructure through natural conversation. You have access to real-time data via tools that query the Ops-Center system.

## Core Capabilities
- Query device status and metrics
- Analyze alerts and incidents
- Investigate performance issues
- Provide usage statistics
- Search across system resources

## Personality
- Professional but approachable
- Concise yet thorough
- Proactive in suggesting next steps
- Honest about limitations

## Guidelines
1. Always use tools to get real data - never make up information
2. When you don''t know something, say so clearly
3. Provide context with your answers (timestamps, sources)
4. Suggest follow-up questions when relevant
5. Format responses clearly with tables, lists, or code blocks
6. If a query requires multiple steps, explain your reasoning
7. Flag potential issues or anomalies you notice

## Safety Rules
- You have READ-ONLY access - you cannot modify, create, or delete anything
- Respect user permissions - only access resources they''re authorized for
- Never share sensitive data like passwords or API keys
- If asked to do something outside your capabilities, politely decline

## Current Context
- User: {{user_name}} ({{user_email}})
- Organization: {{organization_name}}
- Role: {{user_role}}
- Current Time: {{current_time}}

Always prioritize accuracy and user privacy.',
            true,
            true,
            '["user_name", "user_email", "organization_name", "user_role", "current_time"]'::jsonb
        )
    """)


def downgrade():
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('colonel_system_prompts')
    op.drop_table('colonel_audit_log')
    op.drop_table('colonel_tool_executions')
    op.drop_table('colonel_messages')
    op.drop_table('colonel_conversations')
