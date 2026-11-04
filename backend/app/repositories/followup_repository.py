# app/repositories/followup_repository.py
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_
from app.models.followup import FollowUp
from app.models.lead import Lead
from app.utils.dates import get_effective_date

class FollowUpRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, followup_id: int) -> Optional[FollowUp]:
        return self.db.execute(select(FollowUp).where(FollowUp.id == followup_id)).scalar_one_or_none()

    def list_by_lead(self, lead_id: int) -> List[FollowUp]:
        return list(
            self.db.execute(
                select(FollowUp)
                .where(FollowUp.lead_id == lead_id)
                .order_by(FollowUp.scheduled_date.desc())
            ).scalars().all()
        )

    def list_overdue(self, effective_date: Optional[date] = None) -> List[FollowUp]:
        if effective_date is None:
            effective_date = get_effective_date()
        query = (
            select(FollowUp)
            .join(Lead, FollowUp.lead_id == Lead.id)
            .options(joinedload(FollowUp.lead).joinedload(Lead.company))
            .where(
                and_(
                    FollowUp.scheduled_date < effective_date,
                    FollowUp.status == "PENDING",
                    Lead.stage.not_in(["Paid", "Lost"])
                )
            )
            .order_by(FollowUp.scheduled_date.asc())
        )
        return list(self.db.execute(query).scalars().all())

    def create(self, lead_id: int, scheduled_date: date, notes: Optional[str] = None) -> FollowUp:
        followup = FollowUp(
            lead_id=lead_id,
            scheduled_date=scheduled_date,
            status="PENDING",
            notes=notes,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(followup)
        self.db.flush()
        return followup

    def update_status(self, followup_id: int, status: str, notes: Optional[str] = None) -> Optional[FollowUp]:
        followup = self.get_by_id(followup_id)
        if not followup:
            return None
        followup.status = status
        if notes:
            followup.notes = notes
        self.db.flush()
        return followup
