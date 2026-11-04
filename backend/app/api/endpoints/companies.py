# app/api/endpoints/companies.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.company_service import CompanyService
from app.schemas.company import CompanyMergeRequest
from app.api.response import success_response, error_response

router = APIRouter()

@router.get("")
def list_companies(
    search: Optional[str] = None,
    industry: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = CompanyService(db)
    companies = service.list_companies(search=search, industry=industry)
    return success_response(companies)

@router.get("/duplicates")
def get_duplicate_candidates(db: Session = Depends(get_db)):
    service = CompanyService(db)
    duplicates = service.find_duplicate_candidates()
    return success_response(duplicates)

@router.get("/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)):
    service = CompanyService(db)
    company = service.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company {company_id} not found."}
        )
    return success_response({
        "id": company.id,
        "name": company.name,
        "normalized_name": company.normalized_name,
        "industry": company.industry,
        "merged_into_id": company.merged_into_id,
        "leads": [
            {
                "id": l.id,
                "stage": l.stage,
                "deal_value": l.deal_value,
                "contact_name": l.contact_name
            }
            for l in company.leads
        ]
    })

@router.post("/merge")
def merge_companies(request: CompanyMergeRequest, db: Session = Depends(get_db)):
    service = CompanyService(db)
    try:
        result = service.merge_companies(
            source_company_id=request.source_company_id,
            target_company_id=request.target_company_id,
            reason=request.reason
        )
        return success_response(result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MERGE_FAILED", "message": str(e)}
        )
