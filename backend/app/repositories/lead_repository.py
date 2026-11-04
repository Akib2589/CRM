# app/repositories/lead_repository.py
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, desc, asc, or_
from app.models.lead import Lead
from app.models.company import Company
from app.models.stage_history import StageHistory
from app.models.audit_log import AuditLog
from app.models.data_quality import DataQualityIssue
from app.utils.dates import get_effective_date, get_followup_status
from app.utils.currency import format_bdt

class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, lead_id: int) -> Optional[Lead]:
        query = (
            select(Lead)
            .options(
                joinedload(Lead.company),
                joinedload(Lead.data_quality_issues),
                joinedload(Lead.stage_history),
                joinedload(Lead.follow_ups)
            )
            .where(Lead.id == lead_id)
        )
        return self.db.execute(query).unique().scalar_one_or_none()

    def list_leads(
        self,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        industry: Optional[str] = None,
        follow_up_status: Optional[str] = None,
        has_issues_only: Optional[bool] = None,
        sort_by: str = "id",
        sort_order: str = "asc"
    ) -> List[Lead]:
        query = (
            select(Lead)
            .join(Company, Lead.company_id == Company.id)
            .options(
                joinedload(Lead.company),
                joinedload(Lead.data_quality_issues)
            )
        )

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Company.name).like(term),
                    func.lower(Lead.contact_name).like(term),
                    func.lower(Lead.contact_email).like(term),
                    func.lower(Lead.notes).like(term)
                )
            )

        if stage and stage.strip() and stage != "All":
            query = query.where(Lead.stage == stage.strip())

        if industry and industry.strip() and industry != "All":
            query = query.where(func.lower(Company.industry) == industry.strip().lower())

        leads = list(self.db.execute(query).unique().scalars().all())
        effective_date = get_effective_date()

        # In-memory filter for computed statuses if specified
        if follow_up_status and follow_up_status != "All":
            status_target = follow_up_status.upper()
            leads = [l for l in leads if get_followup_status(l, effective_date) == status_target]

        if has_issues_only is True:
            leads = [
                l for l in leads 
                if any(iss.status == "OPEN" for iss in l.data_quality_issues)
            ]

        # Sorting
        def sort_key(lead: Lead):
            if sort_by == "deal_value":
                return lead.deal_value or 0
            elif sort_by == "company":
                return (lead.company.name if lead.company else "").lower()
            elif sort_by == "next_follow_up":
                return lead.next_follow_up_date or date.max
            elif sort_by == "stage":
                return lead.stage or ""
            return lead.id

        reverse = (sort_order.lower() == "desc")
        leads.sort(key=sort_key, reverse=reverse)
        return leads

    def create(self, lead_data: Dict[str, Any]) -> Lead:
        lead = Lead(**lead_data)
        self.db.add(lead)
        self.db.flush()
        return lead

    def record_stage_change(
        self,
        lead_id: int,
        from_stage: Optional[str],
        to_stage: str,
        reason: Optional[str] = None
    ) -> StageHistory:
        hist = StageHistory(
            lead_id=lead_id,
            from_stage=from_stage,
            to_stage=to_stage,
            reason=reason or "Stage updated",
            changed_at=datetime.now(timezone.utc)
        )
        self.db.add(hist)
        self.db.flush()
        return hist

    def record_audit(
        self,
        lead_id: Optional[int],
        company_id: Optional[int],
        action: str,
        old_val: Optional[str],
        new_val: Optional[str]
    ) -> AuditLog:
        log = AuditLog(
            lead_id=lead_id,
            company_id=company_id,
            action=action,
            old_value=old_val,
            new_value=new_val,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(log)
        self.db.flush()
        return log

    def delete(self, lead_id: int) -> bool:
        lead = self.get_by_id(lead_id)
        if not lead:
            return False
        self.db.delete(lead)
        self.db.flush()
        return True
