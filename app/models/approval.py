import uuid
from datetime import datetime
from sqlalchemy import String, Text, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suggestions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    suggestion: Mapped["Suggestion"] = relationship("Suggestion", back_populates="approval")

    __table_args__ = (
        CheckConstraint("decision IN ('approved', 'rejected')", name="ck_approvals_decision"),
    )