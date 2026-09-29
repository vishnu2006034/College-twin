"""Immutable, transactional M3 runs computed exclusively from saved M2 inputs."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import schema as s
from app.auth import current_user, require_planner
from app.db import get_db
from app.simulation import (
    SimulationError,
    SimulationRequest,
    SimulationResponse,
    SimulationSessionsPage,
    simulate,
)
from app.snapshots import saved as saved_snapshot
from app.state import fingerprint

router = APIRouter(prefix="/api/v1/simulations", tags=["simulations"])


@router.post("", status_code=201, response_model=SimulationResponse)
def create_simulation(
    body: SimulationRequest,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=128),
    actor=Depends(require_planner),
    db: Session = Depends(get_db),
):
    normalized = body.model_dump(mode="json")
    request_hash = fingerprint(normalized)
    query = select(s.simulation_run).where(
        s.simulation_run.c.created_by == actor["id"],
        s.simulation_run.c.idempotency_key == idempotency_key,
    )

    def replay(row):
        if row["request_hash"] != request_hash:
            raise HTTPException(409, "Idempotency key already used for a different request")
        return row["response"]

    existing = db.execute(query).mappings().first()
    if existing:
        return replay(existing)
    baseline = saved_snapshot(db, body.snapshot_id)
    source = baseline["response"]
    if str(baseline["edition_id"]) != source["edition_id"]:
        raise HTTPException(409, "Snapshot edition mismatch")
    try:
        calculation = simulate(body, source, baseline["canonical_inputs"])
    except SimulationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    run_id = uuid4()
    response = SimulationResponse(
        id=run_id,
        created_at=datetime.now(UTC),
        created_by=actor["id"],
        snapshot_id=body.snapshot_id,
        request=body,
        baseline_input_hash=source["input_hash"],
        **{
            key: source[key]
            for key in ("edition_id", "edition_hash", "as_of", "window_start", "window_end")
        },
        **calculation.model_dump(exclude={"sessions"}),
    ).model_dump(mode="json")
    inserted = db.scalar(
        insert(s.simulation_run)
        .values(
            id=run_id,
            snapshot_id=body.snapshot_id,
            edition_id=baseline["edition_id"],
            created_by=actor["id"],
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            canonical_inputs={
                "request": normalized,
                "snapshot": source,
                "baseline": baseline["canonical_inputs"],
            },
            response=response,
            sessions=calculation.sessions.model_dump(mode="json"),
        )
        .on_conflict_do_nothing(index_elements=["created_by", "idempotency_key"])
        .returning(s.simulation_run.c.id)
    )
    if inserted is None:
        return replay(db.execute(query).mappings().one())
    db.execute(
        s.audit.insert().values(
            id=uuid4(),
            actor_id=actor["id"],
            action="simulation.create",
            resource_id=run_id,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
            outcome="success",
        )
    )
    db.commit()
    return response


def saved(db, run_id):
    row = (
        db.execute(select(s.simulation_run).where(s.simulation_run.c.id == run_id))
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "Simulation not found")
    return row


@router.get("/{run_id}", response_model=SimulationResponse)
def get_simulation(run_id: UUID, actor=Depends(current_user), db: Session = Depends(get_db)):
    return saved(db, run_id)["response"]


@router.get("/{run_id}/sessions", response_model=SimulationSessionsPage)
def get_sessions(
    run_id: UUID,
    stage: Literal["baseline", "disrupted", "reassigned"],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    room_id: UUID | None = None,
    affected_only: bool = False,
    actor=Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = saved(db, run_id)["sessions"][stage]
    rows = [
        row
        for row in rows
        if (not affected_only or row["affected"])
        and (room_id is None or row["assigned_room_id"] == str(room_id))
    ]
    return dict(items=rows[offset : offset + limit], total=len(rows), limit=limit, offset=offset)
