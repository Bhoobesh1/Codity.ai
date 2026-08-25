"""
Test fixtures.

Isolation strategy: each test runs inside its own DB transaction that's
rolled back at the end, so tests never see each other's data and we don't
pay the cost of recreating tables between tests. This is the standard
pattern for testing against a real relational database.

Requires a real Postgres test database (see TEST_DATABASE_URL below) --
we deliberately don't use SQLite here because a couple of columns use
Postgres-specific JSONB, and because the whole point of Phase 2+ testing
(atomic claiming, row locking) requires real Postgres semantics anyway.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 -- registers all models on Base.metadata
from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://scheduler_user:scheduler_pass@localhost:5432/job_scheduler_test",
)


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def register_and_login(client):
    """Returns a helper that registers + logs in a user, returning auth headers."""

    def _do(email: str, password: str = "supersecret123", full_name: str = "Test User") -> dict:
        r = client.post(
            "/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _do


@pytest.fixture()
def alice_headers(register_and_login):
    return register_and_login("alice@example.com")


@pytest.fixture()
def bob_headers(register_and_login):
    return register_and_login("bob@example.com")


@pytest.fixture()
def alice_org(client, alice_headers) -> str:
    r = client.post("/organizations", json={"name": "Acme Inc"}, headers=alice_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture()
def alice_project(client, alice_headers, alice_org) -> str:
    r = client.post(
        "/projects",
        json={"organization_id": alice_org, "name": "Email Pipeline", "description": "desc"},
        headers=alice_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture()
def alice_queue(client, alice_headers, alice_project) -> str:
    r = client.post(
        f"/projects/{alice_project}/queues",
        json={
            "name": "test-queue",
            "concurrency_limit": 10,
            "retry_policy": {"strategy": "fixed", "base_delay_seconds": 1, "max_retries": 5},
        },
        headers=alice_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture()
def live_db(db_engine):
    """
    A session bound directly to the engine, with NO wrapping transaction
    -- every commit is real and visible to other connections. Needed for
    tests that spin up multiple simultaneous DB sessions to simulate
    multiple worker processes racing to claim jobs; the transactional
    `db` fixture above can't be used for that because SKIP LOCKED only
    does anything meaningful across genuinely separate, concurrently
    committing transactions.

    Cleans up after itself by truncating every table, since nothing here
    gets rolled back automatically.
    """
    from sqlalchemy.orm import sessionmaker

    LiveSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = LiveSessionLocal()
    yield session
    session.close()

    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
