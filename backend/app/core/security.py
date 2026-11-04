# app/core/security.py
import re

def sanitize_string(value: str | None) -> str | None:
    if not value:
        return None
    # Basic strip and control char removal
    cleaned = "".join(ch for ch in value if ch.isprintable() or ch in ("\n", "\r", "\t"))
    return cleaned.strip()
