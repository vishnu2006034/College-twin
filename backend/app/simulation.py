"""Pure M3 room allocation. No database, HTTP, wall clock or source-data writes."""

from collections import Counter
from copy import deepcopy
from datetime import UTC
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.state import (
    Anomaly,
    Coverage,
    SnapshotRequest,
    SnapshotResponse,
    Workload,
    calculate,
    fingerprint,
    minutes,
    stamp,
    teaching_intervals,
)

ALGORITHM_VERSION = "greedy_room_v1"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SimulationRequest(Model):
    snapshot_id: UUID
    type: Literal["room_unavailability"]
    room_id: UUID
    closure_start: AwareDatetime
    closure_end: AwareDatetime

    @model_validator(mode="after")
    def interval(self):
        self.closure_start = self.closure_start.astimezone(UTC)
        self.closure_end = self.closure_end.astimezone(UTC)
        if self.closure_start >= self.closure_end:
            raise ValueError("Closure must have a positive duration")
        return self


class CandidateSummary(Model):
    total_rooms: int = Field(ge=0)
    rejected_type: int = Field(default=0, ge=0)
    rejected_capacity: int = Field(default=0, ge=0)
    rejected_closure: int = Field(default=0, ge=0)
    rejected_room_busy: int = Field(default=0, ge=0)
    rejected_faculty_busy: int = Field(default=0, ge=0)
    rejected_section_busy: int = Field(default=0, ge=0)
    feasible_count: int = Field(default=0, ge=0)


class ScenarioSession(Model):
    id: UUID
    room_id: UUID
    faculty_id: UUID
    section_id: UUID
    course_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    status: Literal["scheduled", "held", "cancelled"]
    original_room_id: UUID
    assigned_room_id: UUID | None
    allocation_status: Literal["unchanged", "displaced", "reassigned", "unresolved"]
    affected: bool
    candidate_summary: CandidateSummary | None = None
    reason_code: Literal["no_feasible_candidate"] | None = None


class StageSummary(Model):
    scheduled_classes: int
    assigned_classes: int
    unassigned_classes: int
    scheduled_occupied_rooms: int
    available_rooms: int
    booked_room_minutes: float
    available_room_minutes: float
    room_utilization: float | None
    required_faculty_minutes: list[Workload]
    assigned_faculty_minutes: list[Workload]
    anomalies: list[Anomaly]


class Stages(Model):
    baseline: StageSummary
    disrupted: StageSummary
    reassigned: StageSummary


class StageRows(Model):
    baseline: list[ScenarioSession]
    disrupted: list[ScenarioSession]
    reassigned: list[ScenarioSession]


class Impact(Model):
    affected_sessions: int
    affected_students: int
    reassigned_sessions: int
    unresolved_sessions: int
    unresolved_students: int


class StageDelta(Model):
    assigned_classes: int
    unassigned_classes: int
    booked_room_minutes: float
    available_room_minutes: float
    room_utilization: float | None


class Deltas(Model):
    disrupted: StageDelta
    reassigned: StageDelta


class ObservedAttendance(Model):
    label: Literal["Observed at baseline cutoff; unchanged by simulation"] = (
        "Observed at baseline cutoff; unchanged by simulation"
    )
    attendance_present: int
    attendance_recorded: int
    attendance_expected: int
    attendance_rate: float | None
    coverage: Coverage


class Recommendation(Model):
    code: Literal["no_affected_sessions", "all_reassigned", "partially_unresolved"]
    message: str


class SimulationResult(Model):
    stages: Stages
    impact: Impact
    deltas: Deltas
    observed_attendance: ObservedAttendance
    recommendation: Recommendation


class SimulationCalculation(Model):
    """Internal calculation output; stage rows are persisted for later paginated reads."""

    schema_version: Literal[1] = 1
    algorithm_version: Literal["greedy_room_v1"] = ALGORITHM_VERSION
    input_hash: str
    result_hash: str
    result: SimulationResult
    sessions: StageRows


class SimulationResponse(Model):
    """Saved API envelope; creation identity is supplied by persistence."""

    id: UUID
    created_at: AwareDatetime
    created_by: UUID
    schema_version: Literal[1] = 1
    algorithm_version: Literal["greedy_room_v1"] = ALGORITHM_VERSION
    synthetic_data_only: Literal[True] = True
    snapshot_id: UUID
    edition_id: UUID
    edition_hash: str
    baseline_input_hash: str
    as_of: AwareDatetime
    window_start: AwareDatetime
    window_end: AwareDatetime
    request: SimulationRequest
    input_hash: str
    result_hash: str
    result: SimulationResult


class SimulationSessionsPage(Model):
    items: list[ScenarioSession]
    total: int
    limit: int
    offset: int


