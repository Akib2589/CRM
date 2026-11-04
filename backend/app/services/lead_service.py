# app/services/lead_service.py
from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.company import Company
from app.repositories.lead_repository import LeadRepository
from app.repositories.company_repository import CompanyRepository
from app.services.data_quality_service import DataQualityService
from app.validators.stage_validator import validate_stage_and_value
from app.utils.dates import get_followup_status

class LeadService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LeadRepository(db)
        self.company_repo = CompanyRepository(db)
        self.dq_service = DataQualityService(db)

    def list_leads(
        self,
        search: Optional[str] = None,
        stage: Optional[str] = None,
        industry: Optional[str] = None,
        follow_up_status: Optional[str] = None,
        has_issues_only: Optional[bool] = None,
        sort_by: str = "id",
        sort_order: str = "asc"
    ) -> List[Dict[str, Any]]:
        leads = self.repo.list_leads(
            search=search,
            stage=stage,
            industry=industry,
            follow_up_status=follow_up_status,
            has_issues_only=has_issues_only,
            sort_by=sort_by,
            sort_order=sort_order
        )

        output = []
        for l in leads:
            fu_status = get_followup_status(l.next_follow_up_date, l.stage)
            open_issues = [i for i in l.data_quality_issues if i.status == "OPEN"]
            output.append({
                "id": l.id,
                "company_id": l.company_id,
                "company_name": l.company.name if l.company else "",
                "industry": l.company.industry if l.company else "",
                "contact_name": l.contact_name,
                "contact_role": l.contact_role,
                "contact_email": l.contact_email,
                "contact_phone": l.contact_phone,
                "source": l.source,
                "deal_value": l.deal_value,
                "stage": l.stage,
                "last_contact_date": l.last_contact_date.isoformat() if l.last_contact_date else None,
                "next_follow_up_date": l.next_follow_up_date.isoformat() if l.next_follow_up_date else None,
                "follow_up_status": fu_status,
                "notes": l.notes,
                "issues_count": len(open_issues),
                "has_critical_issue": any(i.severity == "CRITICAL" for i in open_issues),
                "created_at": l.created_at.isoformat(),
                "updated_at": l.updated_at.isoformat(),
            })
        return output

    def get_lead_details(self, lead_id: int) -> Optional[Dict[str, Any]]:
        lead = self.repo.get_by_id(lead_id)
        if not lead:
            return None

        fu_status = get_followup_status(lead.next_follow_up_date, lead.stage)

        return {
            "id": lead.id,
            "company_id": lead.company_id,
            "company_name": lead.company.name if lead.company else "",
            "industry": lead.company.industry if lead.company else "",
            "contact_name": lead.contact_name,
            "contact_role": lead.contact_role,
            "contact_email": lead.contact_email,
            "contact_phone": lead.contact_phone,
            "source": lead.source,
            "deal_value": lead.deal_value,
            "stage": lead.stage,
            "last_contact_date": lead.last_contact_date.isoformat() if lead.last_contact_date else None,
            "next_follow_up_date": lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
            "follow_up_status": fu_status,
            "notes": lead.notes,
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat(),
            "company": {
                "id": lead.company.id,
                "name": lead.company.name,
                "industry": lead.company.industry,
                "normalized_name": lead.company.normalized_name,
            } if lead.company else None,
            "data_quality_issues": [
                {
                    "id": i.id,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "description": i.description,
                    "status": i.status,
                    "detected_at": i.detected_at.isoformat(),
                    "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                }
                for i in lead.data_quality_issues
            ],
            "stage_history": [
                {
                    "id": s.id,
                    "from_stage": s.from_stage,
                    "to_stage": s.to_stage,
                    "changed_at": s.changed_at.isoformat(),
                    "reason": s.reason,
                }
                for s in lead.stage_history
            ],
            "follow_ups": [
                {
                    "id": f.id,
                    "scheduled_date": f.scheduled_date.isoformat(),
                    "status": f.status,
                    "notes": f.notes,
                    "created_at": f.created_at.isoformat(),
                }
                for f in lead.follow_ups
            ],
            "email_drafts": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "body": e.body,
                    "provider": e.provider,
                    "created_at": e.created_at.isoformat(),
                }
                for e in lead.email_drafts
            ],
        }

    def create_lead(self, data: Dict[str, Any]) -> Lead:
        company_name = data.get("company_name", "").strip()
        industry = data.get("industry")
        
        company = self.company_repo.get_or_create(company_name, industry)

        lead = Lead(
            company_id=company.id,
            contact_name=data.get("contact_name"),
            contact_role=data.get("contact_role"),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone"),
            source=data.get("source"),
            deal_value=data.get("deal_value", 0),
            stage=data.get("stage", "New"),
            last_contact_date=data.get("last_contact_date"),
            next_follow_up_date=data.get("next_follow_up_date"),
            notes=data.get("notes"),
        )
        self.db.add(lead)
        self.db.flush()

        # Record initial stage history
        self.repo.record_stage_change(lead.id, None, lead.stage, "Initial creation")

        # Run data quality scan on new lead
        self.db.commit()
        self.db.refresh(lead)
        self.dq_service.scan_all_leads()

        return lead

    def update_lead(self, lead_id: int, updates: Dict[str, Any]) -> Optional[Lead]:
        lead = self.repo.get_by_id(lead_id)
        if not lead:
            return None

        # Check fields
        editable_fields = [
            "contact_name", "contact_role", "contact_email", "contact_phone",
            "source", "deal_value", "last_contact_date", "next_follow_up_date", "notes"
        ]

        for field in editable_fields:
            if field in updates:
                old_val = getattr(lead, field)
                new_val = updates[field]
                if old_val != new_val:
                    setattr(lead, field, new_val)
                    self.repo.record_audit(
                        lead_id=lead.id,
                        action=f"UPDATE_{field.upper()}",
                        old_value=str(old_val),
                        new_value=str(new_val)
                    )

        lead.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(lead)

        # Trigger quality scan to auto-resolve fixed issues
        self.dq_service.scan_all_leads()
        return lead

    def delete_lead(self, lead_id: int) -> bool:
        return self.repo.delete(lead_id)
