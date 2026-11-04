# app/api/endpoints/imports.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.services.csv_import_service import CSVImportService
from app.api.response import success_response

router = APIRouter()

class CommitImportRequest(BaseModel):
    batch_id: Optional[str] = None
    csv_content: Optional[str] = None

@router.post("/preview")
async def preview_csv_import(
    file: Optional[UploadFile] = File(None),
    csv_text: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    service = CSVImportService(db)
    content = ""
    if file:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="replace")
    elif csv_text:
        content = csv_text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILE_REQUIRED", "message": "No CSV file or text provided."}
        )

    try:
        preview = service.preview_csv(content)
        return success_response(preview)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CSV_PARSE_ERROR", "message": str(e)}
        )

@router.post("/commit")
def commit_csv_import(request: CommitImportRequest, db: Session = Depends(get_db)):
    service = CSVImportService(db)
    try:
        report = service.commit_csv(batch_id=request.batch_id, content=request.csv_content)
        return success_response(report)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CSV_COMMIT_ERROR", "message": str(e)}
        )
