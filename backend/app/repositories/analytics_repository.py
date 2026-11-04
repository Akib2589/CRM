# app/repositories/analytics_repository.py
from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, and_, or_, desc
from app.models.lead import Lead
from app.models.company import Company
from app.models.followup import FollowUp
from app.models.data_quality import DataQualityIssue
from app.validators.stage_validator import ACTIVE_STAGES, LeadStage
from app.utils.dates import get_effective_date

class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_kpi_summary(self, effective_date: Optional[date] = None) -> Dict[str, Any]:
        if effective_date is None:
            effective_date = get_effective_date()

        # Total leads
        total_leads = self.db.execute(select(func.count(Lead.id))).scalar() or 0

        # Active pipeline value
        active_pipeline_value = self.db.execute(
            select(func.coalesce(func.sum(Lead.deal_value), 0))
            .where(Lead.stage.in_(ACTIVE_STAGES))
        ).scalar() or 0

        # Paid value
        paid_deal_value = self.db.execute(
            select(func.coalesce(func.sum(Lead.deal_value), 0))
            .where(Lead.stage == LeadStage.PAID.value)
        ).scalar() or 0

        # Lost value
        lost_deal_value = self.db.execute(
            select(func.coalesce(func.sum(Lead.deal_value), 0))
            .where(Lead.stage == LeadStage.LOST.value)
        ).scalar() or 0

        # Overdue follow-ups
        overdue_followups_count = self.db.execute(
            select(func.count(FollowUp.id))
            .join(Lead, FollowUp.lead_id == Lead.id)
            .where(
                and_(
                    FollowUp.scheduled_date < effective_date,
                    FollowUp.status == "PENDING",
                    Lead.stage.not_in(["Paid", "Lost"])
                )
            )
        ).scalar() or 0

        # Missing follow-up dates (active leads with no next_follow_up_date)
        missing_followup_count = self.db.execute(
            select(func.count(Lead.id))
            .where(
                and_(
                    Lead.next_follow_up_date.is_(None),
                    Lead.stage.not_in(["Paid", "Lost"])
                )
            )
        ).scalar() or 0

        # Open Data Quality Issues
        open_quality_issues_count = self.db.execute(
            select(func.count(DataQualityIssue.id))
            .where(DataQualityIssue.status == "OPEN")
        ).scalar() or 0

        return {
            "effective_date": effective_date.isoformat(),
            "total_leads": total_leads,
            "active_pipeline_value": active_pipeline_value,
            "paid_deal_value": paid_deal_value,
            "lost_deal_value": lost_deal_value,
            "overdue_followups_count": overdue_followups_count,
            "missing_followup_count": missing_followup_count,
            "open_quality_issues_count": open_quality_issues_count,
        }

    def get_pipeline_distribution(self) -> List[Dict[str, Any]]:
        stages_order = [
            LeadStage.NEW.value,
            LeadStage.CONTACTED.value,
            LeadStage.MEETING.value,
            LeadStage.PROPOSAL.value,
            LeadStage.INVOICE_SENT.value,
            LeadStage.PAID.value,
            LeadStage.LOST.value,
        ]

        query = (
            select(
                Lead.stage,
                func.count(Lead.id).label("count"),
                func.coalesce(func.sum(Lead.deal_value), 0).label("total_value")
            )
            .group_by(Lead.stage)
        )
        results = {row[0]: {"count": row[1], "total_value": row[2]} for row in self.db.execute(query).all()}

        distribution = []
        for stage in stages_order:
            stage_data = results.get(stage, {"count": 0, "total_value": 0})
            distribution.append({
                "stage": stage,
                "count": stage_data["count"],
                "total_value": stage_data["total_value"],
                "is_active": stage in ACTIVE_STAGES,
                "is_terminal": stage in [LeadStage.PAID.value, LeadStage.LOST.value]
            })

        return distribution

    def get_deals_requiring_attention(self, limit: int = 10, effective_date: Optional[date] = None) -> List[Dict[str, Any]]:
        if effective_date is None:
            effective_date = get_effective_date()

        # Prioritize active leads that have overdue followups or open data quality issues
        query = (
            select(Lead)
            .join(Company, Lead.company_id == Company.id)
            .options(
                joinedload(Lead.company),
                joinedload(Lead.data_quality_issues),
                joinedload(Lead.follow_ups)
            )
            .where(Lead.stage.not_in(["Paid", "Lost"]))
            .order_by(desc(Lead.deal_value))
        )
        leads = list(self.db.execute(query).unique().scalars().all())

        priorities = []
        for lead in leads:
            reasons = []
            if lead.next_follow_up_date and lead.next_follow_up_date < effective_date:
                days_overdue = (effective_date - lead.next_follow_up_date).days
                reasons.append(f"Follow-up is {days_overdue} days overdue")
            elif lead.next_follow_up_date is None:
                reasons.append("Missing next follow-up date")

            open_issues = [i for i in lead.data_quality_issues if i.status == "OPEN"]
            if open_issues:
                issue_types = ", ".join(set(i.issue_type for i in open_issues))
                reasons.append(f"Data issues: {issue_types}")

            if reasons:
                priorities.append({
                    "lead_id": lead.id,
                    "company_id": lead.company_id,
                    "company_name": lead.company.name if lead.company else "Unknown",
                    "stage": lead.stage,
                    "deal_value": lead.deal_value,
                    "contact_name": lead.contact_name,
                    "next_follow_up_date": lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
                    "reasons": reasons,
                    "has_critical_issue": any(i.severity == "CRITICAL" for i in open_issues)
                })

        return priorities[:limit]

    def execute_structured_query(self, intent: str, filters: Dict[str, Any], aggregation: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Execute allowlisted deterministic queries for NL assistant."""
        effective_date = get_effective_date()

        if intent == "list_overdue":
            query = (
                select(Lead)
                .join(Company, Lead.company_id == Company.id)
                .options(joinedload(Lead.company))
                .where(
                    and_(
                        Lead.next_follow_up_date < effective_date,
                        Lead.stage.not_in(["Paid", "Lost"])
                    )
                )
                .order_by(Lead.next_follow_up_date.asc())
            )
            if limit:
                query = query.limit(limit)
            leads = list(self.db.execute(query).unique().scalars().all())
            return {
                "intent": intent,
                "count": len(leads),
                "items": [
                    {
                        "lead_id": l.id,
                        "company_name": l.company.name if l.company else "",
                        "stage": l.stage,
                        "deal_value": l.deal_value,
                        "next_follow_up_date": l.next_follow_up_date.isoformat() if l.next_follow_up_date else None,
                        "contact_name": l.contact_name,
                    }
                    for l in leads
                ]
            }

        elif intent == "aggregate_deal_value":
            stage_filter = filters.get("stage")
            industry_filter = filters.get("industry")
            
            stmt = select(
                func.coalesce(func.sum(Lead.deal_value), 0),
                func.coalesce(func.avg(Lead.deal_value), 0),
                func.count(Lead.id)
            ).join(Company, Lead.company_id == Company.id)

            if stage_filter:
                stmt = stmt.where(func.lower(Lead.stage) == stage_filter.lower())
            if industry_filter:
                stmt = stmt.where(func.lower(Company.industry) == industry_filter.lower())

            sum_val, avg_val, count = self.db.execute(stmt).one()
            val = avg_val if aggregation == "avg" else sum_val

            return {
                "intent": intent,
                "aggregation": aggregation or "sum",
                "value": float(val),
                "count": count,
                "filters": filters
            }

        elif intent == "count_leads":
            stage_filter = filters.get("stage")
            industry_filter = filters.get("industry")
            
            stmt = select(func.count(Lead.id)).join(Company, Lead.company_id == Company.id)
            if stage_filter:
                stmt = stmt.where(func.lower(Lead.stage) == stage_filter.lower())
            if industry_filter:
                stmt = stmt.where(func.lower(Company.industry) == industry_filter.lower())

            count = self.db.execute(stmt).scalar() or 0
            return {
                "intent": intent,
                "count": count,
                "filters": filters
            }

        elif intent in ("list_by_stage", "list_by_industry"):
            stage_filter = filters.get("stage")
            industry_filter = filters.get("industry")

            stmt = select(Lead).join(Company, Lead.company_id == Company.id).options(joinedload(Lead.company))
            if stage_filter:
                stmt = stmt.where(func.lower(Lead.stage) == stage_filter.lower())
            if industry_filter:
                stmt = stmt.where(func.lower(Company.industry) == industry_filter.lower())

            if limit:
                stmt = stmt.limit(limit)

            leads = list(self.db.execute(stmt).unique().scalars().all())
            return {
                "intent": intent,
                "count": len(leads),
                "items": [
                    {
                        "lead_id": l.id,
                        "company_name": l.company.name if l.company else "",
                        "stage": l.stage,
                        "deal_value": l.deal_value,
                        "contact_name": l.contact_name,
                        "industry": l.company.industry if l.company else "",
                    }
                    for l in leads
                ]
            }

        elif intent == "highest_value_deals":
            limit = limit or 5
            stmt = (
                select(Lead)
                .join(Company, Lead.company_id == Company.id)
                .options(joinedload(Lead.company))
                .where(Lead.stage.not_in(["Lost"]))
                .order_by(desc(Lead.deal_value))
                .limit(limit)
            )
            leads = list(self.db.execute(stmt).unique().scalars().all())
            return {
                "intent": intent,
                "items": [
                    {
                        "lead_id": l.id,
                        "company_name": l.company.name if l.company else "",
                        "stage": l.stage,
                        "deal_value": l.deal_value,
                        "contact_name": l.contact_name,
                    }
                    for l in leads
                ]
            }

        elif intent == "find_missing_contact":
            stmt = (
                select(Lead)
                .join(Company, Lead.company_id == Company.id)
                .options(joinedload(Lead.company))
                .where(
                    or_(
                        Lead.contact_name.is_(None),
                        Lead.contact_name == "",
                        Lead.contact_email.is_(None),
                        Lead.contact_email == "",
                        Lead.contact_phone.is_(None),
                        Lead.contact_phone == "",
                    )
                )
            )
            leads = list(self.db.execute(stmt).unique().scalars().all())
            return {
                "intent": intent,
                "count": len(leads),
                "items": [
                    {
                        "lead_id": l.id,
                        "company_name": l.company.name if l.company else "",
                        "contact_name": l.contact_name,
                        "contact_email": l.contact_email,
                        "contact_phone": l.contact_phone,
                        "stage": l.stage
                    }
                    for l in leads
                ]
            }

        elif intent == "pipeline_summary":
            kpis = self.get_kpi_summary(effective_date)
            dist = self.get_pipeline_distribution()
            return {
                "intent": intent,
                "summary": kpis,
                "distribution": dist
            }

        # Fallback
        return {
            "intent": intent,
            "message": "Query executed without specific filters.",
            "filters": filters
        }
