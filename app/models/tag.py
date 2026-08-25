import uuid
from datetime import datetime
from typing import List
from sqlalchemy import String, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    images: Mapped[List["Image"]] = relationship(
        "Image", secondary="image_tags", back_populates="tags"
    )

    __table_args__ = (
        Index("ix_tags_category", "category"),
    )