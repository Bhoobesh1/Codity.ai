"""
Import every model here. This file's only job is to make sure all model
classes are registered on `Base.metadata` before Alembic's autogenerate
(or `Base.metadata.create_all`) runs. If a model isn't imported somewhere
that gets executed, SQLAlchemy doesn't know it exists and Alembic will
silently skip creating its table -- a classic gotcha.
"""

from app.models.dead_letter_queue import DeadLetterQueueEntry
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.models.job_log import JobLog
from app.models.project import Project
from app.models.queue import Queue
from app.models.retry_policy import RetryPolicy
from app.models.scheduled_job import ScheduledJob
from app.models.user import Organization, OrganizationMember, User
from app.models.worker import Worker, WorkerHeartbeat

__all__ = [
    "User",
    "Organization",
    "OrganizationMember",
    "Project",
    "Queue",
    "RetryPolicy",
    "Job",
    "JobExecution",
    "JobLog",
    "ScheduledJob",
    "Worker",
    "WorkerHeartbeat",
    "DeadLetterQueueEntry",
]
