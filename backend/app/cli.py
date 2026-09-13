"""Administrative operations; not exposed through the web application."""

import argparse
import getpass
import json
import os
from pathlib import Path
from uuid import uuid4

from psycopg import sql
from sqlalchemy import select

from app.auth import hasher
from app.db import engine
from app.generator import GeneratorConfig, canonical, generate, validate_dataset
from app.loader import load_dataset
from app.schema import DOMAIN_TABLES, user


def create_user(username, role, password):
    if len(password) < 16 or password.startswith("replace-"):
        raise ValueError(
            "Use a unique password with at least 16 characters; placeholders are rejected"
        )
    with engine().begin() as conn:
        if conn.scalar(select(user.c.id).where(user.c.username == username)):
            return
        conn.execute(
            user.insert().values(
                id=uuid4(), username=username, password_hash=hasher.hash(password), role=role
            )
        )


def provision_app_role(password):
    if len(password) < 24 or password.startswith("replace-"):
        raise ValueError("API_DB_PASSWORD must contain at least 24 characters")
    # psycopg's Identifier/Literal quoting avoids password interpolation into raw SQL.
    raw = engine().raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='twin_app'")
            if not cur.fetchone():
                cur.execute("CREATE ROLE twin_app LOGIN")
            cur.execute(sql.SQL("ALTER ROLE twin_app PASSWORD {}").format(sql.Literal(password)))
            cur.execute("GRANT USAGE ON SCHEMA public TO twin_app")
            for name in ["dataset_edition"] + [t.name for t in DOMAIN_TABLES]:
                cur.execute(sql.SQL("GRANT SELECT ON {} TO twin_app").format(sql.Identifier(name)))
            cur.execute("GRANT SELECT ON app_user TO twin_app")
            cur.execute("GRANT SELECT, INSERT, DELETE ON auth_session TO twin_app")
            cur.execute("GRANT INSERT ON audit_log TO twin_app")
        raw.commit()
    finally:
        raw.close()


def main():
    parser = argparse.ArgumentParser(description="College Twin M1 administration")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "seed"):
        child = sub.add_parser(command)
        child.add_argument("--seed", type=int, default=42)
        child.add_argument("--weeks", type=int, default=16)
        if command == "generate":
            child.add_argument("--output", type=Path, required=True)
    sub.add_parser("bootstrap")
    account = sub.add_parser("create-user")
    account.add_argument("username")
    account.add_argument("--role", choices=["viewer", "planner"], required=True)
    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.username, args.role, getpass.getpass("Password (16+ characters): "))
        return
    if args.command == "bootstrap":
        for role in ("planner", "viewer"):
            create_user(role, role, os.environ[f"{role.upper()}_PASSWORD"])
        provision_app_role(os.environ["API_DB_PASSWORD"])
    config = GeneratorConfig(seed=getattr(args, "seed", 42), weeks=getattr(args, "weeks", 16))
    dataset = generate(config)
    counts = validate_dataset(dataset)
    if args.command == "generate":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical(dataset) + "\n", encoding="utf-8")
    else:
        inserted = load_dataset(engine(), dataset)
        print("Loaded new edition" if inserted else "Edition already loaded; unchanged")
    print(
        json.dumps(
            {
                "edition_id": str(dataset["edition"]["id"]),
                "hash": dataset["edition"]["logical_content_hash"],
                "counts": counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
