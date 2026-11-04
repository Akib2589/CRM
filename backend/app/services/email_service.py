# app/services/email_service.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.lead import Lead
from app.models.email_draft import EmailDraft
from app.ai.client import get_ai_provider
from app.ai.structured_output import extract_json_from_text
from app.repositories.lead_repository import LeadRepository
from app.utils.currency import format_bdt

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts", "email_followup.txt")

class EmailService:
    def __init__(self, db: Session):
        self.db = db
        self.lead_repo = LeadRepository(db)
        self.ai = get_ai_provider()

    def _load_prompt_template(self) -> str:
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return (
                "You are an executive sales advisor for BIAI corporate AI training. "
                "Draft a short, polite, professional follow-up email in English adhering to: "
                '{"subject": "...", "body": "..."}'
            )

    async def generate_draft(
        self,
        lead_id: int,
        tone: Optional[str] = "polite and professional",
        additional_notes: Optional[str] = None
    ) -> EmailDraft:
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead with ID {lead_id} not found.")

        system_prompt = self._load_prompt_template()

        formatted_val = format_bdt(lead.deal_value) if lead.deal_value else "Not finalized / In discussion"
        user_prompt = f"""
Lead Context:
- Company Name: {lead.company.name if lead.company else 'Prospective Client'}
- Industry: {lead.company.industry if lead.company else 'Corporate'}
- Contact Person: {lead.contact_name or 'Hiring / Training Lead'}
- Contact Role: {lead.contact_role or 'Executive'}
- Current Pipeline Stage: {lead.stage}
- Agreed Deal Value: {formatted_val}
- Last Contact Date: {lead.last_contact_date.isoformat() if lead.last_contact_date else 'N/A'}
- Next Follow-up Scheduled: {lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else 'N/A'}
- Internal Lead Notes: {lead.notes or 'None recorded'}
- Desired Tone: {tone}
- Additional Instructions: {additional_notes or 'Standard courteous follow-up'}

Please generate the email follow-up in the requested JSON format.
"""

        raw_output = await self.ai.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        data = extract_json_from_text(raw_output)

        if not data or "subject" not in data or "body" not in data:
            # Fallback if model returned unstructured text
            subject = f"Following up on BIAI Corporate AI Training — {lead.company.name if lead.company else ''}"
            body = raw_output.replace("```json", "").replace("```", "").strip()
        else:
            subject = data["subject"].strip()
            body = data["body"].strip()

        now = datetime.now(timezone.utc)
        draft = EmailDraft(
            lead_id=lead.id,
            subject=subject,
            body=body,
            provider="openai_compatible",
            created_at=now
        )
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)

        return draft

    def list_drafts(self, lead_id: int) -> List[EmailDraft]:
        return list(
            self.db.execute(
                select(EmailDraft)
                .where(EmailDraft.lead_id == lead_id)
                .order_by(EmailDraft.created_at.desc())
            ).scalars().all()
        )
