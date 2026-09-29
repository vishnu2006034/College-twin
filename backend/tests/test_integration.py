import os
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi.encoders import jsonable_encoder
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


def snapshot_request(client):
    edition_id = client.get("/api/v1/datasets").json()["items"][0]["id"]
    return dict(
        edition_id=edition_id,
        as_of="2026-01-05T17:00:00+05:30",
        window_start="2026-01-05T00:00:00+05:30",
        window_end="2026-01-06T00:00:00+05:30",
    )


def test_snapshot_persistence_replay_conflict_and_sessions(client, pg):
    from app.schema import snapshot
    from app.state import fingerprint

    login(client)
    body = snapshot_request(client)
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "fixture-1",
    }
    response = client.post("/api/v1/snapshots", json=body, headers=headers)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["metrics"]["scheduled_classes"] == 32
    assert result["anomalies"] == []
    assert client.post("/api/v1/snapshots", json=body, headers=headers).json() == result
    changed = dict(body, as_of="2026-01-05T16:00:00+05:30")
    assert client.post("/api/v1/snapshots", json=changed, headers=headers).status_code == 409
    assert client.get(f"/api/v1/snapshots/{result['id']}").json() == result
    page = client.get(f"/api/v1/snapshots/{result['id']}/sessions?limit=2&offset=1").json()
    assert page["total"] == 32 and len(page["items"]) == 2
    with pg.connect() as conn:
        stored = conn.execute(select(snapshot)).mappings().one()
        assert result["input_hash"] == fingerprint(stored["canonical_inputs"])
    with pytest.raises(DBAPIError, match="immutable"), pg.begin() as conn:
        conn.execute(snapshot.delete())
    login(client, "viewer")
    assert client.get(f"/api/v1/snapshots/{result['id']}").status_code == 200
    headers["X-CSRF-Token"] = client.cookies["twin_csrf"]
    assert client.post("/api/v1/snapshots", json=body, headers=headers).status_code == 403


def test_snapshot_security_and_validation(client):
    assert client.get(f"/api/v1/snapshots/{uuid4()}").status_code == 401
    login(client)
    body = snapshot_request(client)
    assert client.post("/api/v1/snapshots", json=body).status_code == 403
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "validate",
    }
    assert (
        client.post(
            "/api/v1/snapshots", json=dict(body, as_of="2026-01-05T17:00:00"), headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/snapshots", json=dict(body, edition_id=str(uuid4())), headers=headers
        ).status_code
        == 404
    )
    outside = dict(
        body,
        window_start="2027-01-01T00:00:00Z",
        window_end="2027-01-02T00:00:00Z",
        as_of="2027-01-01T12:00:00Z",
    )
    assert client.post("/api/v1/snapshots", json=outside, headers=headers).status_code == 422
    assert client.get(f"/api/v1/snapshots/{uuid4()}").status_code == 404


def test_snapshot_concurrent_retry_is_one_atomic_result(client, pg):
    from concurrent.futures import ThreadPoolExecutor

    from app.schema import audit, snapshot

    login(client)
    body = snapshot_request(client)
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "concurrent",
    }
    cookies = dict(client.cookies)

    def create():
        with TestClient(app) as worker:
            worker.cookies.update(cookies)
            response = worker.post("/api/v1/snapshots", json=body, headers=headers)
            assert response.status_code == 201, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert results[0] == results[1]
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(snapshot)) == 1
        assert (
            conn.scalar(
                select(func.count()).select_from(audit).where(audit.c.action == "snapshot.create")
            )
            == 1
        )


def test_snapshot_audit_failure_rolls_back_snapshot(client, pg):
    from sqlalchemy import event
    from sqlalchemy.exc import SQLAlchemyError

    from app.schema import snapshot

    login(client)
    body = snapshot_request(client)
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "rollback",
    }

    def fail_audit(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO audit_log"):
            raise SQLAlchemyError("Deliberate audit failure")

    event.listen(pg, "before_cursor_execute", fail_audit)
    try:
        assert client.post("/api/v1/snapshots", json=body, headers=headers).status_code == 503
    finally:
        event.remove(pg, "before_cursor_execute", fail_audit)
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(snapshot)) == 0
    assert client.post("/api/v1/snapshots", json=body, headers=headers).status_code == 201


