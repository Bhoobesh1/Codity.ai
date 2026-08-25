class TestAuth:
    def test_register_success(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "supersecret123", "full_name": "New User"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == "new@example.com"
        assert body["is_active"] is True
        # Password must never come back in the response.
        assert "password" not in body
        assert "hashed_password" not in body

    def test_register_duplicate_email_returns_409(self, client):
        payload = {"email": "dup@example.com", "password": "supersecret123", "full_name": "A"}
        r1 = client.post("/auth/register", json=payload)
        assert r1.status_code == 201

        r2 = client.post("/auth/register", json=payload)
        assert r2.status_code == 409
        assert r2.json()["error"]["code"] == "conflict"

    def test_register_rejects_short_password(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "short@example.com", "password": "abc", "full_name": "A"},
        )
        assert r.status_code == 422

    def test_register_rejects_invalid_email(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "supersecret123", "full_name": "A"},
        )
        assert r.status_code == 422

    def test_login_success_returns_token(self, client):
        client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "supersecret123", "full_name": "A"},
        )
        r = client.post(
            "/auth/login", json={"email": "login@example.com", "password": "supersecret123"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    def test_login_wrong_password_returns_401(self, client):
        client.post(
            "/auth/register",
            json={"email": "wrongpw@example.com", "password": "supersecret123", "full_name": "A"},
        )
        r = client.post(
            "/auth/login", json={"email": "wrongpw@example.com", "password": "totally-wrong"}
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthorized"

    def test_login_nonexistent_user_returns_401(self, client):
        r = client.post(
            "/auth/login", json={"email": "ghost@example.com", "password": "whatever123"}
        )
        assert r.status_code == 401

    def test_protected_endpoint_without_token_returns_401(self, client):
        r = client.get("/organizations")
        assert r.status_code == 401

    def test_protected_endpoint_with_garbage_token_returns_401(self, client):
        r = client.get("/organizations", headers={"Authorization": "Bearer not-a-real-token"})
        assert r.status_code == 401

    def test_protected_endpoint_with_valid_token_succeeds(self, client, alice_headers):
        r = client.get("/organizations", headers=alice_headers)
        assert r.status_code == 200
