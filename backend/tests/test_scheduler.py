from datetime import datetime, timedelta, timezone

from app.models.base import JobStatus
from app.repositories import job_repository
from app.services.scheduled_job_service import run_scheduler_tick


class TestScheduledJobCreation:
    def test_create_scheduled_job(self, client, alice_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "nightly-cleanup", "cron_expression": "0 2 * * *", "payload": {"x": 1}},
            headers=alice_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["is_active"] is True
        assert body["next_run_at"] is not None
        assert body["last_run_at"] is None

    def test_invalid_cron_expression_rejected(self, client, alice_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "bad", "cron_expression": "not a cron", "payload": {}},
            headers=alice_headers,
        )
        assert r.status_code == 422

    def test_other_user_cannot_create_scheduled_job_in_your_queue(
        self, client, bob_headers, alice_queue
    ):
        r = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "sneaky", "cron_expression": "* * * * *", "payload": {}},
            headers=bob_headers,
        )
        assert r.status_code == 404

    def test_list_scheduled_jobs(self, client, alice_headers, alice_queue):
        client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "a", "cron_expression": "0 * * * *", "payload": {}},
            headers=alice_headers,
        )
        client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "b", "cron_expression": "0 0 * * *", "payload": {}},
            headers=alice_headers,
        )
        r = client.get(f"/queues/{alice_queue}/scheduled-jobs", headers=alice_headers)
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_pause_and_resume_scheduled_job(self, client, alice_headers, alice_queue):
        sid = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "a", "cron_expression": "0 * * * *", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        r = client.post(f"/scheduled-jobs/{sid}/pause", headers=alice_headers)
        assert r.status_code == 200 and r.json()["is_active"] is False

        r = client.post(f"/scheduled-jobs/{sid}/resume", headers=alice_headers)
        assert r.status_code == 200 and r.json()["is_active"] is True


class TestSchedulerTick:
    def test_tick_spawns_job_for_due_template(self, client, db, alice_headers, alice_queue):
        sid = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "every-minute", "cron_expression": "* * * * *", "payload": {"k": "v"}},
            headers=alice_headers,
        ).json()["id"]

        from app.repositories import scheduled_job_repository

        template = scheduled_job_repository.get_by_id(db, sid)
        template.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        spawned = run_scheduler_tick(db)
        assert spawned == 1

        r = client.get(
            f"/queues/{alice_queue}/jobs", params={"status": "queued"}, headers=alice_headers
        )
        jobs = r.json()["items"]
        assert any(j["job_type"] == "recurring" and j["payload"] == {"k": "v"} for j in jobs)

    def test_tick_advances_next_run_at(self, client, db, alice_headers, alice_queue):
        sid = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "every-minute", "cron_expression": "* * * * *", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        from app.repositories import scheduled_job_repository

        template = scheduled_job_repository.get_by_id(db, sid)
        template.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        run_scheduler_tick(db)

        template = scheduled_job_repository.get_by_id(db, sid)
        assert template.last_run_at is not None
        assert template.next_run_at > datetime.now(timezone.utc)

    def test_paused_template_not_spawned(self, client, db, alice_headers, alice_queue):
        sid = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "every-minute", "cron_expression": "* * * * *", "payload": {}},
            headers=alice_headers,
        ).json()["id"]
        client.post(f"/scheduled-jobs/{sid}/pause", headers=alice_headers)

        from app.repositories import scheduled_job_repository

        template = scheduled_job_repository.get_by_id(db, sid)
        template.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        spawned = run_scheduler_tick(db)
        assert spawned == 0

    def test_spawned_job_is_claimable(self, client, db, alice_headers, alice_queue):
        sid = client.post(
            f"/queues/{alice_queue}/scheduled-jobs",
            json={"name": "echo", "cron_expression": "* * * * *", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        from app.repositories import scheduled_job_repository, worker_repository

        template = scheduled_job_repository.get_by_id(db, sid)
        template.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        run_scheduler_tick(db)

        worker = worker_repository.register(db, name="w", hostname="h", max_concurrency=5)
        claimed = job_repository.claim_jobs(db, worker_id=worker.id, max_jobs=10)
        assert len(claimed) == 1
        assert claimed[0].status == JobStatus.CLAIMED
