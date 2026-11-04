# app/api/endpoints/leads.py
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.lead_service import LeadService
from app.services.pipeline_service import PipelineService
from app.services.email_service import EmailService
from app.schemas.lead import LeadCreate, LeadUpdate, LeadStageUpdateRequest
from app.schemas.email import EmailDraftGenerateRequest
from app.api.response import success_response, error_response

router = APIRouter()

@router.get("")
def list_leads(
    search: Optional[str] = None,
    stage: Optional[str] = None,
    industry: Optional[str] = None,
    follow_up_status: Optional[str] = None,
    has_issues_only: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    leads = service.list_leads(
        search=search,
        stage=stage,
        industry=industry,
        follow_up_status=follow_up_status,
        has_issues_only=has_issues_only,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return success_response(leads)

@router.post("")
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.create_lead(lead_in.model_dump())
    return success_response({"id": lead.id, "message": "Lead created successfully."})

@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.get_lead_details(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} not found."}
        )
    return success_response(lead)

@router.patch("/{lead_id}")
def update_lead(lead_id: int, lead_in: LeadUpdate, db: Session = Depends(get_db)):
    service = LeadService(db)
    updated = service.update_lead(lead_id, lead_in.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} not found."}
        )
    return success_response({"id": updated.id, "message": "Lead updated successfully."})

@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    success = service.delete_lead(lead_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} not found."}
        )
    return success_response({"message": f"Lead {lead_id} deleted."})

@router.patch("/{lead_id}/stage")
def change_lead_stage(lead_id: int, request: LeadStageUpdateRequest, db: Session = Depends(get_db)):
    service = PipelineService(db)
    try:
        result = service.change_stage(
            lead_id=lead_id,
            target_stage=request.target_stage,
            reason=request.reason
        )
        return success_response(result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_STAGE_TRANSITION", "message": str(e)}
        )

@router.get("/{lead_id}/history")
def get_lead_stage_history(lead_id: int, db: Session = Depends(get_db)):
    service = PipelineService(db)
    history = service.get_stage_history(lead_id)
    return success_response(history)

@router.post("/{lead_id}/email-draft")
async def generate_email_draft(
    lead_id: int,
    request: EmailDraftGenerateRequest = EmailDraftGenerateRequest(),
    db: Session = Depends(get_db)
):
    service = EmailService(db)
    try:
        draft = await service.generate_draft(
            lead_id=lead_id,
            tone=request.tone,
            additional_notes=request.additional_notes
        )
        return success_response({
            "id": draft.id,
            "lead_id": draft.lead_id,
            "subject": draft.subject,
            "body": draft.body,
            "provider": draft.provider,
            "created_at": draft.created_at.isoformat()
        })
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_GENERATION_FAILED", "message": str(e)}
        )

@router.get("/{lead_id}/email-drafts")
def list_email_drafts(lead_id: int, db: Session = Depends(get_db)):
    service = EmailService(db)
    drafts = service.list_drafts(lead_id)
    return success_response([
        {
            "id": d.id,
            "lead_id": d.lead_id,
            "subject": d.subject,
            "body": d.body,
            "provider": d.provider,
            "created_at": d.created_at.isoformat()
        }
        for d in drafts
    ])
