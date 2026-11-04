# app/services/weekly_summary_service.py
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.services.data_quality_service import DataQualityService
from app.ai.client import get_ai_provider
from app.utils.currency import format_bdt
from app.utils.dates import get_effective_date

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts", "weekly_summary.txt")

class WeeklySummaryService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics_repo = AnalyticsRepository(db)
        self.dq_service = DataQualityService(db)
        self.ai = get_ai_provider()

    def _load_prompt(self) -> str:
        try:
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "You are BIAI Strategic Sales Advisor. Generate an executive weekly sales priority briefing."

    async def generate_weekly_summary(self) -> Dict[str, Any]:
        ref_date = get_effective_date()
        kpis = self.analytics_repo.get_kpi_summary(ref_date)
        distribution = self.analytics_repo.get_pipeline_distribution()
        priorities = self.analytics_repo.get_deals_requiring_attention(limit=8, effective_date=ref_date)
        dq_summary = self.dq_service.get_summary()

        # Build context for LLM
        context = {
            "effective_assessment_date": ref_date.isoformat(),
            "kpis": {
                "total_leads": kpis["total_leads"],
                "active_pipeline_value_bdt": kpis["active_pipeline_value"],
                "formatted_active_value": format_bdt(kpis["active_pipeline_value"]),
                "paid_deal_value_bdt": kpis["paid_deal_value"],
                "formatted_paid_value": format_bdt(kpis["paid_deal_value"]),
                "overdue_followups_count": kpis["overdue_followups_count"],
                "missing_followup_dates_count": kpis["missing_followup_count"],
                "open_quality_issues_count": kpis["open_quality_issues_count"],
            },
            "stage_breakdown": distribution,
            "top_deals_needing_attention": priorities,
            "data_quality_issues": dq_summary
        }

        system_prompt = self._load_prompt()
        user_prompt = f"""
Pipeline Database Snapshot as of {ref_date.isoformat()}:
{json.dumps(context, indent=2, default=str)}

Please produce the strategic Weekly Priority Summary following the required structure.
"""

        try:
            summary_markdown = await self.ai.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Weekly summary generation failed: {e}")
            summary_markdown = f"""# BIAI Executive Weekly Priority Briefing
**Effective Date:** {ref_date.isoformat()}

## 1. Executive Snapshot
- **Active Pipeline Value:** {format_bdt(kpis['active_pipeline_value'])}
- **Total Leads:** {kpis['total_leads']}
- **Overdue Follow-ups:** {kpis['overdue_followups_count']} deals require immediate outreach.

## 2. Priority Deals to Chase Immediately
{chr(10).join([f"- **{p['company_name']}** ({p['stage']}, {format_bdt(p['deal_value'])}): {', '.join(p['reasons'])}" for p in priorities[:5]])}

## 3. Data Quality & Action Items
- {dq_summary['total_open']} data quality issues detected across leads.
- Critical issues: {dq_summary['critical_count']}.
- Ensure overdue prospects receive personalized outreach today.
"""

        return {
            "period": f"Week of {ref_date.strftime('%B %d, %Y')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_markdown": summary_markdown.strip(),
            "top_priorities": priorities,
            "total_active_pipeline": format_bdt(kpis["active_pipeline_value"]),
            "overdue_count": kpis["overdue_followups_count"]
        }
