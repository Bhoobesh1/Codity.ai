from app.repositories import job_repository, worker_repository
from app.workers.executor import execute_job


class TestDashboardMetrics:
    def test_metrics_start_at_zero_for_new_user(self, client, alice_headers):
        r = client.get("/metrics/dashboard", headers=alice_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total_jobs"] == 0
        assert body["completed_jobs"] == 0
        assert body["average_execution_time_ms"] is None

    def test_metrics_count_jobs_by_status(self, client, db, alice_headers, alice_queue):
        client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        )
        client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        )

        r = client.get("/metrics/dashboard", headers=alice_headers)
        assert r.json()["total_jobs"] == 2

        # Run one to completion.
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        claimed = job_repository.claim_jobs(db, worker_id=worker.id, max_jobs=1)
        execute_job(db, job=claimed[0], worker_id=worker.id)

        r = client.get("/metrics/dashboard", headers=alice_headers)
        body = r.json()
        assert body["completed_jobs"] == 1
        assert body["average_execution_time_ms"] is not None

    def test_metrics_only_include_own_organizations_data(
        self, client, alice_headers, bob_headers, alice_queue
    ):
        client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        )

        r = client.get("/metrics/dashboard", headers=bob_headers)
        assert r.json()["total_jobs"] == 0, "bob should not see alice's job counts"

        r = client.get("/metrics/dashboard", headers=alice_headers)
        assert r.json()["total_jobs"] == 1

    def test_metrics_include_dead_letter_and_worker_counts(
        self, client, db, alice_headers, alice_queue
    ):
        client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "always_fail", "job_type": "immediate", "payload": {}, "max_retries": 0},
            headers=alice_headers,
        )
        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        claimed = job_repository.claim_jobs(db, worker_id=worker.id, max_jobs=1)
        execute_job(db, job=claimed[0], worker_id=worker.id)

        r = client.get("/metrics/dashboard", headers=alice_headers)
        body = r.json()
        assert body["dead_letter_jobs"] == 1
        assert body["total_workers"] >= 1
