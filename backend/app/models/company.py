# app/models/company.py
from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    merged_into_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Self-referential merge relations
    merged_into = relationship("Company", remote_side=[id], backref="merged_sources")
    leads = relationship("Lead", back_populates="company", cascade="all, delete-orphan")
