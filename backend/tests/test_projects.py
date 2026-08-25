class TestOrganizations:
    def test_create_organization_makes_creator_owner(self, client, alice_headers):
        r = client.post("/organizations", json={"name": "Acme Inc"}, headers=alice_headers)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Acme Inc"
        assert body["slug"] == "acme-inc"
        assert body["role"] == "owner"

    def test_duplicate_name_gets_unique_slug(self, client, alice_headers, bob_headers):
        r1 = client.post("/organizations", json={"name": "Acme Inc"}, headers=alice_headers)
        r2 = client.post("/organizations", json={"name": "Acme Inc"}, headers=bob_headers)
        assert r1.json()["slug"] == "acme-inc"
        assert r2.json()["slug"] == "acme-inc-2"

    def test_list_organizations_only_shows_own(self, client, alice_headers, bob_headers):
        client.post("/organizations", json={"name": "Alice Org"}, headers=alice_headers)
        client.post("/organizations", json={"name": "Bob Org"}, headers=bob_headers)

        r = client.get("/organizations", headers=alice_headers)
        assert r.status_code == 200
        names = [o["name"] for o in r.json()]
        assert names == ["Alice Org"]


class TestProjects:
    def test_create_and_get_project(self, client, alice_headers, alice_org):
        r = client.post(
            "/projects",
            json={"organization_id": alice_org, "name": "My Project", "description": "d"},
            headers=alice_headers,
        )
        assert r.status_code == 201
        project_id = r.json()["id"]

        r = client.get(f"/projects/{project_id}", headers=alice_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "My Project"

    def test_create_project_in_org_you_dont_belong_to_is_forbidden(
        self, client, alice_headers, bob_headers, alice_org
    ):
        r = client.post(
            "/projects",
            json={"organization_id": alice_org, "name": "Sneaky", "description": None},
            headers=bob_headers,
        )
        assert r.status_code == 403

    def test_other_user_cannot_see_project(self, client, alice_headers, bob_headers, alice_project):
        r = client.get(f"/projects/{alice_project}", headers=bob_headers)
        assert r.status_code == 404

    def test_get_nonexistent_project_returns_404(self, client, alice_headers):
        r = client.get("/projects/does-not-exist", headers=alice_headers)
        assert r.status_code == 404

    def test_list_projects_paginated(self, client, alice_headers, alice_org):
        for i in range(3):
            client.post(
                "/projects",
                json={"organization_id": alice_org, "name": f"Project {i}", "description": None},
                headers=alice_headers,
            )
        r = client.get("/projects", params={"page": 1, "page_size": 2}, headers=alice_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert body["pages"] == 2
        assert len(body["items"]) == 2

    def test_update_project(self, client, alice_headers, alice_project):
        r = client.put(
            f"/projects/{alice_project}",
            json={"description": "new description"},
            headers=alice_headers,
        )
        assert r.status_code == 200
        assert r.json()["description"] == "new description"

    def test_other_user_cannot_update_project(self, client, bob_headers, alice_project):
        r = client.put(
            f"/projects/{alice_project}", json={"name": "hacked"}, headers=bob_headers
        )
        assert r.status_code == 404

    def test_delete_project(self, client, alice_headers, alice_project):
        r = client.delete(f"/projects/{alice_project}", headers=alice_headers)
        assert r.status_code == 204

        r = client.get(f"/projects/{alice_project}", headers=alice_headers)
        assert r.status_code == 404
