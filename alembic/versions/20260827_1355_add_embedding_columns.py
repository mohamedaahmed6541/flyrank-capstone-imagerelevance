"""Add embedding indexes to images and posts

Revision ID: 004
Revises: 003
Create Date: 2026-08-27 13:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Embedding columns already exist, just add indexes
    op.create_index('ix_images_embedding', 'images', ['embedding'], unique=False, postgresql_using='gin')
    op.create_index('ix_posts_embedding', 'posts', ['embedding'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('ix_posts_embedding', table_name='posts')
    op.drop_index('ix_images_embedding', table_name='images')