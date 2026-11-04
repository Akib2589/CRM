# app/validators/contact_validator.py
import re
from typing import List, Dict, Any

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_contact_info(
    contact_name: str | None,
    contact_email: str | None,
    contact_phone: str | None
) -> List[Dict[str, Any]]:
    issues = []
    
    has_name = bool(contact_name and contact_name.strip())
    has_email = bool(contact_email and contact_email.strip())
    has_phone = bool(contact_phone and contact_phone.strip())
    
    if not has_name:
        issues.append({
            "issue_type": "MISSING_CONTACT_NAME",
            "severity": "WARNING",
            "description": "Lead has no primary contact name assigned."
        })
        
    if not has_email and not has_phone:
        issues.append({
            "issue_type": "MISSING_CONTACT_METHOD",
            "severity": "CRITICAL",
            "description": "Lead has neither email nor phone number. Cannot reach contact."
        })
    elif not has_email:
        issues.append({
            "issue_type": "MISSING_EMAIL",
            "severity": "WARNING",
            "description": "Lead is missing contact email address."
        })
    elif not has_phone:
        issues.append({
            "issue_type": "MISSING_PHONE",
            "severity": "WARNING",
            "description": "Lead is missing contact phone number."
        })
        
    if has_email:
        email_clean = contact_email.strip()
        if not EMAIL_REGEX.match(email_clean) or ".." in email_clean:
            issues.append({
                "issue_type": "INVALID_EMAIL",
                "severity": "WARNING",
                "description": f"Email format '{email_clean}' appears malformed or invalid."
            })
            
    return issues
