# app/services/csv_import_service.py
import csv
import io
import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.lead import Lead
from app.models.followup import FollowUp
from app.models.stage_history import StageHistory
from app.models.audit_log import AuditLog
from app.models.data_quality import DataQualityIssue
from app.repositories.company_repository import CompanyRepository
from app.repositories.lead_repository import LeadRepository
from app.services.data_quality_service import DataQualityService
from app.validators.contact_validator import validate_contact_info
from app.validators.date_validator import validate_lead_dates
from app.validators.stage_validator import validate_stage_and_value
from app.validators.duplicate_detector import detect_duplicates, compute_company_similarity
from app.utils.dates import parse_date_safely, get_effective_date
from app.utils.normalization import normalize_company_name

# In-memory storage for pending previews
PREVIEW_CACHE: Dict[str, Dict[str, Any]] = {}

REQUIRED_COLUMNS = [
    "company",
    "stage",
]

COLUMN_MAP = {
    "lead id": "csv_lead_id",
    "lead_id": "csv_lead_id",
    "company": "company_name",
    "company name": "company_name",
    "industry": "industry",
    "contact name": "contact_name",
    "contact_name": "contact_name",
    "contact role": "contact_role",
    "contact_role": "contact_role",
    "contact email": "contact_email",
    "contact_email": "contact_email",
    "contact phone": "contact_phone",
    "contact_phone": "contact_phone",
    "source": "source",
    "stage": "stage",
    "deal value (bdt)": "deal_value",
    "deal value": "deal_value",
    "deal_value": "deal_value",
    "last contact": "last_contact_date",
    "last_contact": "last_contact_date",
    "next follow-up": "next_follow_up_date",
    "next follow up": "next_follow_up_date",
    "next_follow_up": "next_follow_up_date",
    "notes": "notes",
}

