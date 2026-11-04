# app/api/endpoints/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.analytics_service import AnalyticsService
from app.api.response import success_response

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    service = AnalyticsService(db)
    data = service.get_summary()
    return success_response(data)

@router.get("/pipeline")
def get_pipeline_distribution(db: Session = Depends(get_db)):
    service = AnalyticsService(db)
    data = service.get_pipeline()
    return success_response(data)

@router.get("/priorities")
def get_dashboard_priorities(limit: int = 10, db: Session = Depends(get_db)):
    service = AnalyticsService(db)
    data = service.get_priorities(limit=limit)
    return success_response(data)
