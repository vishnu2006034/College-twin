"""Run the suite against a dedicated local PostgreSQL database, without echoing secrets."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.config import settings

parser = argparse.ArgumentParser()
parser.add_argument("--create-test-database", action="store_true")
args = parser.parse_args()
source = make_url(settings().database_url)
target = source.set(database="college_twin_test")
if args.create_test_database:
    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname=:name"),
            {"name": "college_twin_test"},
        ):
            conn.execute(text("CREATE DATABASE college_twin_test"))
    admin.dispose()
env = dict(os.environ, TEST_DATABASE_URL=target.render_as_string(hide_password=False))
raise SystemExit(
    subprocess.call(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=root / "backend",
        env=env,
    )
)
