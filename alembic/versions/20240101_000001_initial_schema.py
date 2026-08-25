"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_tags'),
        sa.UniqueConstraint('name', name='uq_tags_name'),
    )
    op.create_index('ix_tags_category', 'tags', ['category'], unique=False)

    op.create_table(
        'images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('license', sa.String(100), nullable=False),
        sa.Column('attribution', sa.Text(), nullable=False),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('attributes', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_images'),
        sa.UniqueConstraint('filename', name='uq_images_filename'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_images_confidence_range'),
    )
    op.create_index('ix_images_category', 'images', ['category'], unique=False)
    op.create_index('ix_images_subject', 'images', ['subject'], unique=False)

    op.create_table(
        'image_tags',
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('image_id', 'tag_id', name='pk_image_tags'),
    )

    op.create_table(
        'posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('target_category', sa.String(50), nullable=False),
        sa.Column('target_subject', sa.String(100), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_posts'),
        sa.UniqueConstraint('slug', name='uq_posts_slug'),
    )
    op.create_index('ix_posts_target_category', 'posts', ['target_category'], unique=False)

    op.create_table(
        'suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('similarity_score', sa.Numeric(4, 3), nullable=False),
        sa.Column('guard_passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('guard_reason', sa.Text(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_suggestions'),
        sa.CheckConstraint('similarity_score >= -1 AND similarity_score <= 1', name='ck_suggestions_similarity_range'),
    )
    op.create_index('ix_suggestions_post_rank', 'suggestions', ['post_id', 'rank'], unique=False)
    op.create_index('ix_suggestions_guard_passed', 'suggestions', ['guard_passed'], unique=False)
    op.create_index('ix_suggestions_post_id', 'suggestions', ['post_id'], unique=False)
    op.create_index('ix_suggestions_image_id', 'suggestions', ['image_id'], unique=False)

    op.create_table(
        'approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['suggestion_id'], ['suggestions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_approvals'),
        sa.UniqueConstraint('suggestion_id', name='uq_approvals_suggestion_id'),
        sa.CheckConstraint("decision IN ('approved', 'rejected')", name='ck_approvals_decision'),
    )


def downgrade() -> None:
    op.drop_table('approvals')
    op.drop_table('suggestions')
    op.drop_table('posts')
    op.drop_table('image_tags')
    op.drop_table('images')
    op.drop_table('tags')