"""
Create user_subscriptions table for Epic 5.0

Revision ID: epic_5_0_user_subscriptions
Create Date: 2026-01-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'epic_5_0_user_subscriptions'
down_revision = None  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create user_subscriptions table
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tier_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('billing_cycle', sa.String(20), nullable=False, server_default='monthly'),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('cancel_at', sa.DateTime(), nullable=True),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_user_subscriptions_user_id', 'user_subscriptions', ['user_id'])
    op.create_index('ix_user_subscriptions_stripe_subscription_id', 'user_subscriptions', ['stripe_subscription_id'], unique=True)
    op.create_index('ix_user_subscriptions_stripe_customer_id', 'user_subscriptions', ['stripe_customer_id'])
    op.create_index('ix_user_subscriptions_status', 'user_subscriptions', ['status'])
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_user_subscriptions_user_id',
        'user_subscriptions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_user_subscriptions_tier_id',
        'user_subscriptions', 'subscription_tiers',
        ['tier_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Add unique constraint on user_id (one active subscription per user)
    op.create_unique_constraint(
        'uq_user_subscriptions_user_id',
        'user_subscriptions',
        ['user_id']
    )
    
    # Add stripe_customer_id column to users table if it doesn't exist
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'], unique=True)


def downgrade():
    # Drop indexes and constraints
    op.drop_index('ix_users_stripe_customer_id', 'users')
    op.drop_column('users', 'stripe_customer_id')
    
    op.drop_constraint('uq_user_subscriptions_user_id', 'user_subscriptions')
    op.drop_constraint('fk_user_subscriptions_tier_id', 'user_subscriptions')
    op.drop_constraint('fk_user_subscriptions_user_id', 'user_subscriptions')
    
    op.drop_index('ix_user_subscriptions_status', 'user_subscriptions')
    op.drop_index('ix_user_subscriptions_stripe_customer_id', 'user_subscriptions')
    op.drop_index('ix_user_subscriptions_stripe_subscription_id', 'user_subscriptions')
    op.drop_index('ix_user_subscriptions_user_id', 'user_subscriptions')
    
    # Drop table
    op.drop_table('user_subscriptions')
