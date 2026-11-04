# app/api/response.py
from typing import Any, Optional
from pydantic import BaseModel

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[dict] = None

def success_response(data: Any) -> dict:
    return {
        "success": True,
        "data": data,
        "error": None
    }

def error_response(code: str, message: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message
        }
    }
