# app/schemas/company.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CompanyBase(BaseModel):
    name: str
    industry: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    merged_into_id: Optional[int] = None

class CompanyMergeRequest(BaseModel):
    source_company_id: int
    target_company_id: int
    reason: Optional[str] = "Duplicate company merge"

class CompanyResponse(CompanyBase):
    id: int
    normalized_name: str
    merged_into_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    lead_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
