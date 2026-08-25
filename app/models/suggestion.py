import uuid
from datetime import datetime
from sqlalchemy import String, Text, Numeric, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False
    )
    guard_passed: Mapped[bool] = mapped_column(nullable=False, default=False)
    guard_reason: Mapped[str] = mapped_column(Text, nullable=True)
    rank: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    post: Mapped["Post"] = relationship("Post", back_populates="suggestions")
    image: Mapped["Image"] = relationship("Image", back_populates="suggestions")
    approval: Mapped["Approval"] = relationship(
        "Approval", back_populates="suggestion", uselist=False
    )

    __table_args__ = (
        CheckConstraint("similarity_score >= -1 AND similarity_score <= 1", name="ck_suggestions_similarity_range"),
        Index("ix_suggestions_post_rank", "post_id", "rank"),
        Index("ix_suggestions_guard_passed", "guard_passed"),
    )