"""Disposable real-API browser fixture on localhost:8000; Ctrl+C removes its test schema.

Use only with the local frontend. Account: m2-preview / local-preview-only-password.
The account and synthetic records exist only in a random college_twin_test schema.
"""

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

import uvicorn
from alembic import command
from alembic.config import Config
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
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--origin", default="http://localhost:5173")
args = parser.parse_args()
url = make_url(settings().database_url).set(database="college_twin_test")
schema_name = "preview_" + uuid4().hex
admin = create_engine(url)
with admin.begin() as conn:
    conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
preview_engine = create_engine(
    url, connect_args={"options": f"-csearch_path={schema_name},public"}
)
db.engine = lambda: preview_engine
os.environ["APP_ORIGIN"] = args.origin
settings.cache_clear()
os.chdir(root / "backend")
try:
    command.upgrade(Config("alembic.ini"), "head")
    load_dataset(
        preview_engine, generate(GeneratorConfig(weeks=1, students_per_section=2))
    )
    with preview_engine.begin() as conn:
        conn.execute(
            user.insert().values(
                id=uuid4(),
                username="m2-preview",
                role="planner",
                password_hash=hasher.hash("local-preview-only-password"),
            )
        )
    print(f"Disposable test schema: {schema_name}", flush=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, proxy_headers=False)
finally:
    preview_engine.dispose()
    with admin.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
    admin.dispose()
