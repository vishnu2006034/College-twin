"""Explicit planner-reviewed room links; no label or row-order inference."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import schema as s
from app.auth import current_user, require_planner
from app.db import get_db

CATALOG = {
    r["id"]: r
    for r in json.loads(Path(__file__).with_name("campus_catalog.json").read_text(encoding="utf-8"))
}
router = APIRouter(prefix="/api/v1/room-mappings", tags=["room mappings"])


class Binding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    space_id: str = Field(min_length=1, max_length=100)
    room_id: UUID


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=0)
    bindings: list[Binding] = Field(max_length=200)
    review_note: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def unique(self):
        for field in ("space_id", "room_id"):
            if len({getattr(b, field) for b in self.bindings}) != len(self.bindings):
                raise ValueError("Each physical space and synthetic room may be linked only once")
        return self


def frozen_edition(db, edition_id):
    if not db.scalar(
        select(s.edition.c.id).where(
            s.edition.c.id == edition_id, s.edition.c.frozen_at.is_not(None)
        )
    ):
        raise HTTPException(404, "Frozen dataset not found")


@router.get("/{edition_id}")
def get_mapping(edition_id: UUID, actor=Depends(current_user), db: Session = Depends(get_db)):
    frozen_edition(db, edition_id)
    row = (
        db.execute(select(s.room_mapping).where(s.room_mapping.c.edition_id == edition_id))
        .mappings()
        .first()
    )
    return (
        dict(row)
        if row
        else dict(
            edition_id=edition_id,
            version=0,
            bindings=[],
            reviewed_by=None,
            reviewed_at=None,
            review_note=None,
        )
    )


@router.post("/{edition_id}")
def review_mapping(
    edition_id: UUID,
    body: Review,
    request: Request,
    actor=Depends(require_planner),
    db: Session = Depends(get_db),
):
    frozen_edition(db, edition_id)
    rooms = {
        r["id"]: r
        for r in db.execute(select(s.room).where(s.room.c.edition_id == edition_id)).mappings()
    }
    for binding in body.bindings:
        space, room = CATALOG.get(binding.space_id), rooms.get(binding.room_id)
        if space is None or room is None:
            raise HTTPException(422, "Unknown teaching space or room outside this edition")
        if space["kind"] != room["kind"]:
            raise HTTPException(422, "Physical and synthetic room kinds must match")
    values = dict(
        version=body.expected_version + 1,
        bindings=[
            b.model_dump(mode="json") for b in sorted(body.bindings, key=lambda b: b.space_id)
        ],
        reviewed_by=actor["id"],
        reviewed_at=datetime.now(UTC),
        review_note=body.review_note,
    )
    if body.expected_version == 0:
        stmt = (
            insert(s.room_mapping).values(edition_id=edition_id, **values).on_conflict_do_nothing()
        )
    else:
        stmt = (
            update(s.room_mapping)
            .where(
                s.room_mapping.c.edition_id == edition_id,
                s.room_mapping.c.version == body.expected_version,
            )
            .values(**values)
        )
    row = db.execute(stmt.returning(s.room_mapping)).mappings().first()
    if not row:
        raise HTTPException(409, "Mapping changed since review. Reload before reviewing again.")
    db.execute(
        s.audit.insert().values(
            id=uuid4(),
            actor_id=actor["id"],
            action="room_mapping.review",
            resource_id=edition_id,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
            outcome="success",
        )
    )
    result = dict(row)
    db.commit()
    return result
