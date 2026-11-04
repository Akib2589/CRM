# app/utils/dates.py
from datetime import date, datetime
from typing import Union, Optional, Any
from zoneinfo import ZoneInfo
from app.core.config import settings

def get_effective_date() -> date:
    if settings.ASSESSMENT_MODE:
        return settings.ASSESSMENT_REFERENCE_DATE
    try:
        tz = ZoneInfo(settings.TIMEZONE)
        return datetime.now(tz).date()
    except Exception:
        return datetime.now().date()

def parse_date_flexible(val: Union[str, date, datetime, None]) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    
    val_str = str(val).strip()
    if not val_str:
        return None
        
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None

parse_date_safely = parse_date_flexible

def get_followup_status(
    lead_or_date: Any = None,
    stage: Optional[str] = None,
    effective_date: Optional[date] = None
) -> str:
    if effective_date is None:
        effective_date = get_effective_date()

    # If lead object passed
    if hasattr(lead_or_date, "stage"):
        st = getattr(lead_or_date, "stage", "")
        next_d = getattr(lead_or_date, "next_follow_up_date", None)
    else:
        st = stage or ""
        next_d = lead_or_date

    if st in ("Paid", "Lost"):
        return "INACTIVE"
        
    if not next_d:
        return "MISSING"
        
    if isinstance(next_d, str):
        next_d = parse_date_flexible(next_d)
        if not next_d:
            return "MISSING"

    if next_d < effective_date:
        return "OVERDUE"
    elif next_d == effective_date:
        return "DUE_TODAY"
    else:
        return "UPCOMING"
