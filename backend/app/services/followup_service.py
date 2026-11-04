# app/services/followup_service.py
from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.followup import FollowUp
from app.models.lead import Lead
from app.repositories.followup_repository import FollowUpRepository
from app.repositories.lead_repository import LeadRepository
from app.utils.dates import get_effective_date, get_followup_status
from app.services.data_quality_service import DataQualityService

class FollowUpService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FollowUpRepository(db)
        self.lead_repo = LeadRepository(db)
        self.dq_service = DataQualityService(db)

    def list_followups(self, lead_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(FollowUp)
        if lead_id:
            query = query.where(FollowUp.lead_id == lead_id)
        if status:
            query = query.where(FollowUp.status == status)

        query = query.order_by(FollowUp.scheduled_date.asc())
        results = list(self.db.execute(query).scalars().all())

        return [
            {
                "id": f.id,
                "lead_id": f.lead_id,
                "scheduled_date": f.scheduled_date.isoformat(),
                "status": f.status,
                "notes": f.notes,
                "created_at": f.created_at.isoformat(),
            }
            for f in results
        ]

    def list_overdue(self, effective_date: Optional[date] = None) -> List[Dict[str, Any]]:
        if effective_date is None:
            effective_date = get_effective_date()

        followups = self.repo.list_overdue(effective_date)
        output = []
        for f in followups:
            lead = f.lead
            days_overdue = (effective_date - f.scheduled_date).days
            output.append({
                "followup_id": f.id,
                "lead_id": lead.id,
                "company_id": lead.company_id,
                "company_name": lead.company.name if lead.company else "",
                "contact_name": lead.contact_name,
                "stage": lead.stage,
                "deal_value": lead.deal_value,
                "scheduled_date": f.scheduled_date.isoformat(),
                "days_overdue": days_overdue,
                "notes": f.notes,
            })
        return output

    def create_followup(self, lead_id: int, scheduled_date: date, notes: Optional[str] = None) -> FollowUp:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead with ID {lead_id} does not exist.")

        followup = self.repo.create(lead_id=lead_id, scheduled_date=scheduled_date, notes=notes)

        # Update lead's next follow-up date if it is earliest pending or lead had none
        if lead.next_follow_up_date is None or scheduled_date <= lead.next_follow_up_date:
            lead.next_follow_up_date = scheduled_date
            lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(followup)

        # Rescan data quality
        self.dq_service.scan_all_leads()
        return followup

    def complete_followup(self, followup_id: int, notes: Optional[str] = None) -> Optional[FollowUp]:
        followup = self.repo.get_by_id(followup_id)
        if not followup:
            return None

        followup.status = "COMPLETED"
        if notes:
            followup.notes = f"{followup.notes or ''} [Completed]: {notes}".strip()

        # Update lead's next follow-up date to the next pending followup, if any
        lead = followup.lead
        if lead:
            next_pending = (
                self.db.execute(
                    select(FollowUp)
                    .where(
                        and_(
                            FollowUp.lead_id == lead.id,
                            FollowUp.status == "PENDING",
                            FollowUp.id != followup.id
                        )
                    )
                    .order_by(FollowUp.scheduled_date.asc())
                ).scalars().first()
            )
            lead.next_follow_up_date = next_pending.scheduled_date if next_pending else None
            lead.last_contact_date = get_effective_date()
            lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(followup)

        self.dq_service.scan_all_leads()
        return followup