def test_reviewed_room_mapping_validation_isolation_and_revision(client, pg, small):
    from app.mappings import CATALOG
    from app.schema import room_mapping

    login(client)
    edition_id = snapshot_request(client)["edition_id"]
    path = f"/api/v1/room-mappings/{edition_id}"
    initial = client.get(path).json()
    assert initial["version"] == 0 and initial["bindings"] == []
    headers = {"Origin": "http://testserver", "X-CSRF-Token": client.cookies["twin_csrf"]}
    room_id = str(next(r["id"] for r in small["tables"]["room"] if r["kind"] == "classroom"))
    space_id = next(k for k, v in CATALOG.items() if v["kind"] == "classroom")
    body = dict(
        expected_version=0,
        bindings=[dict(space_id=space_id, room_id=room_id)],
        review_note="Synthetic test-only mapping, not a real campus assertion",
    )
    assert client.post(path, json=body).status_code == 403
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 1
    assert client.get(path).json()["bindings"] == body["bindings"]
    assert client.post(path, json=body, headers=headers).status_code == 409
    duplicate = dict(body, expected_version=1, bindings=body["bindings"] * 2)
    assert client.post(path, json=duplicate, headers=headers).status_code == 422
    second = generate(GeneratorConfig(seed=99, weeks=1, students_per_section=2))
    load_dataset(pg, second)
    invalid = dict(
        body,
        expected_version=1,
        bindings=[dict(space_id=space_id, room_id=str(second["tables"]["room"][0]["id"]))],
    )
    assert client.post(path, json=invalid, headers=headers).status_code == 422
    invalid["bindings"][0] = dict(space_id="hall-g-library", room_id=room_id)
    assert client.post(path, json=invalid, headers=headers).status_code == 422
    lab_space = next(k for k, v in CATALOG.items() if v["kind"] == "lab")
    invalid["bindings"][0] = dict(space_id=lab_space, room_id=room_id)
    assert client.post(path, json=invalid, headers=headers).status_code == 422
    assert client.get(f"/api/v1/room-mappings/{second['edition']['id']}").json()["bindings"] == []
    login(client, "viewer")
    headers["X-CSRF-Token"] = client.cookies["twin_csrf"]
    assert client.get(path).status_code == 200
    assert (
        client.post(path, json=dict(body, expected_version=1), headers=headers).status_code == 403
    )
    login(client)
    headers["X-CSRF-Token"] = client.cookies["twin_csrf"]
    cleared = client.post(path, json=dict(body, expected_version=1, bindings=[]), headers=headers)
    assert cleared.status_code == 200 and cleared.json()["version"] == 2
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(room_mapping)) == 1


