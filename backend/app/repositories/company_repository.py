# app/repositories/company_repository.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.company import Company
from app.models.lead import Lead
from app.utils.normalization import normalize_company_name

class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, company_id: int) -> Optional[Company]:
        return self.db.execute(select(Company).where(Company.id == company_id)).scalar_one_or_none()

    def get_by_exact_name(self, name: str) -> Optional[Company]:
        return self.db.execute(select(Company).where(func.lower(Company.name) == name.strip().lower())).scalars().first()

    def get_by_normalized_name(self, norm_name: str) -> Optional[Company]:
        return self.db.execute(
            select(Company).where(Company.normalized_name == norm_name, Company.merged_into_id.is_(None))
        ).scalars().first()

    def list_all(
        self,
        active_only: bool = True,
        search: Optional[str] = None,
        industry: Optional[str] = None
    ) -> List[Company]:
        query = select(Company)
        if active_only:
            query = query.where(Company.merged_into_id.is_(None))
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(func.lower(Company.name).like(term))
        if industry and industry.strip():
            query = query.where(func.lower(Company.industry) == industry.strip().lower())
        return list(self.db.execute(query.order_by(Company.name)).scalars().all())

    def create(self, name: str, industry: Optional[str] = None) -> Company:
        norm = normalize_company_name(name)
        company = Company(
            name=name.strip(),
            normalized_name=norm,
            industry=industry.strip() if industry else None
        )
        self.db.add(company)
        self.db.flush()
        return company

    def get_or_create(self, name: str, industry: Optional[str] = None, create_always: bool = True) -> Company:
        if not create_always:
            existing = self.get_by_exact_name(name)
            if existing:
                return existing
        return self.create(name=name, industry=industry)

    def merge_companies(self, source_id: int, target_id: int) -> Company:
        source = self.get_by_id(source_id)
        target = self.get_by_id(target_id)
        if not source or not target:
            raise ValueError("Invalid source or target company ID")
        if source_id == target_id:
            raise ValueError("Cannot merge company into itself")

        # Mark source as merged
        source.merged_into_id = target_id
        
        # Point all leads belonging to source to target
        self.db.query(Lead).filter(Lead.company_id == source_id).update({"company_id": target_id})
        self.db.flush()
        return target
