import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import LoginLimiter, digest, hasher, require_csrf, require_planner, verify_password
from app.config import settings
from app.db import get_db
from app.main import app


@pytest.fixture(autouse=True)
def configuration(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused@localhost/unused")
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")
    settings.cache_clear()
    app.dependency_overrides[get_db] = lambda: None
    yield
    app.dependency_overrides.clear()
    settings.cache_clear()


def test_password_hash_verification():
    encoded = hasher.hash("test-only-password")
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, "test-only-password")
    assert not verify_password(encoded, "wrong")


def test_unauthenticated_reads_and_origin_rejected_without_database_access():
    with TestClient(app) as client:
        result = client.get("/api/v1/datasets")
        assert result.status_code == 401
        assert result.json()["request_id"] == result.headers["X-Request-ID"]
        assert (
            client.post(
                "/api/v1/auth/login", json={"username": "planner", "password": "secret"}
            ).status_code
            == 403
        )


def test_validation_does_not_echo_password():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://testserver"},
            json={"username": "invalid name", "password": "do-not-echo-this"},
        )
        assert response.status_code == 422
        assert "do-not-echo-this" not in response.text
        assert "input" not in response.json()["field_errors"][0]


def test_role_and_csrf_guards():
    actor = {"role": "viewer", "csrf_hash": digest("valid-token")}
    request = Request(
        {
            "type": "http",
            "headers": [(b"origin", b"http://testserver"), (b"x-csrf-token", b"valid-token")],
        }
    )
    assert require_csrf(request, actor) is actor
    with pytest.raises(HTTPException) as exc:
        require_planner(actor)
    assert exc.value.status_code == 403
    actor["role"] = "planner"
    assert require_planner(actor) is actor
    actor["csrf_hash"] = digest("different-token")
    with pytest.raises(HTTPException):
        require_csrf(request, actor)


def test_login_attempts_are_bounded():
    limiter = LoginLimiter()
    for _ in range(10):
        limiter.check("test-client")
    with pytest.raises(HTTPException) as exc:
        limiter.check("test-client")
    assert exc.value.status_code == 429
