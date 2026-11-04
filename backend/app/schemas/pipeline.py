# app/schemas/pipeline.py
from datetime import date
from typing import List, Optional, Dict
from pydantic import BaseModel

class DashboardSummary(BaseModel):
    total_leads: int
    active_leads_count: int
    active_pipeline_value: int
    formatted_active_value: str
    paid_deal_value: int
    formatted_paid_value: str
    lost_deal_value: int
    formatted_lost_value: str
    overdue_follow_ups: int
    missing_follow_up_dates: int
    open_data_quality_issues: int
    reference_date: str

class StageDistributionItem(BaseModel):
    stage: str
    count: int
    total_value: int
    formatted_value: str
    order: int
    is_terminal: bool

class PriorityLeadItem(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    deal_value: int
    formatted_deal_value: str
    stage: str
    next_follow_up_date: Optional[date] = None
    follow_up_status: str
    priority_reason: str
    days_overdue: int = 0
