# app/api/router.py
from fastapi import APIRouter
from app.api.endpoints import (
    dashboard,
    companies,
    leads,
    followups,
    data_quality,
    imports,
    exports,
    assistant,
)

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_router.include_router(followups.router, prefix="/followups", tags=["Follow-ups"])
api_router.include_router(data_quality.router, prefix="/data-quality", tags=["Data Quality"])
api_router.include_router(imports.router, prefix="/imports", tags=["Imports"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["AI Assistant"])
