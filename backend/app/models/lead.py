# app/models/lead.py
from datetime import datetime, date, timezone
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("deal_value >= 0", name="check_deal_value_positive"),
        Index("idx_lead_company_stage", "company_id", "stage"),
        Index("idx_lead_next_follow_up", "next_follow_up_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    deal_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    
    last_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    company = relationship("Company", back_populates="leads")
    follow_ups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan", order_by="desc(FollowUp.scheduled_date)")
    stage_history = relationship("StageHistory", back_populates="lead", cascade="all, delete-orphan", order_by="desc(StageHistory.changed_at)")
    data_quality_issues = relationship("DataQualityIssue", back_populates="lead", cascade="all, delete-orphan", order_by="desc(DataQualityIssue.detected_at)")
    email_drafts = relationship("EmailDraft", back_populates="lead", cascade="all, delete-orphan", order_by="desc(EmailDraft.created_at)")
    audit_logs = relationship("AuditLog", back_populates="lead", cascade="all, delete-orphan", order_by="desc(AuditLog.created_at)")
