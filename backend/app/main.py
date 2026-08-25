"""
FastAPI application entrypoint.

Kept deliberately thin: routers are defined in app/api/* and wired in
here. Business logic never lives in this file or in route handlers
directly -- it belongs in app/services/ (Phase 2+), keeping API routes
as a thin translation layer between HTTP and the domain logic.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.api.organizations import router as organizations_router
from app.api.projects import router as projects_router
from app.api.queues import router as queues_router
from app.api.scheduled_jobs import router as scheduled_jobs_router
from app.api.workers import router as workers_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Distributed Job Scheduler",
    description="A production-inspired distributed job scheduling platform.",
    version="0.6.0",
)

# The frontend runs on a different origin (localhost:5173) than the API
# (localhost:8000), so the browser blocks requests between them unless
# the API explicitly allows it. In production, replace allow_origins
# with your actual frontend domain instead of a wildcard/localhost list.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(projects_router)
app.include_router(queues_router)
app.include_router(jobs_router)
app.include_router(scheduled_jobs_router)
app.include_router(workers_router)
app.include_router(metrics_router)


@app.get("/")
def root() -> dict:
    return {
        "service": "distributed-job-scheduler",
        "environment": settings.ENVIRONMENT,
        "phase": "6-7 - scheduler and metrics",
    }
