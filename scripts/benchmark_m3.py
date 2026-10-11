"""Measure M3 real API operations in a disposable college_twin_test schema."""

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app import db
from app import schema as s
from app.auth import hasher
from app.config import settings
from app.generator import VERSION, GeneratorConfig, content_hash, generate
from app.loader import load_dataset


def summary(samples):
    return {
        "runs": len(samples),
        "median_ms": round(statistics.median(samples), 2),
        "p95_ms": round(sorted(samples)[math.ceil(len(samples) * 0.95) - 1], 2),
        "max_ms": round(max(samples), 2),
        "samples_ms": [round(value, 2) for value in samples],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()
    if args.runs < 20:
        parser.error("Use at least 20 runs for nearest-rank p95")
    # Never seed, migrate or benchmark against the application database.
    url = make_url(settings().database_url).set(database="college_twin_test")
    schema_name = "benchmark_m3_" + uuid4().hex
    admin = create_engine(url)
    bench = create_engine(
        url, connect_args={"options": f"-csearch_path={schema_name},public"}
    )
    old_engine = db.engine
    old_origin = os.environ.get("APP_ORIGIN")
    old_cwd = Path.cwd()
    created = False
    try:
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        created = True
        db.engine = lambda: bench
        os.environ["APP_ORIGIN"] = "http://testserver"
        settings.cache_clear()
        os.chdir(root / "backend")
        command.upgrade(Config("alembic.ini"), "head")
        dataset = generate(GeneratorConfig())
        load_dataset(bench, dataset)
        with bench.begin() as conn:
            conn.execute(
                s.user.insert().values(
                    id=uuid4(),
                    username="benchmark",
                    role="planner",
                    password_hash=hasher.hash("local-benchmark-only-password"),
                )
            )
            postgres = conn.scalar(text("SHOW server_version"))

        def source_hash():
            with bench.connect() as conn:
                return content_hash(
                    {
                        name: sorted(
                            [
                                dict(row)
                                for row in conn.execute(
                                    select(s.metadata.tables[name])
                                ).mappings()
                            ],
                            key=lambda row: str(row["id"]),
                        )
                        for name in dataset["tables"]
                    }
                )

        before = source_hash()
        from app.main import app

        report = {
            "measured_at": datetime.now(UTC).isoformat(),
            "base_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
            ).strip(),
            "os": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
            "postgresql": postgres,
            "generator_version": VERSION,
            "seed": 42,
            "dataset_counts": {
                name: len(rows) for name, rows in dataset["tables"].items()
            },
            "edition_hash": dataset["edition"]["logical_content_hash"],
            "method": "FastAPI TestClient; real auth, PostgreSQL, allocation, serialization, persistence and audit commit. Sequential unique-key creates. Excludes TCP, browser, generation, migration and snapshot creation.",
            "first_call_definition": "First call per operation after seed/login/snapshot creation; not a cold process or cold database. Remaining calls are warm; nearest-rank p95.",
            "results": {},
        }
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                headers={"Origin": "http://testserver"},
                json={
                    "username": "benchmark",
                    "password": "local-benchmark-only-password",
                },
            )
            assert response.status_code == 200, response.text
            headers = {
                "Origin": "http://testserver",
                "X-CSRF-Token": client.cookies["twin_csrf"],
            }
            response = client.post(
                "/api/v1/snapshots",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={
                    "edition_id": str(dataset["edition"]["id"]),
                    "window_start": "2026-01-05T00:00:00+05:30",
                    "window_end": "2026-01-12T00:00:00+05:30",
                    "as_of": "2026-01-05T00:00:00+05:30",
                },
            )
            assert response.status_code == 201, response.text
            snapshot = response.json()
            assert snapshot["anomalies"] == []
            rooms = {
                room["code"]: str(room["id"]) for room in dataset["tables"]["room"]
            }
            report["planning_window"] = {
                key: snapshot[key] for key in ("as_of", "window_start", "window_end")
            }

            def measure(name, operation, validate):
                samples = []
                for _ in range(args.runs + 1):
                    start = perf_counter()
                    result = operation()
                    samples.append((perf_counter() - start) * 1000)
                    validate(result)
                report["results"][name] = {
                    "first_call_ms": round(samples[0], 2),
                    **summary(samples[1:]),
                }
                return result

            for name, room, start, end in [
                ("classroom_week", "ROOM-02", "2026-01-05", "2026-01-12"),
                ("lab_week", "LAB-11", "2026-01-05", "2026-01-12"),
                ("weekend_no_impact", "ROOM-02", "2026-01-10", "2026-01-12"),
            ]:
                body = {
                    "snapshot_id": snapshot["id"],
                    "type": "room_unavailability",
                    "room_id": rooms[room],
                    "closure_start": f"{start}T00:00:00+05:30",
                    "closure_end": f"{end}T00:00:00+05:30",
                }
                hashes, ids = set(), set()

                def validate_create(result, hashes=hashes, ids=ids):
                    assert result.status_code == 201, result.text
                    run = result.json()
                    hashes.add(run["result_hash"])
                    ids.add(run["id"])
                    assert run["baseline_input_hash"] == snapshot["input_hash"]

                result = measure(
                    name,
                    lambda body=body: client.post(
                        "/api/v1/simulations",
                        json=body,
                        headers={**headers, "Idempotency-Key": str(uuid4())},
                    ),
                    validate_create,
                )
                assert len(hashes) == 1 and len(ids) == args.runs + 1
                run = result.json()
                report["results"][name].update(
                    request=body,
                    impact=run["result"]["impact"],
                    result_hash=run["result_hash"],
                    distinct_runs=len(ids),
                )
                if name == "weekend_no_impact":
                    assert run["result"]["impact"]["affected_sessions"] == 0
                else:
                    assert run["result"]["impact"]["affected_sessions"] > 0
                if name == "classroom_week":
                    saved_run = run

            def validate_read(result):
                assert result.status_code == 200, result.text
                assert result.json() == saved_run

            measure(
                "saved_run_read",
                lambda: client.get(f"/api/v1/simulations/{saved_run['id']}"),
                validate_read,
            )

            def validate_page(result):
                assert result.status_code == 200, result.text
                assert (
                    result.json()["total"]
                    == saved_run["result"]["impact"]["affected_sessions"]
                )
                assert all(row["affected"] for row in result.json()["items"])

            measure(
                "affected_page_read",
                lambda: client.get(
                    f"/api/v1/simulations/{saved_run['id']}/sessions?stage=reassigned&affected_only=true&limit=50"
                ),
                validate_page,
            )
            response = client.get(f"/api/v1/snapshots/{snapshot['id']}")
            assert response.status_code == 200 and response.json() == snapshot

        assert source_hash() == before
        report["source_and_snapshot_preserved"] = True
        report["creation_p95_under_2s"] = all(
            report["results"][name]["p95_ms"] < 2000
            for name in ("classroom_week", "lab_week", "weekend_no_impact")
        )
    finally:
        db.engine = old_engine
        os.chdir(old_cwd)
        if old_origin is None:
            os.environ.pop("APP_ORIGIN", None)
        else:
            os.environ["APP_ORIGIN"] = old_origin
        settings.cache_clear()
        bench.dispose()
        try:
            if created:
                with admin.begin() as conn:
                    conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        finally:
            admin.dispose()
    report["disposable_schema_removed"] = True
    (root / "docs" / "m3-performance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
