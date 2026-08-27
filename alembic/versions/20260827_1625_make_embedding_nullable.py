"""Make embedding columns nullable for regeneration

Revision ID: 005
Revises: 004
Create Date: 2026-08-27 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make embedding columns nullable
    op.alter_column('images', 'embedding', nullable=True)
    op.alter_column('posts', 'embedding', nullable=True)


def downgrade() -> None:
    op.alter_column('images', 'embedding', nullable=False)
    op.alter_column('posts', 'embedding', nullable=False)