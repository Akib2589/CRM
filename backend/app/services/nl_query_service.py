# app/services/nl_query_service.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.assistant_session import AssistantSession, AssistantMessage
from app.repositories.analytics_repository import AnalyticsRepository
from app.ai.client import get_ai_provider
from app.ai.structured_output import extract_json_from_text
from app.utils.currency import format_bdt
from app.utils.dates import get_effective_date

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts", "nl_query_system.txt")

ALLOWED_INTENTS = {
    "list_overdue",
    "count_leads",
    "aggregate_deal_value",
    "list_by_stage",
    "list_by_industry",
    "find_missing_contact",
    "find_duplicates",
    "list_upcoming",
    "highest_value_deals",
    "pipeline_summary",
}

class NLQueryService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics_repo = AnalyticsRepository(db)
        self.ai = get_ai_provider()

    def _load_system_prompt(self) -> str:
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "Extract JSON intent: {'intent': '...', 'filters': {...}, 'aggregation': '...', 'limit': null}"

    def _heuristic_intent(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        if "overdue" in lower or "late" in lower or "বাকি" in lower or "দেরি" in lower:
            return {"intent": "list_overdue", "filters": {}, "aggregation": None, "limit": None}
        if "duplicate" in lower or "একই" in lower or "ডুপ্লিকেট" in lower:
            return {"intent": "find_duplicates", "filters": {}, "aggregation": None, "limit": None}
        if "missing" in lower or "নাই" in lower or "নেই" in lower or "ইমেইল" in lower or "ফোন" in lower:
            return {"intent": "find_missing_contact", "filters": {}, "aggregation": None, "limit": None}
        if "top" in lower or "highest" in lower or "biggest" in lower or "সবচেয়ে বড়" in lower:
            return {"intent": "highest_value_deals", "filters": {}, "aggregation": None, "limit": 5}
        
        # Stages
        stages = ["new", "contacted", "meeting", "proposal", "invoice sent", "paid", "lost"]
        matched_stage = None
        for s in stages:
            if s in lower:
                matched_stage = s.title()
                if matched_stage == "Invoice Sent":
                    matched_stage = "Invoice sent"
                break

        if ("value" in lower or "টাকা" in lower or "amount" in lower or "মোট" in lower or "total" in lower) and matched_stage:
            return {"intent": "aggregate_deal_value", "filters": {"stage": matched_stage}, "aggregation": "sum", "limit": None}
        if matched_stage:
            return {"intent": "list_by_stage", "filters": {"stage": matched_stage}, "aggregation": None, "limit": None}

        return {"intent": "pipeline_summary", "filters": {}, "aggregation": None, "limit": None}

    async def process_query(self, query: str, session_id: Optional[int] = None) -> Dict[str, Any]:
        # 1. Session setup
        session = None
        if session_id:
            session = self.db.execute(select(AssistantSession).where(AssistantSession.id == session_id)).scalar_one_or_none()
        if not session:
            title = query[:40] + ("..." if len(query) > 40 else "")
            session = AssistantSession(title=title, created_at=datetime.now(timezone.utc))
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

        # Record user message
        user_msg = AssistantMessage(
            session_id=session.id,
            role="user",
            content=query,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(user_msg)
        self.db.commit()

        # 2. Extract structured intent via LLM
        system_prompt = self._load_system_prompt()
        intent_data = None
        try:
            raw_intent = await self.ai.generate(
                system_prompt=system_prompt,
                user_prompt=f"User Query: {query}",
                temperature=0.0
            )
            intent_data = extract_json_from_text(raw_intent)
        except Exception as e:
            logger.warning(f"AI intent extraction failed, using heuristic: {e}")

        if not intent_data or intent_data.get("intent") not in ALLOWED_INTENTS:
            intent_data = self._heuristic_intent(query)

        intent = intent_data.get("intent", "pipeline_summary")
        filters = intent_data.get("filters") or {}
        aggregation = intent_data.get("aggregation")
        limit = intent_data.get("limit")

        # 3. Execute authoritative deterministic query against DB
        db_result = self.analytics_repo.execute_structured_query(
            intent=intent,
            filters=filters,
            aggregation=aggregation,
            limit=limit
        )

        # 4. Generate formatted natural language response using LLM or deterministic template
        format_prompt = f"""
You are the BIAI Corporate Pipeline Assistant.
The user asked: "{query}"

We retrieved the following verified, authoritative data from SQLite:
{json.dumps(db_result, indent=2, default=str)}

Respond directly to the user in a natural, helpful, polite tone.
Rules:
- Match the language of the user's question (if they asked in Bengali or Banglish, answer naturally in Bengali or Banglish. If English, answer in English).
- Always use the exact figures and data from the query result. Do NOT invent numbers.
- Mention currency as BDT (৳).
- Keep it concise and informative.
"""
        try:
            answer = await self.ai.generate(
                system_prompt="You format business pipeline data into clear answers matching user language.",
                user_prompt=format_prompt,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"Failed to generate formatted response: {e}")
            if intent == "aggregate_deal_value":
                st = filters.get("stage", "selected")
                val_formatted = format_bdt(db_result.get("value", 0))
                answer = f"The total deal value for {st} stage is {val_formatted} across {db_result.get('count', 0)} deals."
            elif intent == "list_overdue":
                answer = f"There are currently {db_result.get('count', 0)} deals with overdue follow-ups."
            else:
                answer = f"Query executed successfully with {db_result.get('count', 0)} matching records."

        # 5. Format lead items if present
        lead_items = []
        if "items" in db_result:
            for item in db_result["items"]:
                val = item.get("deal_value", 0)
                lead_items.append({
                    "id": item.get("lead_id", 0),
                    "company_name": item.get("company_name", ""),
                    "contact_name": item.get("contact_name"),
                    "contact_email": item.get("contact_email"),
                    "contact_phone": item.get("contact_phone"),
                    "stage": item.get("stage", ""),
                    "deal_value": val,
                    "formatted_deal_value": format_bdt(val),
                    "next_follow_up_date": item.get("next_follow_up_date"),
                    "follow_up_status": "Overdue" if intent == "list_overdue" else "Normal"
                })

        # Save assistant message
        asst_msg = AssistantMessage(
            session_id=session.id,
            role="assistant",
            content=answer,
            structured_data=json.dumps(db_result, default=str),
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(asst_msg)
        self.db.commit()

        return {
            "session_id": session.id,
            "answer": answer.strip(),
            "intent": intent,
            "confidence": 1.0,
            "structured_data": db_result,
            "leads": lead_items,
            "summary_metric": format_bdt(db_result.get("value", 0)) if "value" in db_result else None
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = list(
            self.db.execute(
                select(AssistantSession).order_by(AssistantSession.created_at.desc())
            ).scalars().all()
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "message_count": len(s.messages)
            }
            for s in sessions
        ]

    def get_session_history(self, session_id: int) -> Optional[Dict[str, Any]]:
        session = self.db.execute(select(AssistantSession).where(AssistantSession.id == session_id)).scalar_one_or_none()
        if not session:
            return None
        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "structured_data": json.loads(m.structured_data) if m.structured_data else None,
                    "created_at": m.created_at.isoformat(),
                }
                for m in session.messages
            ]
        }
