from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.engine import Engine

from app.generator import validate_dataset
from app.schema import DOMAIN_TABLES, edition


def load_dataset(engine: Engine, dataset: dict) -> bool:
    """Atomic, idempotent load. Returns False for an already identical edition."""
    validate_dataset(dataset)
    item = dataset["edition"]
    with engine.begin() as conn:
        # Serialize seed imports so concurrent startup cannot race on the edition PK.
        conn.execute(text("SELECT pg_advisory_xact_lock(7319041)"))
        existing = (
            conn.execute(select(edition).where(edition.c.id == item["id"])).mappings().first()
        )
        if existing:
            if (
                existing["logical_content_hash"] != item["logical_content_hash"]
                or not existing["frozen_at"]
            ):
                raise ValueError("Existing edition differs or is not frozen")
            return False
        conn.execute(edition.insert().values(**item))
        for table in DOMAIN_TABLES:
            rows = dataset["tables"][table.name]
            for offset in range(0, len(rows), 2000):
                conn.execute(table.insert(), rows[offset : offset + 2000])
        conn.execute(
            update(edition).where(edition.c.id == item["id"]).values(frozen_at=datetime.now(UTC))
        )
    return True
