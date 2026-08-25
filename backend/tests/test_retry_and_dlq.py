from datetime import datetime, timezone

from app.models.base import JobStatus
from app.repositories import job_repository, worker_repository
from app.workers.executor import execute_job


class TestRetryAndDeadLetterQueue:
    def _register_worker(self, db):
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        return worker.id

    def test_successful_job_completes_on_first_try(self, client, db, alice_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}, "max_retries": 3},
            headers=alice_headers,
        ).json()["id"]

        worker_id = self._register_worker(db)
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        assert len(claimed) == 1
        execute_job(db, job=claimed[0], worker_id=worker_id)

        r = client.get(f"/jobs/{job_id}", headers=alice_headers)
        assert r.json()["status"] == "completed"

        executions = client.get(f"/jobs/{job_id}/executions", headers=alice_headers).json()
        assert len(executions) == 1
        assert executions[0]["status"] == "succeeded"

    def test_failing_job_retries_then_reaches_dead_letter_queue(
        self, client, db, alice_headers, alice_queue
    ):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={
                "name": "always_fail",
                "job_type": "immediate",
                "payload": {},
                "max_retries": 2,
            },
            headers=alice_headers,
        ).json()["id"]

        worker_id = self._register_worker(db)

        # Attempt 0: fails, requeued with a future scheduled_at (retry backoff).
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        assert len(claimed) == 1
        execute_job(db, job=claimed[0], worker_id=worker_id)

        job = job_repository.get_by_id(db, job_id)
        assert job.status == JobStatus.QUEUED
        assert job.retry_count == 1
        assert job.scheduled_at > datetime.now(timezone.utc), (
            "retry should be scheduled into the future per the backoff policy"
        )

        # Not claimable yet -- it's not due.
        assert job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10) == []

        # Force it due now (simulating time passing) for attempt 1.
        job.scheduled_at = datetime.now(timezone.utc)
        db.commit()
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        assert len(claimed) == 1
        execute_job(db, job=claimed[0], worker_id=worker_id)

        job = job_repository.get_by_id(db, job_id)
        assert job.status == JobStatus.QUEUED
        assert job.retry_count == 2

        # Attempt 2 (the last one, max_retries=2) -> exhausted -> DLQ.
        job.scheduled_at = datetime.now(timezone.utc)
        db.commit()
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        assert len(claimed) == 1
        execute_job(db, job=claimed[0], worker_id=worker_id)

        r = client.get(f"/jobs/{job_id}", headers=alice_headers)
        assert r.json()["status"] == "dead_letter"
        assert r.json()["retry_count"] == 2

        executions = client.get(f"/jobs/{job_id}/executions", headers=alice_headers).json()
        assert len(executions) == 3
        assert all(e["status"] == "failed" for e in executions)

    def test_manual_retry_resets_dlq_job(self, client, db, alice_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "always_fail", "job_type": "immediate", "payload": {}, "max_retries": 0},
            headers=alice_headers,
        ).json()["id"]

        worker_id = self._register_worker(db)
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        execute_job(db, job=claimed[0], worker_id=worker_id)

        assert client.get(f"/jobs/{job_id}", headers=alice_headers).json()["status"] == "dead_letter"

        r = client.post(f"/jobs/{job_id}/retry", headers=alice_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "queued"
        assert r.json()["retry_count"] == 0

        # It's claimable again now.
        claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
        assert len(claimed) == 1
        assert claimed[0].id == job_id

    def test_flaky_job_succeeds_after_configured_failures(
        self, client, db, alice_headers, alice_queue
    ):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={
                "name": "flaky",
                "job_type": "immediate",
                "payload": {"fail_until": 2},
                "max_retries": 5,
            },
            headers=alice_headers,
        ).json()["id"]

        worker_id = self._register_worker(db)
        for _ in range(3):
            job = job_repository.get_by_id(db, job_id)
            job.scheduled_at = datetime.now(timezone.utc)
            db.commit()
            claimed = job_repository.claim_jobs(db, worker_id=worker_id, max_jobs=10)
            if not claimed:
                break
            execute_job(db, job=claimed[0], worker_id=worker_id)

        r = client.get(f"/jobs/{job_id}", headers=alice_headers)
        assert r.json()["status"] == "completed"
        assert r.json()["retry_count"] == 2