class CSVImportService:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.lead_repo = LeadRepository(db)
        self.dq_service = DataQualityService(db)

    def parse_csv_content(self, content: str) -> List[Dict[str, Any]]:
        # Remove BOM if present
        if content.startswith("\ufeff"):
            content = content[1:]

        reader = csv.DictReader(io.StringIO(content))
        normalized_rows = []

        for raw_row in reader:
            normalized_row = {}
            for col_name, val in raw_row.items():
                if not col_name:
                    continue
                clean_key = col_name.strip().lower()
                mapped_key = COLUMN_MAP.get(clean_key, clean_key)
                normalized_row[mapped_key] = val.strip() if val else None
            normalized_rows.append(normalized_row)

        return normalized_rows

    def preview_csv(self, content: str) -> Dict[str, Any]:
        rows = self.parse_csv_content(content)
        if not rows:
            raise ValueError("CSV file is empty or headers are missing.")

        batch_id = str(uuid.uuid4())
        processed_rows = []
        seen_companies = []

        date_errors_count = 0
        missing_contact_count = 0
        duplicate_candidates_count = 0
        invalid_values_count = 0

        # Check existing DB companies for cross-detection
        existing_companies = self.company_repo.list_all()
        existing_records = [
            {"id": c.id, "name": c.name, "normalized_name": c.normalized_name, "contact_email": None, "lead_id": None}
            for c in existing_companies
        ]

        for idx, row in enumerate(rows):
            csv_id = row.get("csv_lead_id") or f"ROW_{idx+1}"
            company_name = row.get("company_name") or ""
            industry = row.get("industry")
            contact_name = row.get("contact_name")
            contact_role = row.get("contact_role")
            contact_email = row.get("contact_email")
            contact_phone = row.get("contact_phone")
            source = row.get("source")
            stage = row.get("stage") or "New"
            notes = row.get("notes")

            # Parse deal value
            raw_value = row.get("deal_value") or "0"
            deal_value = 0
            try:
                # Remove commas or currency symbols if present
                clean_val_str = str(raw_value).replace(",", "").replace("৳", "").strip()
                deal_value = int(float(clean_val_str)) if clean_val_str else 0
            except (ValueError, TypeError):
                invalid_values_count += 1

            # Parse dates
            last_contact = parse_date_safely(row.get("last_contact_date"))
            next_follow_up = parse_date_safely(row.get("next_follow_up_date"))

            # Run in-memory validations
            issues = []
            c_issues = validate_contact_info(contact_name, contact_email, contact_phone)
            if c_issues:
                issues.extend(c_issues)
                missing_contact_count += 1

            d_issues = validate_lead_dates(last_contact, next_follow_up, stage)
            if d_issues:
                issues.extend(d_issues)
                if any(i["issue_type"] == "DATE_ORDER_ERROR" for i in d_issues):
                    date_errors_count += 1

            s_issues = validate_stage_and_value(stage, deal_value)
            if s_issues:
                issues.extend(s_issues)
                invalid_values_count += len(s_issues)

            # Intra-CSV and database duplicate detection
            all_known = existing_records + seen_companies
            dup_matches = detect_duplicates(company_name, contact_email, all_known)
            if dup_matches:
                duplicate_candidates_count += 1
                for dup in dup_matches:
                    issues.append({
                        "issue_type": "DUPLICATE_COMPANY",
                        "severity": "WARNING",
                        "description": f"Potential duplicate of '{dup['matched_company']}' ({dup['similarity_score']}% match)."
                    })

            seen_companies.append({
                "id": None,
                "name": company_name,
                "normalized_name": normalize_company_name(company_name),
                "contact_email": contact_email,
                "lead_id": csv_id
            })

            processed_rows.append({
                "row_index": idx + 1,
                "csv_lead_id": csv_id,
                "company_name": company_name,
                "industry": industry,
                "contact_name": contact_name,
                "contact_role": contact_role,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "source": source,
                "stage": stage,
                "deal_value": deal_value,
                "last_contact_date": last_contact.isoformat() if last_contact else None,
                "next_follow_up_date": next_follow_up.isoformat() if next_follow_up else None,
                "notes": notes,
                "issues": issues,
                "has_critical": any(i["severity"] == "CRITICAL" for i in issues)
            })

        summary = {
            "batch_id": batch_id,
            "total_rows": len(rows),
            "date_errors_count": date_errors_count,
            "missing_contact_count": missing_contact_count,
            "duplicate_candidates_count": duplicate_candidates_count,
            "invalid_values_count": invalid_values_count,
            "rows_with_issues": sum(1 for r in processed_rows if r["issues"]),
        }

        # Cache preview
        PREVIEW_CACHE[batch_id] = {
            "summary": summary,
            "rows": processed_rows,
            "raw_content": content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        return {
            "summary": summary,
            "rows": processed_rows
        }

    def commit_csv(self, batch_id: Optional[str] = None, content: Optional[str] = None) -> Dict[str, Any]:
        rows_to_import = []
        if batch_id and batch_id in PREVIEW_CACHE:
            rows_to_import = PREVIEW_CACHE[batch_id]["rows"]
        elif content:
            preview_res = self.preview_csv(content)
            rows_to_import = preview_res["rows"]
        else:
            raise ValueError("Either valid batch_id or CSV content must be provided.")

        now = datetime.now(timezone.utc)
        imported_leads = []

        for r in rows_to_import:
            company_name = r["company_name"]
            industry = r["industry"]
            company = self.company_repo.get_or_create(company_name, industry)

            last_contact = parse_date_safely(r["last_contact_date"])
            next_followup = parse_date_safely(r["next_follow_up_date"])

            lead = Lead(
                company_id=company.id,
                contact_name=r["contact_name"],
                contact_role=r["contact_role"],
                contact_email=r["contact_email"],
                contact_phone=r["contact_phone"],
                source=r["source"],
                stage=r["stage"],
                deal_value=r["deal_value"],
                last_contact_date=last_contact,
                next_follow_up_date=next_followup,
                notes=r["notes"],
                created_at=now,
                updated_at=now
            )
            self.db.add(lead)
            self.db.flush()

            # Record initial stage history
            self.lead_repo.record_stage_change(lead.id, None, lead.stage, "Imported from CSV")

            # Create initial FollowUp entry if scheduled
            if next_followup:
                followup = FollowUp(
                    lead_id=lead.id,
                    scheduled_date=next_followup,
                    status="PENDING",
                    notes=f"Initial scheduled follow-up from CSV ({r.get('csv_lead_id')})",
                    created_at=now
                )
                self.db.add(followup)

            # Audit record
            audit = AuditLog(
                lead_id=lead.id,
                company_id=company.id,
                action="CSV_IMPORTED",
                old_value=None,
                new_value=f"Imported from {r.get('csv_lead_id')}",
                created_at=now
            )
            self.db.add(audit)

            imported_leads.append(lead)

        self.db.commit()

        # Run full Data Quality Engine scan across all leads
        dq_results = self.dq_service.scan_all_leads()
        dq_summary = self.dq_service.get_summary()

        report = {
            "total_rows": len(rows_to_import),
            "successfully_imported": len(imported_leads),
            "date_errors": dq_summary["by_type"].get("DATE_ORDER_ERROR", 0),
            "missing_contact_info": dq_summary["by_type"].get("MISSING_CONTACT_NAME", 0) + dq_summary["by_type"].get("MISSING_CONTACT_METHOD", 0) + dq_summary["by_type"].get("MISSING_PHONE", 0) + dq_summary["by_type"].get("MISSING_EMAIL", 0),
            "duplicate_candidates": dq_summary["by_type"].get("DUPLICATE_COMPANY", 0),
            "total_open_issues": dq_summary["total_open"],
            "critical_issues": dq_summary["critical_count"],
            "warning_issues": dq_summary["warning_count"],
            "breakdown_by_type": dq_summary["by_type"],
            "imported_at": now.isoformat()
        }

        return report
