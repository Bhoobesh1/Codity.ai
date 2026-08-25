from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.models.base import JobStatus, JobType, WorkerStatus
from app.models.job import Job
from app.models.project import Project
from app.models.queue import Queue
from app.models.user import Organization
from app.models.worker import Worker
from app.repositories import job_repository, worker_repository
from app.scheduler.recovery import recover_stale_jobs


def _make_queue(db) -> str:
    org = Organization(name="HbOrg", slug=f"hb-org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    project = Project(organization_id=org.id, name="P")
    db.add(project)
    db.flush()
    queue = Queue(project_id=project.id, name="q", concurrency_limit=10)
    db.add(queue)
    db.commit()
    return queue.id


class TestHeartbeats:
    def test_register_worker_sets_initial_heartbeat(self, db):
        worker = worker_repository.register(db, name="w1", hostname="host1", max_concurrency=5)
        assert worker.status == WorkerStatus.IDLE
        assert worker.last_heartbeat_at is not None
        assert worker.current_job_count == 0

    def test_record_heartbeat_updates_worker_and_appends_history(self, db):
        worker = worker_repository.register(db, name="w1", hostname="host1", max_concurrency=5)
        worker_id = worker.id
        first_heartbeat = worker.last_heartbeat_at

        worker_repository.record_heartbeat(
            db, worker_id=worker_id, status=WorkerStatus.BUSY, current_job_count=3
        )

        updated = worker_repository.get_by_id(db, worker_id)
        assert updated.status == WorkerStatus.BUSY
        assert updated.current_job_count == 3
        assert updated.last_heartbeat_at >= first_heartbeat

    def test_mark_stopped(self, db):
        worker = worker_repository.register(db, name="w1", hostname="host1", max_concurrency=5)
        worker_repository.mark_stopped(db, worker_id=worker.id)
        assert worker_repository.get_by_id(db, worker.id).status == WorkerStatus.STOPPED


class TestStaleJobRecovery:
    def test_healthy_worker_jobs_are_untouched(self, db):
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        # last_heartbeat_at is "now" -- not stale.
        recovered = recover_stale_jobs(db, heartbeat_timeout_seconds=30)
        assert recovered == 0

    def test_crashed_worker_jobs_are_requeued(self, db):
        queue_id = _make_queue(db)
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        worker_id = worker.id

        job = Job(
            queue_id=queue_id,
            name="echo",
            job_type=JobType.IMMEDIATE,
            payload={},
            status=JobStatus.RUNNING,
            scheduled_at=datetime.now(timezone.utc),
            claimed_by=worker_id,
            claimed_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        job_id = job.id

        # Simulate the worker having gone silent a while ago.
        db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(last_heartbeat_at=datetime.now(timezone.utc) - timedelta(seconds=120))
        )
        db.commit()

        recovered = recover_stale_jobs(db, heartbeat_timeout_seconds=30)
        assert recovered == 1

        worker_after = worker_repository.get_by_id(db, worker_id)
        assert worker_after.status == WorkerStatus.UNHEALTHY

        job_after = job_repository.get_by_id(db, job_id)
        assert job_after.status == JobStatus.QUEUED
        assert job_after.claimed_by is None
        assert job_after.claimed_at is None

    def test_recovered_job_is_claimable_again(self, db):
        queue_id = _make_queue(db)
        crashed_worker = worker_repository.register(db, name="crashed", hostname="h", max_concurrency=5)
        crashed_worker_id = crashed_worker.id

        job = Job(
            queue_id=queue_id,
            name="echo",
            job_type=JobType.IMMEDIATE,
            payload={},
            status=JobStatus.CLAIMED,
            scheduled_at=datetime.now(timezone.utc),
            claimed_by=crashed_worker_id,
            claimed_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()

        db.execute(
            update(Worker)
            .where(Worker.id == crashed_worker_id)
            .values(last_heartbeat_at=datetime.now(timezone.utc) - timedelta(seconds=120))
        )
        db.commit()

        recover_stale_jobs(db, heartbeat_timeout_seconds=30)

        new_worker = worker_repository.register(db, name="fresh", hostname="h", max_concurrency=5)
        claimed = job_repository.claim_jobs(db, worker_id=new_worker.id, max_jobs=10)
        assert len(claimed) == 1
        assert claimed[0].id == job.id
        assert claimed[0].claimed_by == new_worker.id

    def test_already_stopped_worker_not_marked_unhealthy(self, db):
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        worker_id = worker.id
        worker_repository.mark_stopped(db, worker_id=worker_id)

        db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(last_heartbeat_at=datetime.now(timezone.utc) - timedelta(seconds=120))
        )
        db.commit()

        recover_stale_jobs(db, heartbeat_timeout_seconds=30)
        # A cleanly-stopped worker shouldn't flip to UNHEALTHY -- it's
        # expected to be offline.
        assert worker_repository.get_by_id(db, worker_id).status == WorkerStatus.STOPPED
