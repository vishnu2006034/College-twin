import os
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import db as database
from app.auth import hasher, limiter, require_planner
from app.config import settings
from app.generator import GeneratorConfig, content_hash, generate
from app.loader import load_dataset
from app.main import app
from app.schema import auth_session, edition, room, student, user

pytestmark = pytest.mark.integration


@pytest.fixture
def pg(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Refusing integration tests outside a dedicated *_test database")
    admin = create_engine(url)
    schema = "test_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
    monkeypatch.setattr(database, "engine", lambda: engine)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")
    settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    yield engine
    app.dependency_overrides.clear()
    settings.cache_clear()
    engine.dispose()
    with admin.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.fixture
def small():
    return generate(GeneratorConfig(weeks=1, students_per_section=2))


def test_migration_upgrade_downgrade_replay(pg):
    config = Config("alembic.ini")
    command.check(config)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(edition)) == 0


def test_atomic_idempotent_load_and_freeze(pg, small):
    assert load_dataset(pg, small)
    assert not load_dataset(pg, small)
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(student)) == 16
    with pytest.raises(DBAPIError, match="immutable"), pg.begin() as conn:
        conn.execute(room.update().values(capacity=99))
    with pytest.raises(DBAPIError, match="immutable"), pg.begin() as conn:
        conn.execute(edition.delete())


def test_database_failure_rolls_back_entire_import(pg, small):
    bad = deepcopy(small)
    # This SQL-only uniqueness violation occurs after earlier domain tables were inserted.
    bad["tables"]["room"][1]["code"] = bad["tables"]["room"][0]["code"]
    bad["edition"]["logical_content_hash"] = content_hash(bad["tables"])
    with pytest.raises(IntegrityError):
        load_dataset(pg, bad)
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(edition)) == 0
        assert conn.scalar(select(func.count()).select_from(student)) == 0


def test_database_rejects_cross_edition_foreign_key(pg, small):
    load_dataset(pg, small)
    second = dict(small["edition"], id=uuid4())
    with pg.begin() as conn:
        conn.execute(edition.insert().values(**second))
    foreign_student = dict(small["tables"]["student"][0], id=uuid4(), edition_id=second["id"])
    with pytest.raises(IntegrityError), pg.begin() as conn:
        conn.execute(student.insert().values(**foreign_student))


@pytest.fixture
def client(pg, small):
    load_dataset(pg, small)
    with pg.begin() as conn:
        conn.execute(
            user.insert(),
            [
                dict(
                    id=uuid4(),
                    username=role,
                    role=role,
                    password_hash=hasher.hash("test-only-long-password"),
                )
                for role in ("planner", "viewer")
            ],
        )
    limiter.attempts.clear()
    with TestClient(app) as client:
        yield client


def login(client, role="planner"):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://testserver"},
        json={"username": role, "password": "test-only-long-password"},
    )


def test_login_read_logout_csrf_and_errors(client):
    assert client.get("/api/v1/health").status_code == 200
    response = client.get("/api/v1/datasets")
    assert response.status_code == 401
    assert response.json()["request_id"]
    signed_in = login(client)
    assert signed_in.status_code == 200
    assert any(
        "twin_session=" in cookie and "HttpOnly" in cookie
        for cookie in signed_in.headers.get_list("set-cookie")
    )
    datasets = client.get("/api/v1/datasets").json()
    assert datasets["total"] == 1
    result = client.get(
        "/api/v1/rooms", params={"edition_id": datasets["items"][0]["id"], "limit": 2}
    ).json()
    assert result["total"] == 12 and len(result["items"]) == 2
    assert client.get("/api/v1/rooms?edition_id=invalid").status_code == 422
    assert client.get("/api/v1/datasets?limit=201").status_code == 422
    assert (
        client.post("/api/v1/auth/logout", headers={"Origin": "http://testserver"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://testserver", "X-CSRF-Token": client.cookies["twin_csrf"]},
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me").status_code == 401


def test_auth_failure_origin_validation_and_expired_session(client, pg):
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "planner", "password": "wrong"}
        ).status_code
        == 403
    )
    headers = {"Origin": "http://testserver"}
    result = client.post(
        "/api/v1/auth/login", headers=headers, json={"username": "planner", "password": ""}
    )
    assert result.status_code == 422 and "input" not in result.text
    assert (
        client.post(
            "/api/v1/auth/login", headers=headers, json={"username": "missing", "password": "wrong"}
        ).status_code
        == 401
    )
    login(client)
    with pg.begin() as conn:
        conn.execute(
            auth_session.update().values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert client.get("/api/v1/datasets").status_code == 401


def test_roles_without_adding_future_domain_endpoints(client, pg):
    # Exercise the authorization dependency on a temporary test-only route.
    @app.post("/test-planner")
    def restricted(actor=Depends(require_planner)):
        return {"role": actor["role"]}

    try:
        login(client, "viewer")
        headers = {"Origin": "http://testserver", "X-CSRF-Token": client.cookies["twin_csrf"]}
        assert client.post("/test-planner", headers=headers).status_code == 403
        assert client.get("/api/v1/datasets").status_code == 200
        login(client)
        headers["X-CSRF-Token"] = client.cookies["twin_csrf"]
        assert client.post("/test-planner", headers=headers).status_code == 200
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", "") != "/test-planner"
        ]


def test_login_rate_limit(client):
    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://testserver"},
            json={"username": "planner", "password": "wrong"},
        )
        assert response.status_code == 401
    assert login(client).status_code == 429
