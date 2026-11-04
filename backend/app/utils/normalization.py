# app/utils/normalization.py
import re
import unicodedata

def normalize_company_name(name: str | None) -> str:
    if not name:
        return ""
    # Unicode NFKC
    text = unicodedata.normalize("NFKC", str(name))
    text = text.lower().strip()
    
    # Remove punctuation / special symbols, keep alphanumeric and spaces
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    # Suffixes sorted by longest first
    suffixes = [
        " private limited",
        " pvt ltd",
        " pvt. ltd.",
        " pvt limited",
        " limited",
        " corporation",
        " pharmaceuticals",
        " pharma ltd",
        " textiles ltd",
        " industries",
        " hospitality group",
        " ltd",
        " corp",
        " inc",
        " pvt",
        " co"
    ]
    # Suffix normalization with caution (longest first)
    for suffix in suffixes:
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
            break
            
    return text.strip()

def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = str(email).strip().lower()
    return cleaned if cleaned else None

def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = str(phone).strip()
    # Normalize multiple spaces or dashes if needed
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned if cleaned else None

def clean_deal_value(val: str | int | float | None) -> int:
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(val))
    val_str = str(val).strip()
    # Remove currency symbols (৳, Tk, BDT, $, commas)
    val_clean = re.sub(r"[^\d.]", "", val_str)
    try:
        return max(0, int(float(val_clean))) if val_clean else 0
    except (ValueError, TypeError):
        return 0
