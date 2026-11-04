# app/schemas/data_quality.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class DataQualityIssueResponse(BaseModel):
    id: int
    lead_id: int
    company_name: Optional[str] = None
    issue_type: str
    severity: str
    description: str
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DataQualityIssueUpdate(BaseModel):
    status: str  # RESOLVED or DISMISSED

class DataQualitySummary(BaseModel):
    total_issues: int
    open_issues: int
    resolved_issues: int
    dismissed_issues: int
    critical_issues: int
    warning_issues: int
    by_type: Dict[str, int]
