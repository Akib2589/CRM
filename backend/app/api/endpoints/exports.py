# app/api/endpoints/exports.py
import io
import csv
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.lead_service import LeadService

router = APIRouter()

@router.get("/leads.csv")
def export_leads_csv(db: Session = Depends(get_db)):
    service = LeadService(db)
    leads = service.list_leads()

    output = io.StringIO()
    writer = csv.writer(output)

    # Headers matching original corporate leads CSV
    headers = [
        "lead id",
        "company",
        "industry",
        "contact name",
        "contact role",
        "contact email",
        "contact phone",
        "source",
        "stage",
        "deal value (BDT)",
        "last contact",
        "next follow-up",
        "notes",
        "follow_up_status",
        "data_issues_count"
    ]
    writer.writerow(headers)

    for l in leads:
        writer.writerow([
            f"L{l['id']:02d}",
            l["company_name"],
            l["industry"] or "",
            l["contact_name"] or "",
            l["contact_role"] or "",
            l["contact_email"] or "",
            l["contact_phone"] or "",
            l["source"] or "",
            l["stage"],
            l["deal_value"],
            l["last_contact_date"] or "",
            l["next_follow_up_date"] or "",
            l["notes"] or "",
            l["follow_up_status"],
            l["issues_count"]
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=biai_corporate_leads.csv"}
    )