def test_room_snapshot_uses_saved_inputs_and_keeps_cross_room_conflicts(client, pg):
    from app.schema import snapshot
    from app.state import SnapshotRequest, calculate, fingerprint

    login(client)
    body = snapshot_request(client)
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "room-fixture",
    }
    original = client.post("/api/v1/snapshots", json=body, headers=headers).json()
    with pg.connect() as conn:
        saved = dict(conn.execute(select(snapshot)).mappings().one())
    inputs = deepcopy(saved["canonical_inputs"])
    first = inputs["tables"]["class_session"][0]
    first_room = next(r for r in inputs["tables"]["room"] if r["id"] == first["room_id"])
    other_room = next(
        r
        for r in inputs["tables"]["room"]
        if r["id"] != first_room["id"] and r["kind"] == first_room["kind"]
    )
    duplicate = dict(first, id=str(uuid4()), room_id=other_room["id"])
    inputs["tables"]["class_session"].append(duplicate)
    result = calculate(SnapshotRequest(**inputs["request"]), inputs["tables"])
    inputs["sessions"] = result["sessions"]
    new_id = uuid4()
    response = dict(
        original,
        id=str(new_id),
        input_hash=fingerprint(inputs),
        **{k: result[k] for k in ("metrics", "coverage", "anomalies")},
    )
    with pg.begin() as conn:
        conn.execute(
            snapshot.insert().values(
                **dict(
                    saved,
                    id=new_id,
                    idempotency_key="deliberate-room-fixture",
                    canonical_inputs=inputs,
                    response=response,
                )
            )
        )
    url = f"/api/v1/snapshots/{new_id}"
    room_state = client.get(f"{url}/rooms/{first_room['id']}").json()
    assert room_state["snapshot_id"] == str(new_id)
    assert room_state["input_hash"] == response["input_hash"]
    assert room_state["synthetic_data_only"] is True
    assert room_state["window_start"] == original["window_start"]
    assert any(
        a["rule"] == "faculty_overlap" and duplicate["id"] in a["session_ids"]
        for a in room_state["anomalies"]
    )
    page = client.get(f"{url}/sessions?room_id={first_room['id']}&limit=2").json()
    assert all(s["room_id"] == first_room["id"] for s in page["items"])
    assert len(page["items"]) == 2 and page["total"] >= 2
    assert page["items"][0]["starts_at"] <= page["items"][1]["starts_at"]
    assert client.get(f"{url}/rooms/{uuid4()}").status_code == 404
    assert client.get(f"/api/v1/snapshots/{original['id']}").json() == original


def simulation_fixture(client):
    login(client)
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies["twin_csrf"],
        "Idempotency-Key": "m3-fixture",
    }
    body = snapshot_request(client)
    body["as_of"] = body["window_start"]
    result = client.post("/api/v1/snapshots", json=body, headers=headers)
    assert result.status_code == 201, result.text
    baseline = result.json()
    sessions = client.get(f"/api/v1/snapshots/{baseline['id']}/sessions").json()["items"]
    row = next(r for r in sessions if r["status"] == "scheduled")
    return (
        dict(
            snapshot_id=baseline["id"],
            type="room_unavailability",
            room_id=row["room_id"],
            closure_start=row["starts_at"],
            closure_end=row["ends_at"],
        ),
        headers,
        baseline,
    )


