"""
Health check endpoint.

Checks not just "is the process alive" but "can it actually reach the
database" -- a process can be running while its DB connection is broken,
and that distinction matters a lot for container orchestration
(Docker/K8s liveness vs readiness probes) later on.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }
