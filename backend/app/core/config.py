import os
from datetime import date
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "BIAI Corporate Lead Pipeline"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./storage/biai_pipeline.db",
        description="SQLite database path"
    )
    
    # Assessment Mode & Dates
    ASSESSMENT_MODE: bool = True
    ASSESSMENT_REFERENCE_DATE: date = date(2026, 11, 1)
    TIMEZONE: str = "Asia/Dhaka"
    
    # AI Configuration
    AI_PROVIDER: str = "openai_compatible"
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
