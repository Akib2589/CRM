# app/models/followup.py
from datetime import datetime, date, timezone
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class FollowUp(Base):
    __tablename__ = "follow_ups"
    __table_args__ = (
        Index("idx_followup_lead_date", "lead_id", "scheduled_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, COMPLETED, CANCELLED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    lead = relationship("Lead", back_populates="follow_ups")
