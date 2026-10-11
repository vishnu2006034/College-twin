"""Verify the local launcher and real frontend proxy with disposable PostgreSQL data."""

import json
import os
import platform
import secrets
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from start_local import check_ports, services

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import db
from app.auth import hasher
from app.config import settings
from app.generator import GeneratorConfig, generate
from app.loader import load_dataset
from app.schema import user


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    url = make_url(settings().database_url).set(database="college_twin_test")
    schema_name = "startup_" + uuid4().hex
    admin = create_engine(url)
    scoped_url = url.update_query_dict(
        {"options": f"-csearch_path={schema_name},public"}
    )
    isolated = create_engine(scoped_url)
    original_engine = db.engine
    original_url = os.environ.get("DATABASE_URL")
    original_cwd = Path.cwd()
    password = secrets.token_urlsafe(24)
    created = False
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "os": platform.platform(),
        "checks": {},
    }
    try:
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        created = True
        db.engine = lambda: isolated
        os.environ["DATABASE_URL"] = scoped_url.render_as_string(hide_password=False)
        settings.cache_clear()
        os.chdir(ROOT / "backend")
        command.upgrade(Config("alembic.ini"), "head")
        dataset = generate(GeneratorConfig(weeks=1, students_per_section=2))
        assert load_dataset(isolated, dataset)
        assert not load_dataset(isolated, dataset)
        report["checks"]["seed_replay_unchanged"] = True
        with isolated.begin() as conn:
            for role in ("planner", "viewer"):
                conn.execute(
                    user.insert().values(
                        id=uuid4(),
                        username=role,
                        role=role,
                        password_hash=hasher.hash(password),
                    )
                )
        backend_port, frontend_port = free_port(), free_port()
        while frontend_port == backend_port:
            frontend_port = free_port()
        origin = f"http://localhost:{frontend_port}"
        with services(backend_port, frontend_port) as processes:
            report["checks"]["both_services_running"] = all(
                process.poll() is None for process in processes
            )
            try:
                check_ports((backend_port, frontend_port))
                raise AssertionError("Occupied ports were not rejected")
            except RuntimeError:
                report["checks"]["occupied_ports_rejected"] = True
            with httpx.Client(base_url=origin, timeout=15, trust_env=False) as client:
                assert client.get("/").status_code == 200
                assert client.get("/api/v1/health").json()["status"] == "ok"
                assert client.get("/api/v1/datasets").status_code == 401
                report["checks"]["frontend_proxy_health_and_anonymous_denial"] = True
                for role in ("planner", "viewer"):
                    response = client.post(
                        "/api/v1/auth/login",
                        headers={"Origin": origin},
                        json={"username": role, "password": password},
                    )
                    assert response.status_code == 200
                    assert client.get("/api/v1/auth/me").json()["role"] == role
                    response = client.get("/api/v1/datasets")
                    assert response.status_code == 200
                    assert str(dataset["edition"]["id"]) in response.text
                    response = client.get(
                        "/api/v1/rooms",
                        params={"edition_id": str(dataset["edition"]["id"])},
                    )
                    assert response.status_code == 200
                    assert response.json()["total"] == 12
                    assert (
                        client.post(
                            "/api/v1/auth/logout", headers={"Origin": origin}
                        ).status_code
                        == 403
                    )
                    response = client.post(
                        "/api/v1/auth/logout",
                        headers={
                            "Origin": origin,
                            "X-CSRF-Token": client.cookies["twin_csrf"],
                        },
                    )
                    assert response.status_code in (200, 204)
                    assert client.get("/api/v1/auth/me").status_code == 401
                    report["checks"][f"{role}_login_reads_csrf_logout"] = True
        assert all(process.poll() is not None for process in processes)
        check_ports((backend_port, frontend_port))
        report["checks"]["owned_services_stopped_and_ports_released"] = True
    finally:
        db.engine = original_engine
        os.chdir(original_cwd)
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url
        settings.cache_clear()
        isolated.dispose()
        try:
            if created:
                with admin.begin() as conn:
                    conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        finally:
            admin.dispose()
    report["checks"]["disposable_schema_removed"] = True
    (ROOT / "docs/m1-startup-verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
