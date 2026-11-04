# app/schemas/email.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class EmailDraftGenerateRequest(BaseModel):
    tone: Optional[str] = "polite and professional"
    additional_notes: Optional[str] = None

class EmailDraftResponse(BaseModel):
    id: Optional[int] = None
    lead_id: int
    subject: str
    body: str
    provider: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
