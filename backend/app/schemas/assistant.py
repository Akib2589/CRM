# app/schemas/assistant.py
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class NaturalLanguageQueryRequest(BaseModel):
    query: str
    session_id: Optional[int] = None

class StructuredQueryFilters(BaseModel):
    stage: Optional[str] = None
    industry: Optional[str] = None
    overdue_only: Optional[bool] = None
    missing_contact: Optional[bool] = None
    has_duplicates: Optional[bool] = None
    min_deal_value: Optional[int] = None
    max_deal_value: Optional[int] = None

class StructuredIntent(BaseModel):
    intent: str
    filters: Optional[StructuredQueryFilters] = Field(default_factory=StructuredQueryFilters)
    aggregation: Optional[str] = None # sum, count, avg
    field: Optional[str] = None       # deal_value
    group_by: Optional[str] = None
    limit: Optional[int] = None
    clarification_needed: Optional[str] = None

class AssistantLeadItem(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    stage: str
    deal_value: int
    formatted_deal_value: str
    next_follow_up_date: Optional[str] = None
    follow_up_status: str

class AssistantQueryResponse(BaseModel):
    session_id: int
    answer: str
    intent: str
    confidence: float = 1.0
    clarification: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    leads: List[AssistantLeadItem] = []
    summary_metric: Optional[str] = None

class AssistantSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    message_count: int = 0

class WeeklySummaryResponse(BaseModel):
    period: str
    generated_at: str
    summary_markdown: str
    top_priorities: List[Dict[str, Any]]
    total_active_pipeline: str
    overdue_count: int
