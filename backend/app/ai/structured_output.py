# app/ai/structured_output.py
import re
import json
import logging
from typing import Type, TypeVar, Tuple, Optional
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

def extract_json_from_text(text: str) -> Optional[dict]:
    """Extract valid JSON from markdown fences or raw string."""
    text = text.strip()
    
    # Try finding markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    candidate = match.group(1).strip() if match else text

    # Try standard json load
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # Try finding outer braces { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        sub = text[first_brace : last_brace + 1]
        try:
            return json.loads(sub)
        except Exception:
            pass

    return None

def parse_structured_response(text: str, schema_cls: Type[T]) -> Tuple[Optional[T], Optional[str]]:
    raw_json = extract_json_from_text(text)
    if not raw_json:
        return None, "Failed to parse JSON structure from LLM response."

    try:
        parsed = schema_cls.model_validate(raw_json)
        return parsed, None
    except ValidationError as e:
        logger.warning(f"Schema validation error on LLM output: {e.errors()}")
        return None, f"Schema validation failed: {str(e)}"
