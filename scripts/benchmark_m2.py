"""Repeatable in-process HTTP/API benchmark on an isolated PostgreSQL test schema."""

import argparse
import json
import math
import os
import platform
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app import db
from app.auth import hasher
from app.config import settings
from app.generator import GeneratorConfig, generate
from app.loader import load_dataset
from app.schema import user

parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=int, default=20)
args = parser.parse_args()
if args.runs < 20:
    parser.error("Use at least 20 runs for p95")
url = make_url(settings().database_url).set(database="college_twin_test")
schema_name = "benchmark_" + uuid4().hex
admin = create_engine(url)
with admin.begin() as conn:
    conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
bench = create_engine(
    url, connect_args={"options": f"-csearch_path={schema_name},public"}
)
db.engine = lambda: bench
os.environ["APP_ORIGIN"] = "http://testserver"
settings.cache_clear()
os.chdir(root / "backend")


def summary(samples):
    return {
        "runs": len(samples),
        "median_ms": round(statistics.median(samples), 2),
        "p95_ms": round(sorted(samples)[math.ceil(len(samples) * 0.95) - 1], 2),
        "max_ms": round(max(samples), 2),
    }


try:
    command.upgrade(Config("alembic.ini"), "head")
    dataset = generate(GeneratorConfig())
    load_dataset(bench, dataset)
    with bench.begin() as conn:
        conn.execute(
            user.insert().values(
                id=uuid4(),
                username="benchmark",
                role="planner",
                password_hash=hasher.hash("local-benchmark-only-password"),
            )
        )
        postgres = conn.scalar(text("SHOW server_version"))
    from app.main import app

    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "os": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "postgresql": postgres,
        "dataset_counts": {k: len(v) for k, v in dataset["tables"].items()},
        "seed": 42,
        "edition_hash": dataset["edition"]["logical_content_hash"],
        "method": "FastAPI TestClient including auth, SQL, computation, JSON persistence and response serialization. Loopback PostgreSQL. Sequential unique-key creates; no concurrent load. Excludes TCP/browser rendering.",
        "cold_definition": "First measured call after seed/login; application and OS/database caches are not cold. Subsequent calls are warm.",
        "results": {},
    }
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/auth/login",
                headers={"Origin": "http://testserver"},
                json={
                    "username": "benchmark", "password": "local-benchmark-only-password"
                },
            ).status_code
            == 200
        )
        headers = {
            "Origin": "http://testserver",
            "X-CSRF-Token": client.cookies["twin_csrf"],
        }
        for name, end, cutoff in [
            ("one_day", "2026-01-06", "2026-01-05"),
            ("seven_days", "2026-01-12", "2026-01-09"),
        ]:
            body = {
                "edition_id": str(dataset["edition"]["id"]),
                "window_start": "2026-01-05T00:00:00+05:30",
                "window_end": f"{end}T00:00:00+05:30",
                "as_of": f"{cutoff}T17:00:00+05:30",
            }
            samples = []
            for _ in range(args.runs + 1):
                start = perf_counter()
                response = client.post(
                    "/api/v1/snapshots",
                    json=body,
                    headers=dict(headers, **{"Idempotency-Key": str(uuid4())}),
                )
                elapsed = (perf_counter() - start) * 1000
                assert response.status_code == 201, response.text
                assert response.json()["anomalies"] == []
                samples.append(elapsed)
            report["results"][name] = dict(
                first_call_ms=round(samples[0], 2), **summary(samples[1:])
            )
        snapshot = response.json()
        room_id = str(dataset["tables"]["room"][0]["id"])
        samples = []
        for _ in range(args.runs):
            start = perf_counter()
            response = client.get(f"/api/v1/snapshots/{snapshot['id']}/rooms/{room_id}")
            samples.append((perf_counter() - start) * 1000)
            assert response.status_code == 200
        report["results"]["saved_room_read"] = summary(samples)
    report["snapshot_p95_under_2s"] = all(
        report["results"][k]["p95_ms"] < 2000 for k in ("one_day", "seven_days")
    )
    output = root / "docs" / "m2-performance.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
finally:
    bench.dispose()
    with admin.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
    admin.dispose()
