# app/core/dependencies.py
from typing import Generator
from sqlalchemy.orm import Session
from app.core.database import get_db

def get_database() -> Generator[Session, None, None]:
    yield from get_db()
