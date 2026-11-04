# app/validators/date_validator.py
from datetime import date
from typing import List, Dict, Any

def validate_lead_dates(
    last_contact_date: date | None,
    next_follow_up_date: date | None,
    stage: str
) -> List[Dict[str, Any]]:
    issues = []
    
    # Chronological violation: last contact cannot be after next follow-up
    if last_contact_date and next_follow_up_date:
        if last_contact_date > next_follow_up_date:
            issues.append({
                "issue_type": "DATE_ORDER_ERROR",
                "severity": "CRITICAL",
                "description": f"Next follow-up date ({next_follow_up_date.isoformat()}) is chronologically before last contact date ({last_contact_date.isoformat()})."
            })
            
    # Active leads need a next follow up scheduled (Paid and Lost do not need follow up)
    if stage not in ("Paid", "Lost") and not next_follow_up_date:
        issues.append({
            "issue_type": "MISSING_FOLLOW_UP_DATE",
            "severity": "WARNING",
            "description": f"Active deal in stage '{stage}' has no scheduled next follow-up date."
        })
        
    return issues
