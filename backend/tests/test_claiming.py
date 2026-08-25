"""
Tests atomic job claiming under real concurrency.

These use the `live_db` fixture (real commits, no wrapping/rollback
transaction) and open several genuinely separate DB sessions
concurrently, because SKIP LOCKED's guarantees only mean something
across distinct, simultaneously-committing transactions -- a single
transactional test session (as used elsewhere in this suite) can't
exercise that.

Data is set up directly via the ORM (not the HTTP API) to keep these
tests focused purely on the claiming mechanism, independent of auth.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from app.models.base import JobStatus, JobType
from app.models.job import Job
from app.models.project import Project
from app.models.queue import Queue
from app.models.retry_policy import RetryPolicy
from app.models.user import Organization
from app.models.worker import Worker
from app.repositories import job_repository, worker_repository


def _make_queue(db, *, concurrency_limit: int = 1000, is_paused: bool = False) -> str:
    org = Organization(name="ConcOrg", slug=f"conc-org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    project = Project(organization_id=org.id, name="P")
    db.add(project)
    db.flush()
    policy = RetryPolicy(name="p", base_delay_seconds=1, max_delay_seconds=60, max_retries=3)
    db.add(policy)
    db.flush()
    queue = Queue(
        project_id=project.id,
        name="q",
        concurrency_limit=concurrency_limit,
        is_paused=is_paused,
        retry_policy_id=policy.id,
    )
    db.add(queue)
    db.commit()
    return queue.id


def _make_jobs(db, *, queue_id: str, count: int) -> set[str]:
    now = datetime.now(timezone.utc)
    ids = set()
    for i in range(count):
        job = Job(
            queue_id=queue_id,
            name="echo",
            job_type=JobType.IMMEDIATE,
            payload={"i": i},
            status=JobStatus.QUEUED,
            scheduled_at=now,
        )
        db.add(job)
        db.flush()
        ids.add(job.id)
    db.commit()
    return ids


class TestConcurrentClaiming:
    def test_no_double_claims_across_concurrent_workers(self, live_db, db_engine):
        queue_id = _make_queue(live_db)
        job_ids = _make_jobs(live_db, queue_id=queue_id, count=30)

        worker_ids = []
        for i in range(5):
            w = worker_repository.register(
                live_db, name=f"worker-{i}", hostname="h", max_concurrency=100
            )
            worker_ids.append(w.id)

        LiveSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

        def claim_attempt(worker_id: str) -> list[str]:
            session = LiveSession()
            try:
                claimed = job_repository.claim_jobs(session, worker_id=worker_id, max_jobs=30)
                return [j.id for j in claimed]
            finally:
                session.close()

        all_claimed: dict[str, str] = {}
        for _ in range(10):  # enough rounds to drain everything
            if len(all_claimed) >= len(job_ids):
                break
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(claim_attempt, wid): wid for wid in worker_ids}
                for future in as_completed(futures):
                    wid = futures[future]
                    for jid in future.result():
                        assert jid not in all_claimed, (
                            f"DOUBLE CLAIM: job {jid} claimed by both "
                            f"{all_claimed[jid]} and {wid}"
                        )
                        all_claimed[jid] = wid

        assert len(all_claimed) == len(job_ids), "not every job was claimed"
        assert set(all_claimed.keys()) == job_ids

        # Verify DB state agrees with what each thread observed.
        for jid, expected_worker in all_claimed.items():
            job = job_repository.get_by_id(live_db, jid)
            assert job.status == JobStatus.CLAIMED
            assert job.claimed_by == expected_worker

    def test_concurrency_limit_is_respected_under_load(self, live_db, db_engine):
        queue_id = _make_queue(live_db, concurrency_limit=3)
        job_ids = _make_jobs(live_db, queue_id=queue_id, count=10)

        worker = worker_repository.register(live_db, name="w", hostname="h", max_concurrency=100)

        claimed = job_repository.claim_jobs(live_db, worker_id=worker.id, max_jobs=10)
        assert len(claimed) == 3, "should only claim up to the queue's concurrency_limit"

        # No more claimable until something finishes (still CLAIMED, not COMPLETED).
        claimed_again = job_repository.claim_jobs(live_db, worker_id=worker.id, max_jobs=10)
        assert claimed_again == []

    def test_paused_queue_yields_no_claims(self, live_db):
        queue_id = _make_queue(live_db, is_paused=True)
        _make_jobs(live_db, queue_id=queue_id, count=5)
        worker = worker_repository.register(live_db, name="w", hostname="h", max_concurrency=10)

        claimed = job_repository.claim_jobs(live_db, worker_id=worker.id, max_jobs=10)
        assert claimed == []

    def test_future_scheduled_jobs_not_claimed_early(self, live_db):
        queue_id = _make_queue(live_db)
        job = Job(
            queue_id=queue_id,
            name="echo",
            job_type=JobType.DELAYED,
            payload={},
            status=JobStatus.QUEUED,
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        live_db.add(job)
        live_db.commit()

        worker = worker_repository.register(live_db, name="w", hostname="h", max_concurrency=10)
        claimed = job_repository.claim_jobs(live_db, worker_id=worker.id, max_jobs=10)
        assert claimed == []
