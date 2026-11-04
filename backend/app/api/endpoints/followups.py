# app/api/endpoints/followups.py
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.services.followup_service import FollowUpService
from app.api.response import success_response

router = APIRouter()

class FollowUpCreate(BaseModel):
    lead_id: int
    scheduled_date: date
    notes: Optional[str] = None

class FollowUpCompleteRequest(BaseModel):
    notes: Optional[str] = None

@router.get("")
def list_followups(
    lead_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = FollowUpService(db)
    followups = service.list_followups(lead_id=lead_id, status=status)
    return success_response(followups)

@router.get("/overdue")
def list_overdue_followups(db: Session = Depends(get_db)):
    service = FollowUpService(db)
    overdue = service.list_overdue()
    return success_response(overdue)

@router.post("")
def create_followup(request: FollowUpCreate, db: Session = Depends(get_db)):
    service = FollowUpService(db)
    try:
        f = service.create_followup(
            lead_id=request.lead_id,
            scheduled_date=request.scheduled_date,
            notes=request.notes
        )
        return success_response({
            "id": f.id,
            "lead_id": f.lead_id,
            "scheduled_date": f.scheduled_date.isoformat(),
            "status": f.status,
            "notes": f.notes
        })
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": str(e)}
        )

@router.post("/{followup_id}/complete")
def complete_followup(
    followup_id: int,
    request: FollowUpCompleteRequest = FollowUpCompleteRequest(),
    db: Session = Depends(get_db)
):
    service = FollowUpService(db)
    f = service.complete_followup(followup_id, notes=request.notes)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FOLLOWUP_NOT_FOUND", "message": f"Follow-up {followup_id} not found."}
        )
    return success_response({
        "id": f.id,
        "status": f.status,
        "notes": f.notes
    })
