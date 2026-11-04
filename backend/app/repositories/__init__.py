# app/repositories/__init__.py
from app.repositories.company_repository import CompanyRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.followup_repository import FollowUpRepository
from app.repositories.analytics_repository import AnalyticsRepository

__all__ = [
    "CompanyRepository",
    "LeadRepository",
    "FollowUpRepository",
    "AnalyticsRepository",
]
