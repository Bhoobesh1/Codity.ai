from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import JobStatus
from app.models.project import Project
from app.models.queue import Queue
from app.models.user import OrganizationMember
from app.repositories import metrics_repository


def _accessible_queue_ids(db: Session, *, user_id: str) -> list[str]:
    org_ids_subquery = select(OrganizationMember.organization_id).where(
        OrganizationMember.user_id == user_id
    )
    project_ids_subquery = select(Project.id).where(Project.organization_id.in_(org_ids_subquery))
    queue_ids = db.execute(
        select(Queue.id).where(Queue.project_id.in_(project_ids_subquery))
    ).scalars().all()
    return list(queue_ids)


def get_dashboard_metrics(db: Session, *, user_id: str) -> dict:
    queue_ids = _accessible_queue_ids(db, user_id=user_id)

    counts = metrics_repository.job_counts_for_queues(db, queue_ids=queue_ids)
    worker_stats = metrics_repository.worker_counts(db)

    def c(status: JobStatus) -> int:
        return counts.get(status.value, 0)

    return {
        "total_jobs": sum(counts.values()),
        "completed_jobs": c(JobStatus.COMPLETED),
        "failed_jobs": c(JobStatus.FAILED),
        "retried_jobs": metrics_repository.retried_job_count(db, queue_ids=queue_ids),
        "dead_letter_jobs": c(JobStatus.DEAD_LETTER),
        "active_workers": worker_stats["active"],
        "unhealthy_workers": worker_stats["unhealthy"],
        "total_workers": worker_stats["total"],
        "average_execution_time_ms": metrics_repository.average_execution_time_ms(
            db, queue_ids=queue_ids
        ),
        "queue_throughput": metrics_repository.queue_throughput(db, queue_ids=queue_ids),
    }
