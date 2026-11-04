# app/api/endpoints/assistant.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.nl_query_service import NLQueryService
from app.services.weekly_summary_service import WeeklySummaryService
from app.schemas.assistant import NaturalLanguageQueryRequest
from app.api.response import success_response

router = APIRouter()

@router.post("/query")
async def ask_assistant(request: NaturalLanguageQueryRequest, db: Session = Depends(get_db)):
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "QUERY_EMPTY", "message": "Query cannot be empty."}
        )
    service = NLQueryService(db)
    result = await service.process_query(query=request.query, session_id=request.session_id)
    return success_response(result)

@router.get("/sessions")
def list_assistant_sessions(db: Session = Depends(get_db)):
    service = NLQueryService(db)
    sessions = service.list_sessions()
    return success_response(sessions)

@router.get("/sessions/{session_id}")
def get_session_history(session_id: int, db: Session = Depends(get_db)):
    service = NLQueryService(db)
    history = service.get_session_history(session_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": f"Session {session_id} not found."}
        )
    return success_response(history)

@router.post("/weekly-summary")
async def generate_weekly_summary(db: Session = Depends(get_db)):
    service = WeeklySummaryService(db)
    summary = await service.generate_weekly_summary()
    return success_response(summary)
