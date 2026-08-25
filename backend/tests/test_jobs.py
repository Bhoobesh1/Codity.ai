class TestJobCreation:
    def test_create_immediate_job(self, client, alice_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {"x": 1}},
            headers=alice_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "queued"
        assert body["job_type"] == "immediate"
        assert body["retry_count"] == 0

    def test_create_delayed_job_sets_future_scheduled_at(self, client, alice_headers, alice_queue):
        before = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        ).json()["scheduled_at"]

        r = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "delayed", "payload": {}, "delay_seconds": 3600},
            headers=alice_headers,
        )
        assert r.status_code == 201
        assert r.json()["scheduled_at"] > before

    def test_delayed_job_without_delay_seconds_is_rejected(self, client, alice_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "delayed", "payload": {}},
            headers=alice_headers,
        )
        assert r.status_code == 422

    def test_scheduled_job_without_scheduled_at_is_rejected(self, client, alice_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "scheduled", "payload": {}},
            headers=alice_headers,
        )
        assert r.status_code == 422

    def test_other_user_cannot_create_job_in_your_queue(self, client, bob_headers, alice_queue):
        r = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=bob_headers,
        )
        assert r.status_code == 404


class TestJobRetrieval:
    def test_get_job(self, client, alice_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        r = client.get(f"/jobs/{job_id}", headers=alice_headers)
        assert r.status_code == 200
        assert r.json()["id"] == job_id

    def test_other_user_cannot_see_your_job(self, client, alice_headers, bob_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        r = client.get(f"/jobs/{job_id}", headers=bob_headers)
        assert r.status_code == 404

    def test_list_jobs_filter_by_status(self, client, alice_headers, alice_queue):
        for _ in range(3):
            client.post(
                f"/queues/{alice_queue}/jobs",
                json={"name": "echo", "job_type": "immediate", "payload": {}},
                headers=alice_headers,
            )
        r = client.get(
            f"/queues/{alice_queue}/jobs", params={"status": "queued"}, headers=alice_headers
        )
        assert r.status_code == 200
        assert r.json()["total"] == 3

        r = client.get(
            f"/queues/{alice_queue}/jobs", params={"status": "completed"}, headers=alice_headers
        )
        assert r.json()["total"] == 0

    def test_job_executions_empty_before_running(self, client, alice_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        r = client.get(f"/jobs/{job_id}/executions", headers=alice_headers)
        assert r.status_code == 200
        assert r.json() == []


class TestManualRetry:
    def test_cannot_retry_a_job_that_isnt_in_dlq(self, client, alice_headers, alice_queue):
        job_id = client.post(
            f"/queues/{alice_queue}/jobs",
            json={"name": "echo", "job_type": "immediate", "payload": {}},
            headers=alice_headers,
        ).json()["id"]

        r = client.post(f"/jobs/{job_id}/retry", headers=alice_headers)
        assert r.status_code == 409
