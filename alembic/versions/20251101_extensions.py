"""Extensions setup (retroactive placeholder)

Revision ID: 20251101_extensions  
Revises: None
Create Date: 2025-11-01 00:00:00.000000

This is a placeholder migration to match what's currently in the database.
The actual migration already ran previously.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251101_extensions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This migration already ran - this is just a placeholder for the migration chain
    pass


def downgrade():
    # This migration already ran - this is just a placeholder for the migration chain
    pass