def test_simulation_persistence_security_and_baseline_preservation(client, pg):
    from app import schema as s
    from app.state import fingerprint

    body, headers, baseline = simulation_fixture(client)

    def frozen():
        with pg.connect() as conn:
            return fingerprint(
                jsonable_encoder(
                    {
                        t.name: [
                            dict(r) for r in conn.execute(select(t).order_by(t.c.id)).mappings()
                        ]
                        for t in [*s.DOMAIN_TABLES, s.snapshot]
                    }
                )
            )

    before = frozen()
    response = client.post("/api/v1/simulations", json=body, headers=headers)
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["baseline_input_hash"] == baseline["input_hash"]
    assert run["result"]["impact"]["affected_sessions"] >= 1
    assert client.post("/api/v1/simulations", json=body, headers=headers).json() == run
    repeated = client.post(
        "/api/v1/simulations", json=body, headers=headers | {"Idempotency-Key": "independent-run"}
    ).json()
    assert repeated["id"] != run["id"]
    assert repeated["result_hash"] == run["result_hash"]
    assert repeated["result"] == run["result"]

    assert (
        client.post(
            "/api/v1/simulations", json=body | {"room_id": str(uuid4())}, headers=headers
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/simulations/{run['id']}").json() == run
    page = client.get(
        f"/api/v1/simulations/{run['id']}/sessions?stage=reassigned&affected_only=true&limit=1"
    ).json()
    assert page["total"] == run["result"]["impact"]["affected_sessions"]
    assert len(page["items"]) == 1
    assert client.get(f"/api/v1/simulations/{run['id']}/sessions?stage=invalid").status_code == 422
    assert (
        client.get(f"/api/v1/simulations/{run['id']}/sessions?stage=baseline&offset=-1").status_code
        == 422
    )
    with pytest.raises(DBAPIError, match="immutable"), pg.begin() as conn:
        conn.execute(s.simulation_run.update().values(request_hash="changed"))
    with pytest.raises(DBAPIError, match="immutable"), pg.begin() as conn:
        conn.execute(s.simulation_run.delete())
    assert client.post("/api/v1/simulations", json=body).status_code == 403
    assert (
        client.post("/api/v1/simulations", json=body | {"extra": 1}, headers=headers).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/simulations",
            json=body | {"room_id": str(uuid4())},
            headers=headers | {"Idempotency-Key": "missing-room"},
        ).status_code
        == 404
    )
    assert frozen() == before
    login(client, "viewer")
    assert client.get(f"/api/v1/simulations/{run['id']}").status_code == 200
    headers["X-CSRF-Token"] = client.cookies["twin_csrf"]
    assert client.post("/api/v1/simulations", json=body, headers=headers).status_code == 403
    client.cookies.clear()
    assert client.get(f"/api/v1/simulations/{run['id']}").status_code == 401


def test_simulation_concurrent_replay_and_audit_rollback(client, pg):
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import event
    from sqlalchemy.exc import SQLAlchemyError

    from app.schema import audit, simulation_run

    body, headers, baseline = simulation_fixture(client)

    def fail_audit(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO audit_log"):
            raise SQLAlchemyError("Deliberate audit failure")

    event.listen(pg, "before_cursor_execute", fail_audit)
    try:
        assert client.post("/api/v1/simulations", json=body, headers=headers).status_code == 503
    finally:
        event.remove(pg, "before_cursor_execute", fail_audit)
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(simulation_run)) == 0
    cookies = dict(client.cookies)

    def create(_):
        with TestClient(app) as worker:
            worker.cookies.update(cookies)
            response = worker.post("/api/v1/simulations", json=body, headers=headers)
            assert response.status_code == 201, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert results[0] == results[1]
    assert client.get(f"/api/v1/snapshots/{baseline['id']}").json() == baseline
    with pg.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(simulation_run)) == 1
        assert (
            conn.scalar(
                select(func.count()).select_from(audit).where(audit.c.action == "simulation.create")
            )
            == 1
        )


def test_simulation_restricted_runtime_role(client, pg):
    from sqlalchemy.orm import Session

    from app.db import get_db

    body, headers, _ = simulation_fixture(client)
    role_name = "m3_test_" + uuid4().hex
    with pg.begin() as conn:
        schema_name = conn.scalar(text("SELECT current_schema()"))
        conn.execute(text(f'CREATE ROLE "{role_name}" NOLOGIN'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema_name}" TO "{role_name}"'))
        conn.execute(
            text(f'GRANT SELECT ON app_user, auth_session, state_snapshot TO "{role_name}"')
        )
        conn.execute(text(f'GRANT SELECT, INSERT ON simulation_run TO "{role_name}"'))
        conn.execute(text(f'GRANT INSERT ON audit_log TO "{role_name}"'))

    def runtime_db():
        with Session(pg) as session:
            session.execute(text(f'SET LOCAL ROLE "{role_name}"'))
            yield session

    app.dependency_overrides[get_db] = runtime_db
    try:
        result = client.post("/api/v1/simulations", json=body, headers=headers)
        assert result.status_code == 201, result.text
        assert client.get(f"/api/v1/simulations/{result.json()['id']}").status_code == 200
        with pytest.raises(DBAPIError, match="permission denied"), pg.begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{role_name}"'))
            conn.execute(text("UPDATE class_session SET status=status"))
    finally:
        app.dependency_overrides.pop(get_db, None)
        with pg.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role_name}"'))
            conn.execute(text(f'DROP ROLE "{role_name}"'))
