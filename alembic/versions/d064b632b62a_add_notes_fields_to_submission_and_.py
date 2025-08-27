"""add notes fields to submission and sample

Revision ID: d064b632b62a
Revises: 66f9fa099abe
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd064b632b62a'
down_revision = '66f9fa099abe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notes column to submission table if it doesn't exist
    try:
        op.add_column('submission', sa.Column('notes', sa.String(), nullable=True))
    except Exception:
        pass  # Column might already exist
    
    # Add notes column to sample table if it doesn't exist
    # (Sample table seems to already have this field but let's ensure it)
    try:
        op.add_column('sample', sa.Column('notes', sa.String(), nullable=True))
    except Exception:
        pass  # Column might already exist


def downgrade() -> None:
    # Remove notes column from submission table
    try:
        op.drop_column('submission', 'notes')
    except Exception:
        pass
    
    # Remove notes column from sample table
    try:
        op.drop_column('sample', 'notes')
    except Exception:
        pass