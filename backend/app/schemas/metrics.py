from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    retried_jobs: int
    dead_letter_jobs: int
    active_workers: int
    unhealthy_workers: int
    total_workers: int
    average_execution_time_ms: float | None
    queue_throughput: dict[str, int]  # queue_id -> completed jobs in the window
