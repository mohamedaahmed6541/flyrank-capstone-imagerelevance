"""Add needs_review and validation_status to images

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('images', sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('images', sa.Column('validation_status', sa.String(20), nullable=False, server_default=sa.text("'pending'")))
    op.create_index('ix_images_needs_review', 'images', ['needs_review'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_images_needs_review', table_name='images')
    op.drop_column('images', 'validation_status')
    op.drop_column('images', 'needs_review')