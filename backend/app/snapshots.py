"""Transactional snapshot persistence and authenticated API."""

from datetime import UTC, datetime, time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import schema as s
from app.auth import current_user, require_planner
from app.db import get_db
from app.state import LOCAL, SnapshotRequest, SnapshotResponse, calculate, fingerprint, stamp

router = APIRouter(prefix="/api/v1/snapshots", tags=["snapshots"])


@router.post("", status_code=201, response_model=SnapshotResponse)
def create_snapshot(
    body: SnapshotRequest,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=128),
    actor=Depends(require_planner),
    db: Session = Depends(get_db),
):
    normalized = body.model_dump(mode="json")
    request_hash = fingerprint(normalized)
    existing_query = select(s.snapshot).where(
        s.snapshot.c.created_by == actor["id"],
        s.snapshot.c.idempotency_key == idempotency_key,
    )

    def replay(row):
        if row["request_hash"] != request_hash:
            raise HTTPException(409, "Idempotency key already used for a different request")
        return row["response"]

    existing = db.execute(existing_query).mappings().first()
    if existing:
        return replay(existing)
    edition = (
        db.execute(
            select(s.edition).where(
                s.edition.c.id == body.edition_id, s.edition.c.frozen_at.is_not(None)
            )
        )
        .mappings()
        .first()
    )
    if not edition:
        raise HTTPException(404, "Frozen dataset not found")
    terms = (
        db.execute(select(s.term).where(s.term.c.edition_id == body.edition_id)).mappings().all()
    )
    if not any(
        datetime.combine(t["start_date"], time(), LOCAL) <= body.window_start
        and body.window_end <= datetime.combine(t["end_date"], time(), LOCAL)
        for t in terms
    ):
        raise HTTPException(422, "Window must be inside the dataset term")
    tables = {}
    for table in (
        s.room,
        s.offering,
        s.course,
        s.student,
        s.faculty,
        s.class_session,
        s.attendance,
    ):
        stmt = select(table).where(table.c.edition_id == body.edition_id)
        if table is s.class_session:
            stmt = stmt.where(
                table.c.starts_at < body.window_end, table.c.ends_at > body.window_start
            )
        if table is s.attendance:
            stmt = stmt.where(
                table.c.recorded_at <= body.as_of,
                table.c.session_id.in_(
                    select(s.class_session.c.id).where(
                        s.class_session.c.edition_id == body.edition_id,
                        s.class_session.c.starts_at < body.window_end,
                        s.class_session.c.ends_at > body.window_start,
                    )
                ),
            )
        tables[table.name] = [dict(r) for r in db.execute(stmt.order_by(table.c.id)).mappings()]
    # Normalize before calculation/hash so replay does not depend on driver representations.
    inputs = jsonable_encoder(dict(request=normalized, tables=tables))
    result = calculate(body, inputs["tables"])
    inputs["sessions"] = result["sessions"]
    snapshot_id = uuid4()
    response = SnapshotResponse(
        **normalized,
        id=snapshot_id,
        input_hash=fingerprint(inputs),
        edition_hash=edition["logical_content_hash"],
        created_at=datetime.now(UTC),
        **{k: result[k] for k in ("metrics", "coverage", "anomalies")},
    ).model_dump(mode="json")
    inserted = db.scalar(
        insert(s.snapshot)
        .values(
            id=snapshot_id,
            edition_id=body.edition_id,
            created_by=actor["id"],
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            canonical_inputs=inputs,
            response=response,
        )
        .on_conflict_do_nothing(index_elements=["created_by", "idempotency_key"])
        .returning(s.snapshot.c.id)
    )
    if inserted is None:
        return replay(db.execute(existing_query).mappings().one())
    db.execute(
        s.audit.insert().values(
            id=uuid4(),
            actor_id=actor["id"],
            action="snapshot.create",
            resource_id=snapshot_id,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
            outcome="success",
        )
    )
    db.commit()
    return response


def saved(db, snapshot_id):
    row = db.execute(select(s.snapshot).where(s.snapshot.c.id == snapshot_id)).mappings().first()
    if not row:
        raise HTTPException(404, "Snapshot not found")
    return row


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
def get_snapshot(snapshot_id: UUID, actor=Depends(current_user), db: Session = Depends(get_db)):
    return saved(db, snapshot_id)["response"]


@router.get("/{snapshot_id}/sessions")
def get_sessions(
    snapshot_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    room_id: UUID | None = None,
    actor=Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = saved(db, snapshot_id)["canonical_inputs"]["sessions"]
    if room_id is not None:
        rows = [r for r in rows if r["room_id"] == str(room_id)]
    rows = sorted(rows, key=lambda r: (stamp(r["starts_at"]), r["id"]))
    return dict(items=rows[offset : offset + limit], total=len(rows), limit=limit, offset=offset)


@router.get("/{snapshot_id}/rooms/{room_id}")
def get_room_state(
    snapshot_id: UUID, room_id: UUID, actor=Depends(current_user), db: Session = Depends(get_db)
):
    row = saved(db, snapshot_id)
    inputs, response = row["canonical_inputs"], row["response"]
    room = next((r for r in inputs["tables"]["room"] if r["id"] == str(room_id)), None)
    if room is None:
        raise HTTPException(404, "Room not present in this snapshot edition")
    # Compute only from the saved canonical inputs, never the current source edition.
    tables = dict(inputs["tables"])
    tables["room"] = [room]
    tables["class_session"] = [r for r in tables["class_session"] if r["room_id"] == str(room_id)]
    result = calculate(SnapshotRequest(**inputs["request"]), tables)
    session_ids = {r["id"] for r in result["sessions"]}
    # Keep cross-room faculty/section clashes from the full saved snapshot.
    anomalies = [a for a in response["anomalies"] if session_ids.intersection(a["session_ids"])]
    return dict(
        snapshot_id=snapshot_id,
        edition_id=response["edition_id"],
        as_of=response["as_of"],
        window_start=response["window_start"],
        window_end=response["window_end"],
        schema_version=response["schema_version"],
        synthetic_data_only=True,
        input_hash=response["input_hash"],
        room=room,
        metrics=result["metrics"],
        coverage=result["coverage"],
        anomalies=anomalies,
    )
