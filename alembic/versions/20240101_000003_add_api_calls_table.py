"""Add api_calls table for cost tracking

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(10, 6), nullable=False, server_default=sa.text('0.0')),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'success'")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_api_calls'),
        sa.CheckConstraint("status IN ('success', 'failed', 'retry')", name='ck_api_calls_status'),
    )
    op.create_index('ix_api_calls_image_id', 'api_calls', ['image_id'], unique=False)
    op.create_index('ix_api_calls_timestamp', 'api_calls', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_table('api_calls')