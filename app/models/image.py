import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String, Text, Numeric, CheckConstraint, Index, ForeignKey, JSON, ARRAY, Float, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    attributes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False
    )
    embedding: Mapped[List[float]] = mapped_column(ARRAY(Float), nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary="image_tags", back_populates="images"
    )
    suggestions: Mapped[List["Suggestion"]] = relationship(
        "Suggestion", back_populates="image"
    )

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_images_confidence_range"),
        CheckConstraint("validation_status IN ('pending', 'success', 'failed', 'partial')", name="ck_images_validation_status"),
        Index("ix_images_subject", "subject"),
        Index("ix_images_category", "category"),
        Index("ix_images_needs_review", "needs_review"),
    )


class ImageTag(Base):
    __tablename__ = "image_tags"

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )