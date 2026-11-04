# app/services/analytics_service.py
from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.repositories.analytics_repository import AnalyticsRepository
from app.utils.dates import get_effective_date

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    def get_summary(self, effective_date: Optional[date] = None) -> Dict[str, Any]:
        return self.repo.get_kpi_summary(effective_date)

    def get_pipeline(self) -> List[Dict[str, Any]]:
        return self.repo.get_pipeline_distribution()

    def get_priorities(self, limit: int = 10, effective_date: Optional[date] = None) -> List[Dict[str, Any]]:
        return self.repo.get_deals_requiring_attention(limit, effective_date)
