class TestQueues:
    def test_create_queue_with_default_retry_policy(self, client, alice_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues",
            json={"name": "emails", "priority": 5, "concurrency_limit": 2},
            headers=alice_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "emails"
        assert body["is_paused"] is False
        assert body["retry_policy"]["strategy"] == "exponential"
        assert body["retry_policy"]["max_retries"] == 5

    def test_create_queue_with_custom_retry_policy(self, client, alice_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues",
            json={
                "name": "webhooks",
                "retry_policy": {
                    "strategy": "linear",
                    "base_delay_seconds": 10,
                    "max_retries": 3,
                },
            },
            headers=alice_headers,
        )
        assert r.status_code == 201
        assert r.json()["retry_policy"]["strategy"] == "linear"
        assert r.json()["retry_policy"]["max_retries"] == 3

    def test_other_user_cannot_create_queue_in_your_project(
        self, client, bob_headers, alice_project
    ):
        r = client.post(
            f"/projects/{alice_project}/queues", json={"name": "sneaky"}, headers=bob_headers
        )
        assert r.status_code == 404

    def test_pause_and_resume_queue(self, client, alice_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues", json={"name": "q1"}, headers=alice_headers
        )
        queue_id = r.json()["id"]
        assert r.json()["is_paused"] is False

        r = client.post(f"/queues/{queue_id}/pause", headers=alice_headers)
        assert r.status_code == 200
        assert r.json()["is_paused"] is True

        # Verify it persisted, not just returned in the response.
        r = client.get(f"/queues/{queue_id}", headers=alice_headers)
        assert r.json()["is_paused"] is True

        r = client.post(f"/queues/{queue_id}/resume", headers=alice_headers)
        assert r.status_code == 200
        assert r.json()["is_paused"] is False

    def test_other_user_cannot_pause_your_queue(self, client, alice_headers, bob_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues", json={"name": "q1"}, headers=alice_headers
        )
        queue_id = r.json()["id"]

        r = client.post(f"/queues/{queue_id}/pause", headers=bob_headers)
        assert r.status_code == 404

        # Confirm it's actually still unpaused.
        r = client.get(f"/queues/{queue_id}", headers=alice_headers)
        assert r.json()["is_paused"] is False

    def test_queue_stats_start_at_zero(self, client, alice_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues", json={"name": "q1"}, headers=alice_headers
        )
        queue_id = r.json()["id"]

        r = client.get(f"/queues/{queue_id}/stats", headers=alice_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total_jobs"] == 0
        assert body["completed"] == 0

    def test_list_queues_filter_by_paused(self, client, alice_headers, alice_project):
        r1 = client.post(
            f"/projects/{alice_project}/queues", json={"name": "active-q"}, headers=alice_headers
        )
        r2 = client.post(
            f"/projects/{alice_project}/queues", json={"name": "paused-q"}, headers=alice_headers
        )
        client.post(f"/queues/{r2.json()['id']}/pause", headers=alice_headers)

        r = client.get(
            f"/projects/{alice_project}/queues",
            params={"is_paused": "true"},
            headers=alice_headers,
        )
        assert r.status_code == 200
        names = [q["name"] for q in r.json()["items"]]
        assert names == ["paused-q"]

    def test_update_queue_concurrency_limit(self, client, alice_headers, alice_project):
        r = client.post(
            f"/projects/{alice_project}/queues",
            json={"name": "q1", "concurrency_limit": 5},
            headers=alice_headers,
        )
        queue_id = r.json()["id"]

        r = client.put(
            f"/queues/{queue_id}", json={"concurrency_limit": 20}, headers=alice_headers
        )
        assert r.status_code == 200
        assert r.json()["concurrency_limit"] == 20