class SimulationError(ValueError):
    """Domain failure with an explicit status for the future API adapter."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def overlaps(a, b, c, d):
    return a < d and c < b


def _baseline(body, response, inputs):
    try:
        snapshot = SnapshotResponse.model_validate(response)
        request = SnapshotRequest.model_validate(inputs["request"])
        if fingerprint(inputs) != snapshot.input_hash:
            raise ValueError("Input checksum differs")
        if request != SnapshotRequest.model_validate(
            snapshot.model_dump(include=set(SnapshotRequest.model_fields))
        ):
            raise ValueError("Snapshot request differs")
        state = calculate(request, inputs["tables"])
        if state["sessions"] != inputs["sessions"]:
            raise ValueError("Saved sessions differ")
        for field in ("metrics", "coverage", "anomalies"):
            # Validate through M2's models to normalize timestamps and numeric types.
            expected = SnapshotResponse.model_validate(
                snapshot.model_dump() | {field: state[field]}
            )
            if getattr(expected, field) != getattr(snapshot, field):
                raise ValueError("Saved results differ")
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise SimulationError(409, "invalid_baseline", "Unsupported or corrupt snapshot") from exc
    if body.snapshot_id != snapshot.id:
        raise SimulationError(409, "snapshot_mismatch", "Request and baseline snapshot differ")
    if request.as_of != request.window_start:
        raise SimulationError(
            409, "planning_baseline_required", "Create a snapshot at window start"
        )
    if not request.window_start <= body.closure_start < body.closure_end <= request.window_end:
        raise SimulationError(422, "closure_outside_window", "Closure must be inside the window")
    if str(body.room_id) not in {str(r["id"]) for r in inputs["tables"]["room"]}:
        raise SimulationError(404, "room_not_found", "Room not present in the snapshot edition")
    for row in state["sessions"]:
        if row["status"] == "cancelled":
            continue
        if row["status"] != "scheduled" or not (
            request.window_start
            <= stamp(row["starts_at"])
            < stamp(row["ends_at"])
            <= request.window_end
        ):
            raise SimulationError(
                409,
                "planning_baseline_required",
                "Create a planning snapshot with all active classes fully inside its window",
            )
    if state["anomalies"]:
        raise SimulationError(
            409, "infeasible_baseline", "Review the baseline snapshot anomalies before simulating"
        )
    return snapshot, request, state


def _summary(request, body, tables, rows, baseline, closure):
    assignments = {str(r.id): str(r.assigned_room_id) for r in rows if r.assigned_room_id}
    projected = dict(tables)
    projected["class_session"] = [
        dict(r, room_id=assignments[str(r["id"])])
        for r in tables["class_session"]
        if str(r["id"]) in assignments
    ]
    state = calculate(request, projected)
    metrics = state["metrics"]
    if state["anomalies"]:
        raise RuntimeError("Scenario produced invalid assignments")
    available = metrics["available_room_minutes"]
    closed_at_cutoff = False
    if closure:
        available -= minutes(
            [
                (max(a, body.closure_start), min(b, body.closure_end))
                for a, b in teaching_intervals(request.window_start, request.window_end)
                if overlaps(a, b, body.closure_start, body.closure_end)
            ]
        )
        closed_at_cutoff = body.closure_start <= request.as_of < body.closure_end
        if any(
            r.assigned_room_id == body.room_id
            and overlaps(r.starts_at, r.ends_at, body.closure_start, body.closure_end)
            for r in rows
        ):
            raise RuntimeError("Scenario assigned a class to the closed room")
    demand = baseline["metrics"]["scheduled_classes"]
    return StageSummary(
        scheduled_classes=demand,
        assigned_classes=metrics["scheduled_classes"],
        unassigned_classes=demand - metrics["scheduled_classes"],
        scheduled_occupied_rooms=metrics["scheduled_occupied_rooms"],
        available_rooms=metrics["available_rooms"] - int(closed_at_cutoff),
        booked_room_minutes=metrics["booked_room_minutes"],
        available_room_minutes=available,
        room_utilization=metrics["booked_room_minutes"] / available if available else None,
        required_faculty_minutes=baseline["metrics"]["faculty_workload"],
        assigned_faculty_minutes=metrics["faculty_workload"],
        anomalies=state["anomalies"],
    )


def _allocate(body, rows, tables):
    sizes = Counter(str(r["section_id"]) for r in tables["student"])
    courses = {str(r["id"]): r for r in tables["course"]}
    affected = sorted(
        (r for r in rows if r.affected),
        key=lambda r: (-sizes[str(r.section_id)], r.starts_at, str(r.id)),
    )
    for row in affected:
        course = courses[str(row.course_id)]
        size = sizes[str(row.section_id)]
        summary = CandidateSummary(total_rooms=len(tables["room"]))
        busy = [
            other
            for other in rows
            if other.assigned_room_id
            and overlaps(row.starts_at, row.ends_at, other.starts_at, other.ends_at)
        ]
        candidates = []
        for room in tables["room"]:
            room_id = UUID(str(room["id"]))
            if (room["kind"], room["lab_type"]) != (
                course["required_room_kind"],
                course["required_lab_type"],
            ):
                summary.rejected_type += 1
            elif room["capacity"] < size:
                summary.rejected_capacity += 1
            elif room_id == body.room_id and overlaps(
                row.starts_at, row.ends_at, body.closure_start, body.closure_end
            ):
                summary.rejected_closure += 1
            elif any(other.assigned_room_id == room_id for other in busy):
                summary.rejected_room_busy += 1
            elif any(other.faculty_id == row.faculty_id for other in busy):
                summary.rejected_faculty_busy += 1
            elif any(other.section_id == row.section_id for other in busy):
                summary.rejected_section_busy += 1
            else:
                candidates.append((room["capacity"] - size, str(room_id)))
        summary.feasible_count = len(candidates)
        row.candidate_summary = summary
        if candidates:
            row.assigned_room_id = UUID(min(candidates)[1])
            row.allocation_status = "reassigned"
        else:
            row.allocation_status = "unresolved"
            row.reason_code = "no_feasible_candidate"


def simulate(
    body: SimulationRequest, response: SnapshotResponse | dict, canonical_inputs: dict
) -> SimulationCalculation:
    """Calculate from a verified saved snapshot, without mutating caller-owned data."""
    snapshot, request, baseline = _baseline(body, response, canonical_inputs)
    tables = canonical_inputs["tables"]
    original = []
    for row in baseline["sessions"]:
        active = row["status"] != "cancelled"
        affected = (
            active
            and row["room_id"] == str(body.room_id)
            and overlaps(
                stamp(row["starts_at"]), stamp(row["ends_at"]), body.closure_start, body.closure_end
            )
        )
        original.append(
            ScenarioSession(
                **row,
                original_room_id=row["room_id"],
                assigned_room_id=row["room_id"] if active else None,
                allocation_status="unchanged",
                affected=affected,
            )
        )
    original.sort(key=lambda r: (r.starts_at, str(r.id)))
    disrupted = deepcopy(original)
    for row in disrupted:
        if row.affected:
            row.assigned_room_id = None
            row.allocation_status = "displaced"
    reassigned = deepcopy(disrupted)
    _allocate(body, reassigned, tables)
    sessions = StageRows(baseline=original, disrupted=disrupted, reassigned=reassigned)
    stages = Stages(
        **{
            name: _summary(
                request, body, tables, getattr(sessions, name), baseline, name != "baseline"
            )
            for name in ("baseline", "disrupted", "reassigned")
        }
    )
    affected = [r for r in reassigned if r.affected]
    unresolved = [r for r in affected if r.allocation_status == "unresolved"]

    def student_count(rows):
        sections = {str(r.section_id) for r in rows}
        return len({str(r["id"]) for r in tables["student"] if str(r["section_id"]) in sections})

    impact = Impact(
        affected_sessions=len(affected),
        affected_students=student_count(affected),
        reassigned_sessions=len(affected) - len(unresolved),
        unresolved_sessions=len(unresolved),
        unresolved_students=student_count(unresolved),
    )
    deltas = {}
    for stage in ("disrupted", "reassigned"):
        before, after = stages.baseline, getattr(stages, stage)
        deltas[stage] = StageDelta(
            **{
                field: (
                    getattr(after, field) - getattr(before, field)
                    if getattr(after, field) is not None and getattr(before, field) is not None
                    else None
                )
                for field in StageDelta.model_fields
            }
        )
    code = (
        "no_affected_sessions"
        if not affected
        else "partially_unresolved"
        if unresolved
        else "all_reassigned"
    )
    message = (
        f"{impact.affected_sessions} affected classes; {impact.reassigned_sessions} reassigned; "
        f"{impact.unresolved_sessions} unresolved. "
    )
    if unresolved:
        message += "No room found by this heuristic for unresolved classes. "
    message += (
        "Uses fixed-time room allocation; does not move unaffected classes or optimize times."
    )
    metrics = baseline["metrics"]
    result = SimulationResult(
        stages=stages,
        impact=impact,
        deltas=Deltas(**deltas),
        observed_attendance=ObservedAttendance(
            **{
                k: metrics[k]
                for k in (
                    "attendance_present",
                    "attendance_recorded",
                    "attendance_expected",
                    "attendance_rate",
                )
            },
            coverage=baseline["coverage"],
        ),
        recommendation=Recommendation(code=code, message=message),
    )
    return SimulationCalculation(
        input_hash=fingerprint(
            dict(
                request=body.model_dump(mode="json"),
                baseline_input_hash=snapshot.input_hash,
                schema_version=1,
                algorithm_version=ALGORITHM_VERSION,
            )
        ),
        result_hash=fingerprint(
            dict(result=result.model_dump(mode="json"), sessions=sessions.model_dump(mode="json"))
        ),
        result=result,
        sessions=sessions,
    )
