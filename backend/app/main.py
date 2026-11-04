# app/main.py
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models import (
    Company,
    Lead,
    FollowUp,
    StageHistory,
    DataQualityIssue,
    EmailDraft,
    AuditLog,
    AssistantSession,
    AssistantMessage,
)
from app.api.router import api_router
from app.services.csv_import_service import CSVImportService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("biai_pipeline")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directory exists
    os.makedirs("./storage", exist_ok=True)
    os.makedirs("./data/imports", exist_ok=True)
    os.makedirs("./data/exports", exist_ok=True)

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")

    # Seed initial sample data if DB is empty
    db = SessionLocal()
    try:
        leads_count = db.query(Lead).count()
        if leads_count == 0:
            candidates = [
                os.path.abspath("./data/imports/corporate-leads.csv"),
                os.path.abspath("../data/imports/corporate-leads.csv"),
                "/root/Desktop/assignments/task2/data/imports/corporate-leads.csv"
            ]
            sample_csv_path = next((p for p in candidates if os.path.exists(p)), None)
            if sample_csv_path:
                logger.info(f"Database is empty. Auto-seeding initial 25 sample corporate leads from {sample_csv_path}...")
                with open(sample_csv_path, "r", encoding="utf-8") as f:
                    csv_text = f.read()
                import_service = CSVImportService(db)
                report = import_service.commit_csv(content=csv_text)
                logger.info(f"Auto-seed complete: {report['successfully_imported']} leads imported with {report['total_open_issues']} issues flagged.")
            else:
                logger.warning("Sample CSV file not found at any expected path.")
    except Exception as e:
        logger.error(f"Error during database initialization/seeding: {e}")
    finally:
        db.close()

    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers for standard error structure
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(exc.detail))
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg") if errors else "Validation failed"
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": first_msg,
                "details": errors
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc)
            }
        }
    )

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "success": True,
        "message": "BIAI Corporate Lead Pipeline Backend API is operational.",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "assessment_mode": settings.ASSESSMENT_MODE}
