# app/services/data_quality_service.py
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, func

from app.models.lead import Lead
from app.models.company import Company
from app.models.data_quality import DataQualityIssue
from app.validators.contact_validator import validate_contact_info
from app.validators.date_validator import validate_lead_dates
from app.validators.stage_validator import validate_stage_and_value
from app.validators.duplicate_detector import detect_duplicates

class DataQualityService:
    def __init__(self, db: Session):
        self.db = db

    def scan_lead(self, lead: Lead, existing_company_records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        detected_issues = []

        # 1. Contact validation
        contact_issues = validate_contact_info(
            contact_name=lead.contact_name,
            contact_email=lead.contact_email,
            contact_phone=lead.contact_phone
        )
        detected_issues.extend(contact_issues)

        # 2. Date validation
        date_issues = validate_lead_dates(
            last_contact_date=lead.last_contact_date,
            next_follow_up_date=lead.next_follow_up_date,
            stage=lead.stage
        )
        detected_issues.extend(date_issues)

        # 3. Stage and Value validation
        stage_issues = validate_stage_and_value(
            stage=lead.stage,
            deal_value=lead.deal_value
        )
        detected_issues.extend(stage_issues)

        # 4. Duplicate company validation
        if lead.company and existing_company_records:
            other_companies = [r for r in existing_company_records if r["lead_id"] != lead.id]
            dup_candidates = detect_duplicates(
                company_name=lead.company.name,
                contact_email=lead.contact_email,
                existing_records=other_companies
            )
            for dup in dup_candidates:
                detected_issues.append({
                    "issue_type": "DUPLICATE_COMPANY",
                    "severity": "WARNING",
                    "description": f"Potential duplicate of company '{dup['matched_company']}' (similarity {dup['similarity_score']}%). {dup['reason']}"
                })

        return detected_issues

    def scan_all_leads(self) -> Dict[str, Any]:
        leads = list(
            self.db.execute(
                select(Lead)
                .join(Company, Lead.company_id == Company.id)
                .options(joinedload(Lead.company), joinedload(Lead.data_quality_issues))
            ).unique().scalars().all()
        )

        company_records = [
            {
                "id": l.company_id,
                "name": l.company.name,
                "normalized_name": l.company.normalized_name,
                "contact_email": l.contact_email,
                "lead_id": l.id,
            }
            for l in leads if l.company
        ]

        total_scanned = len(leads)
        new_issues_count = 0
        resolved_count = 0

        now = datetime.now(timezone.utc)

        for lead in leads:
            active_issues_in_db = {i.issue_type: i for i in lead.data_quality_issues if i.status == "OPEN"}
            detected = self.scan_lead(lead, company_records)
            detected_types = {d["issue_type"]: d for d in detected}

            # Check newly detected issues
            for issue_type, issue_data in detected_types.items():
                if issue_type not in active_issues_in_db:
                    new_issue = DataQualityIssue(
                        lead_id=lead.id,
                        issue_type=issue_type,
                        severity=issue_data["severity"],
                        description=issue_data["description"],
                        status="OPEN",
                        detected_at=now
                    )
                    self.db.add(new_issue)
                    new_issues_count += 1
                else:
                    # Update description if it changed
                    active_issues_in_db[issue_type].description = issue_data["description"]

            # Auto-resolve issues that are no longer present
            for issue_type, db_issue in active_issues_in_db.items():
                if issue_type not in detected_types:
                    db_issue.status = "RESOLVED"
                    db_issue.resolved_at = now
                    resolved_count += 1

        self.db.commit()

        return {
            "total_scanned": total_scanned,
            "new_issues_detected": new_issues_count,
            "issues_resolved": resolved_count,
            "timestamp": now.isoformat()
        }

    def list_issues(self, status: Optional[str] = "OPEN", severity: Optional[str] = None) -> List[DataQualityIssue]:
        query = (
            select(DataQualityIssue)
            .join(Lead, DataQualityIssue.lead_id == Lead.id)
            .join(Company, Lead.company_id == Company.id)
            .options(
                joinedload(DataQualityIssue.lead).joinedload(Lead.company)
            )
        )
        if status:
            query = query.where(DataQualityIssue.status == status)
        if severity:
            query = query.where(DataQualityIssue.severity == severity)

        query = query.order_by(DataQualityIssue.detected_at.desc())
        return list(self.db.execute(query).scalars().all())

    def get_summary(self) -> Dict[str, Any]:
        total_open = self.db.execute(
            select(func.count(DataQualityIssue.id)).where(DataQualityIssue.status == "OPEN")
        ).scalar() or 0

        critical_count = self.db.execute(
            select(func.count(DataQualityIssue.id)).where(
                and_(DataQualityIssue.status == "OPEN", DataQualityIssue.severity == "CRITICAL")
            )
        ).scalar() or 0

        warning_count = self.db.execute(
            select(func.count(DataQualityIssue.id)).where(
                and_(DataQualityIssue.status == "OPEN", DataQualityIssue.severity == "WARNING")
            )
        ).scalar() or 0

        # Breakdown by issue type
        by_type_query = (
            select(DataQualityIssue.issue_type, func.count(DataQualityIssue.id))
            .where(DataQualityIssue.status == "OPEN")
            .group_by(DataQualityIssue.issue_type)
        )
        by_type = {row[0]: row[1] for row in self.db.execute(by_type_query).all()}

        return {
            "total_open": total_open,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "by_type": by_type
        }

    def resolve_issue(self, issue_id: int) -> Optional[DataQualityIssue]:
        issue = self.db.execute(select(DataQualityIssue).where(DataQualityIssue.id == issue_id)).scalar_one_or_none()
        if not issue:
            return None
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(issue)
        return issue

    def dismiss_issue(self, issue_id: int) -> Optional[DataQualityIssue]:
        issue = self.db.execute(select(DataQualityIssue).where(DataQualityIssue.id == issue_id)).scalar_one_or_none()
        if not issue:
            return None
        issue.status = "DISMISSED"
        issue.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(issue)
        return issue
