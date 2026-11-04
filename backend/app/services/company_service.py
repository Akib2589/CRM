# app/services/company_service.py
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, or_, func

from app.models.company import Company
from app.models.lead import Lead
from app.models.audit_log import AuditLog
from app.repositories.company_repository import CompanyRepository
from app.validators.duplicate_detector import detect_duplicates, compute_company_similarity

class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompanyRepository(db)

    def list_companies(self, search: Optional[str] = None, industry: Optional[str] = None) -> List[Dict[str, Any]]:
        companies = self.repo.list_all(search=search, industry=industry)
        results = []
        for c in companies:
            results.append({
                "id": c.id,
                "name": c.name,
                "normalized_name": c.normalized_name,
                "industry": c.industry,
                "merged_into_id": c.merged_into_id,
                "lead_count": len(c.leads) if c.leads else 0,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            })
        return results

    def get_company(self, company_id: int) -> Optional[Company]:
        return self.repo.get_by_id(company_id)

    def find_duplicate_candidates(self) -> List[Dict[str, Any]]:
        companies = self.repo.list_all()
        # Pairwise comparison
        duplicates = []
        visited = set()

        for i in range(len(companies)):
            c1 = companies[i]
            if c1.merged_into_id is not None:
                continue

            for j in range(i + 1, len(companies)):
                c2 = companies[j]
                if c2.merged_into_id is not None:
                    continue

                pair_key = tuple(sorted([c1.id, c2.id]))
                if pair_key in visited:
                    continue

                sim = compute_company_similarity(c1.name, c2.name)

                # Check if they share any contact email across their leads
                emails1 = set(l.contact_email.lower().strip() for l in c1.leads if l.contact_email)
                emails2 = set(l.contact_email.lower().strip() for l in c2.leads if l.contact_email)
                shared_emails = emails1.intersection(emails2)

                if sim >= 80.0 or (shared_emails and sim >= 65.0):
                    visited.add(pair_key)
                    duplicates.append({
                        "company_1": {
                            "id": c1.id,
                            "name": c1.name,
                            "industry": c1.industry,
                            "lead_count": len(c1.leads)
                        },
                        "company_2": {
                            "id": c2.id,
                            "name": c2.name,
                            "industry": c2.industry,
                            "lead_count": len(c2.leads)
                        },
                        "similarity_score": round(sim, 1),
                        "shared_emails": list(shared_emails),
                        "suggested_target_id": c1.id if len(c1.leads) >= len(c2.leads) else c2.id,
                        "suggested_source_id": c2.id if len(c1.leads) >= len(c2.leads) else c1.id,
                    })

        return duplicates

    def merge_companies(self, source_company_id: int, target_company_id: int, reason: Optional[str] = "Duplicate merge") -> Dict[str, Any]:
        source = self.repo.get_by_id(source_company_id)
        target = self.repo.get_by_id(target_company_id)

        if not source or not target:
            raise ValueError("Both source and target companies must exist.")

        if source.id == target.id:
            raise ValueError("Cannot merge a company into itself.")

        now = datetime.now(timezone.utc)
        moved_leads_count = 0

        # Move leads from source to target
        for lead in source.leads:
            lead.company_id = target.id
            moved_leads_count += 1
            # Add audit log
            audit = AuditLog(
                lead_id=lead.id,
                company_id=target.id,
                action="COMPANY_MERGED",
                old_value=f"Company ID: {source.id} ({source.name})",
                new_value=f"Company ID: {target.id} ({target.name})",
                created_at=now
            )
            self.db.add(audit)

        source.merged_into_id = target.id
        source.updated_at = now
        target.updated_at = now

        self.db.commit()

        return {
            "success": True,
            "source_company_id": source.id,
            "target_company_id": target.id,
            "moved_leads_count": moved_leads_count,
            "merged_at": now.isoformat()
        }
