# app/schemas/lead.py
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.schemas.company import CompanyResponse
from app.schemas.data_quality import DataQualityIssueResponse

class LeadBase(BaseModel):
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    deal_value: int = Field(default=0, ge=0)
    stage: str = "New"
    last_contact_date: Optional[date] = None
    next_follow_up_date: Optional[date] = None
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    company_name: str
    industry: Optional[str] = None

class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    deal_value: Optional[int] = Field(default=None, ge=0)
    stage: Optional[str] = None
    last_contact_date: Optional[date] = None
    next_follow_up_date: Optional[date] = None
    notes: Optional[str] = None

class LeadStageUpdateRequest(BaseModel):
    target_stage: Optional[str] = None
    stage: Optional[str] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def populate_target(self):
        if not self.target_stage and self.stage:
            self.target_stage = self.stage
        elif not self.stage and self.target_stage:
            self.stage = self.target_stage
        return self

LeadStageUpdate = LeadStageUpdateRequest

class StageHistoryItem(BaseModel):
    id: int
    from_stage: Optional[str] = None
    to_stage: str
    changed_at: datetime
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class FollowUpItem(BaseModel):
    id: int
    scheduled_date: date
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadResponse(LeadBase):
    id: int
    company_id: int
    company_name: str
    industry: Optional[str] = None
    follow_up_status: str  # OVERDUE, DUE_TODAY, UPCOMING, MISSING, INACTIVE
    formatted_deal_value: str
    open_issues_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadDetailResponse(LeadResponse):
    company: CompanyResponse
    stage_history: List[StageHistoryItem] = []
    follow_ups: List[FollowUpItem] = []
    data_quality_issues: List[DataQualityIssueResponse] = []
