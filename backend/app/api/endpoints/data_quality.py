# app/api/endpoints/data_quality.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.data_quality_service import DataQualityService
from app.api.response import success_response

router = APIRouter()

@router.get("/issues")
def list_quality_issues(
    status: Optional[str] = "OPEN",
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = DataQualityService(db)
    issues = service.list_issues(status=status, severity=severity)
    return success_response([
        {
            "id": i.id,
            "lead_id": i.lead_id,
            "company_name": i.lead.company.name if i.lead and i.lead.company else "Unknown",
            "issue_type": i.issue_type,
            "severity": i.severity,
            "description": i.description,
            "status": i.status,
            "detected_at": i.detected_at.isoformat(),
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        }
        for i in issues
    ])

@router.get("/summary")
def get_quality_summary(db: Session = Depends(get_db)):
    service = DataQualityService(db)
    summary = service.get_summary()
    return success_response(summary)

@router.post("/scan")
def trigger_quality_scan(db: Session = Depends(get_db)):
    service = DataQualityService(db)
    result = service.scan_all_leads()
    return success_response(result)

@router.patch("/issues/{issue_id}/resolve")
def resolve_issue(issue_id: int, db: Session = Depends(get_db)):
    service = DataQualityService(db)
    issue = service.resolve_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ISSUE_NOT_FOUND", "message": f"Issue {issue_id} not found."}
        )
    return success_response({"id": issue.id, "status": issue.status})

@router.patch("/issues/{issue_id}/dismiss")
def dismiss_issue(issue_id: int, db: Session = Depends(get_db)):
    service = DataQualityService(db)
    issue = service.dismiss_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ISSUE_NOT_FOUND", "message": f"Issue {issue_id} not found."}
        )
    return success_response({"id": issue.id, "status": issue.status})
