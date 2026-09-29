"""Independent M3 arithmetic, feasibility and frozen-input regression fixtures."""

from copy import deepcopy
from itertools import product
from uuid import UUID

import pytest
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.generator import GeneratorConfig, generate
from app.simulation import SimulationError, SimulationRequest, simulate
from app.state import SnapshotRequest, SnapshotResponse, calculate, fingerprint


def uid(n):
    return str(UUID(int=n))


def at(hour, day="2026-01-05"):
    return f"{day}T{hour}:00+05:30"


def closure(**changes):
    return SimulationRequest(
        **(
            dict(
                snapshot_id=uid(1),
                type="room_unavailability",
                room_id=uid(10),
                closure_start=at("10:00"),
                closure_end=at("12:00"),
            )
            | changes
        )
    )


def snapshot(tables, **changes):
    request = SnapshotRequest(
        **(
            dict(
                edition_id=uid(2),
                as_of=at("09:00"),
                window_start=at("09:00"),
                window_end=at("17:00"),
            )
            | changes
        )
    )
    inputs = jsonable_encoder(dict(request=request.model_dump(mode="json"), tables=tables))
    state = calculate(request, inputs["tables"])
    inputs["sessions"] = state["sessions"]
    response = SnapshotResponse(
        **request.model_dump(),
        id=uid(1),
        input_hash=fingerprint(inputs),
        edition_hash="fixture-edition",
        created_at=at("09:00"),
        **{k: state[k] for k in ("metrics", "coverage", "anomalies")},
    )
    return response, inputs


def run(tables, body=None, **changes):
    response, inputs = snapshot(tables, **changes)
    before = deepcopy((tables, response, inputs))
    result = simulate(body or closure(), response, inputs)
    assert (tables, response, inputs) == before
    return result


@pytest.fixture
def tables():
    return dict(
        room=[
            dict(id=uid(n), capacity=size, kind="classroom", lab_type=None)
            for n, size in ((10, 40), (11, 50), (12, 45), (13, 20))
        ],
        faculty=[dict(id=uid(n)) for n in (20, 21, 22)],
        student=[dict(id=uid(1000 + n), section_id=uid(30 if n < 40 else 31)) for n in range(70)],
        course=[dict(id=uid(40), required_room_kind="classroom", required_lab_type=None)],
        course_offering=[
            dict(id=uid(50 + n), course_id=uid(40), faculty_id=uid(20 + n), section_id=uid(30 + n))
            for n in range(2)
        ],
        class_session=[
            dict(
                id=uid(60 + n),
                offering_id=uid(50 + n),
                room_id=uid(10 + n),
                starts_at=at("10:00"),
                ends_at=at("11:00"),
                status="held",
                status_recorded_at=at("11:00"),
            )
            for n in range(2)
        ],
        attendance=[],
    )


def test_hand_calculated_reassignment_and_comparisons(tables):
    result = run(tables)
    baseline, disrupted, reassigned = (
        result.result.stages.baseline,
        result.result.stages.disrupted,
        result.result.stages.reassigned,
    )
    assert result.result.impact.model_dump() == dict(
        affected_sessions=1,
        affected_students=40,
        reassigned_sessions=1,
        unresolved_sessions=0,
        unresolved_students=0,
    )
    assert (
        baseline.available_room_minutes,
        disrupted.available_room_minutes,
        reassigned.available_room_minutes,
    ) == (1920, 1800, 1800)
    assert (
        baseline.booked_room_minutes,
        disrupted.booked_room_minutes,
        reassigned.booked_room_minutes,
    ) == (120, 60, 120)
    assert (baseline.room_utilization, disrupted.room_utilization, reassigned.room_utilization) == (
        120 / 1920,
        60 / 1800,
        120 / 1800,
    )
    for stage in (baseline, disrupted, reassigned):
        assert stage.scheduled_classes == 2
        assert stage.assigned_classes + stage.unassigned_classes == 2
        assert stage.anomalies == []
        assert [r.scheduled_minutes for r in stage.required_faculty_minutes] == [60, 60, 0]
    assert [r.scheduled_minutes for r in disrupted.assigned_faculty_minutes] == [0, 60, 0]
    row = result.sessions.reassigned[0]
    assert row.assigned_room_id == UUID(uid(12))
    assert row.room_id == row.original_room_id == UUID(uid(10))
    assert row.status == "scheduled"  # Future held status is not consulted.
    assert row.candidate_summary.model_dump() == dict(
        total_rooms=4,
        rejected_type=0,
        rejected_capacity=1,
        rejected_closure=1,
        rejected_room_busy=1,
        rejected_faculty_busy=0,
        rejected_section_busy=0,
        feasible_count=1,
    )
    assert result.result.deltas.disrupted.assigned_classes == -1
    assert result.result.deltas.reassigned.available_room_minutes == -120
    assert result.result.deltas.reassigned.room_utilization == pytest.approx(
        120 / 1800 - 120 / 1920
    )
    assert result.result.observed_attendance.attendance_rate is None
    assert result.result.recommendation.code == "all_reassigned"


def test_unresolved_demand_is_not_cancelled_or_deleted(tables):
    tables["room"] = [r for r in tables["room"] if r["id"] != uid(12)]
    result = run(tables)
    row = result.sessions.reassigned[0]
    assert row.allocation_status == "unresolved"
    assert row.assigned_room_id is None
    assert row.status == "scheduled"
    assert row.reason_code == "no_feasible_candidate"
    assert result.result.stages.reassigned.unassigned_classes == 1
    assert result.result.impact.unresolved_students == 40
    assert "No room found by this heuristic" in result.result.recommendation.message


@pytest.mark.parametrize(
    "capacity,kind,subtype,expected",
    [
        (40, "classroom", None, "reassigned"),
        (39, "classroom", None, "unresolved"),
        (45, "lab", "computing", "unresolved"),
    ],
)
def test_candidate_capacity_and_kind(tables, capacity, kind, subtype, expected):
    tables["room"][2].update(capacity=capacity, kind=kind, lab_type=subtype)
    assert run(tables).sessions.reassigned[0].allocation_status == expected


@pytest.mark.parametrize(
    "subtype,expected", [("computing", "reassigned"), ("physics", "unresolved")]
)
def test_exact_lab_subtype(tables, subtype, expected):
    tables["class_session"] = tables["class_session"][:1]
    tables["course"][0].update(required_room_kind="lab", required_lab_type="computing")
    tables["room"][0].update(kind="lab", lab_type="computing")
    tables["room"][2].update(kind="lab", lab_type=subtype)
    assert run(tables).sessions.reassigned[0].allocation_status == expected


def test_room_uuid_breaks_spare_capacity_tie(tables):
    tables["room"][3]["capacity"] = 45
    assert run(tables).sessions.reassigned[0].assigned_room_id == UUID(uid(12))


def test_spare_capacity_precedes_uuid_and_candidate_counts_partition_inventory(tables):
    tables["room"][3]["capacity"] = 41
    row = run(tables).sessions.reassigned[0]
    assert row.assigned_room_id == UUID(uid(13))
    counts = row.candidate_summary.model_dump()
    assert counts["feasible_count"] == 2
    assert counts.pop("total_rooms") == sum(counts.values())


@pytest.mark.parametrize(
    "start,end,affected",
    [
        ("09:00", "10:00", 0),
        ("11:00", "12:00", 0),
        ("10:30", "10:45", 1),
    ],
)
def test_half_open_and_partial_closures(tables, start, end, affected):
    result = run(tables, closure(closure_start=at(start), closure_end=at(end)))
    assert result.result.impact.affected_sessions == affected
    assert result.result.stages.reassigned.booked_room_minutes == 120
    assert result.result.stages.disrupted.booked_room_minutes == 120 - 60 * affected


def test_multiple_displaced_classes_reuse_room_and_deduplicate_students(tables):
    tables["class_session"].append(
        dict(
            tables["class_session"][0],
            id=uid(62),
            starts_at=at("11:00"),
            ends_at=at("12:00"),
            status_recorded_at=at("12:00"),
        )
    )
    result = run(tables)
    moved = [r for r in result.sessions.reassigned if r.affected]
    # Same closed room has no overlapping baseline classes; destinations can be reused.
    assert [r.assigned_room_id for r in moved] == [UUID(uid(12)), UUID(uid(12))]
    assert result.result.impact.affected_students == 40
    assert result.result.impact.affected_sessions == 2


@pytest.mark.parametrize("recorded,affected", [("08:00", 0), ("09:00", 0), ("09:01", 1)])
def test_cancellation_respects_cutoff(tables, recorded, affected):
    tables["class_session"][0].update(status="cancelled", status_recorded_at=at(recorded))
    result = run(tables)
    assert result.result.impact.affected_sessions == affected
    row = result.sessions.reassigned[0]
    if not affected:
        assert row.status == "cancelled"
        assert row.assigned_room_id is None
        assert row.allocation_status == "unchanged"
        assert result.result.stages.baseline.scheduled_classes == 1


@pytest.mark.parametrize(
    "rule", ["room_overlap", "faculty_overlap", "section_overlap", "capacity", "room_type"]
)
def test_all_baseline_conflict_rules_reject(tables, rule):
    if rule == "room_overlap":
        tables["class_session"][1]["room_id"] = uid(10)
    elif rule == "faculty_overlap":
        tables["course_offering"][1]["faculty_id"] = uid(20)
    elif rule == "section_overlap":
        tables["course_offering"][1]["section_id"] = uid(30)
    elif rule == "capacity":
        tables["room"][0]["capacity"] = 39
    else:
        tables["room"][0].update(kind="lab", lab_type="physics")
    response, inputs = snapshot(tables)
    assert rule in {a.rule for a in response.anomalies}
    before = deepcopy(inputs)
    with pytest.raises(SimulationError) as error:
        simulate(closure(), response, inputs)
    assert error.value.status_code == 409
    assert error.value.code == "infeasible_baseline"
    assert inputs == before


@pytest.mark.parametrize("mutation", ["starts_before", "ends_after", "held", "later_cutoff"])
def test_unsuitable_planning_baseline_rejects(tables, mutation):
    changes = {}
    if mutation == "starts_before":
        tables["class_session"][0]["starts_at"] = at("08:30")
    elif mutation == "ends_after":
        tables["class_session"][0]["ends_at"] = at("17:30")
    elif mutation == "held":
        tables["class_session"][0]["status_recorded_at"] = at("08:00")
    else:
        changes["as_of"] = at("09:30")
    with pytest.raises(SimulationError) as error:
        run(tables, **changes)
    assert error.value.code == "planning_baseline_required"


@pytest.mark.parametrize(
    "changes",
    [
        {"closure_start": "2026-01-05T10:00:00"},
        {"closure_end": at("10:00")},
        {"closure_end": at("09:00")},
        {"type": "attendance_shock"},
        {"extra": True},
    ],
)
def test_request_validation(changes):
    with pytest.raises(ValidationError):
        closure(**changes)


@pytest.mark.parametrize(
    "changes,status,code",
    [
        ({"closure_start": at("08:00")}, 422, "closure_outside_window"),
        ({"closure_end": at("17:01")}, 422, "closure_outside_window"),
        ({"room_id": uid(999)}, 404, "room_not_found"),
        ({"snapshot_id": uid(999)}, 409, "snapshot_mismatch"),
    ],
)
def test_contextual_request_validation(tables, changes, status, code):
    with pytest.raises(SimulationError) as error:
        run(tables, closure(**changes))
    assert (error.value.status_code, error.value.code) == (status, code)


@pytest.mark.parametrize(
    "corruption", ["hash", "schema", "session", "metrics", "edition", "missing"]
)
def test_corrupt_saved_snapshot_rejected(tables, corruption):
    response, inputs = snapshot(tables)
    response = response.model_dump(mode="json")
    if corruption == "hash":
        inputs["tables"]["room"][0]["capacity"] = 100
    elif corruption == "schema":
        response["schema_version"] = 2
    elif corruption == "session":
        inputs["sessions"][0]["room_id"] = uid(12)
        response["input_hash"] = fingerprint(inputs)
    elif corruption == "metrics":
        response["metrics"]["scheduled_classes"] = 500
    elif corruption == "edition":
        response["edition_id"] = uid(999)
    else:
        del inputs["tables"]
    with pytest.raises(SimulationError) as error:
        simulate(closure(), response, inputs)
    assert error.value.code == "invalid_baseline"


def test_order_independence_replay_and_result_hash(tables):
    first = run(tables)
    assert run(tables) == first
    second = run({key: list(reversed(rows)) for key, rows in tables.items()})
    assert first.result == second.result
    assert first.sessions == second.sessions
    assert first.result_hash == second.result_hash
    assert first.result_hash == fingerprint(
        dict(
            result=first.result.model_dump(mode="json"),
            sessions=first.sessions.model_dump(mode="json"),
        )
    )
    # Baseline hash records exact stored inputs, including their source array order.
    equivalent = run(
        tables, closure(closure_start="2026-01-05T04:30:00Z", closure_end="2026-01-05T06:30:00Z")
    )
    assert equivalent == first


def test_empty_baseline_closed_at_cutoff_and_zero_availability(tables):
    tables["class_session"] = []
    tables["room"] = tables["room"][:1]
    result = run(tables, closure(closure_start=at("09:00"), closure_end=at("17:00")))
    assert result.result.recommendation.code == "no_affected_sessions"
    assert result.result.stages.baseline.available_rooms == 1
    for stage in (result.result.stages.disrupted, result.result.stages.reassigned):
        assert stage.available_room_minutes == 0
        assert stage.available_rooms == 0
        assert stage.room_utilization is None
    assert result.result.deltas.reassigned.room_utilization is None


def test_weekend_closure_has_no_teaching_minutes(tables):
    tables["class_session"] = []
    start, end = at("09:00", "2026-01-10"), at("17:00", "2026-01-10")
    result = run(
        tables,
        closure(closure_start=start, closure_end=end),
        as_of=start,
        window_start=start,
        window_end=end,
    )
    assert result.result.stages.baseline.room_utilization is None
    assert result.result.stages.reassigned.available_room_minutes == 0
    assert result.result.deltas.reassigned.available_room_minutes == 0


def test_full_day_closure_preserves_unassigned_demand_with_no_availability(tables):
    tables["room"] = tables["room"][:1]
    tables["class_session"] = tables["class_session"][:1]
    result = run(tables, closure(closure_start=at("09:00"), closure_end=at("17:00")))
    stage = result.result.stages.reassigned
    assert (stage.scheduled_classes, stage.assigned_classes, stage.unassigned_classes) == (1, 0, 1)
    assert stage.available_room_minutes == 0
    assert stage.booked_room_minutes == 0
    assert stage.room_utilization is None
    assert result.result.impact.unresolved_students == 40


def test_closure_outside_teaching_hours_and_clipped_denominator(tables):
    tables["class_session"] = []
    result = run(
        tables,
        closure(closure_start=at("07:00"), closure_end=at("08:00")),
        as_of=at("07:00"),
        window_start=at("07:00"),
    )
    assert result.result.deltas.reassigned.available_room_minutes == 0
    result = run(
        tables,
        closure(closure_start=at("08:00"), closure_end=at("10:00")),
        as_of=at("07:00"),
        window_start=at("07:00"),
    )
    assert result.result.deltas.reassigned.available_room_minutes == -60


def test_occupied_rooms_at_cutoff_exclude_closed_room(tables):
    for row in tables["class_session"]:
        row.update(starts_at=at("09:00"), ends_at=at("10:00"))
    result = run(tables, closure(closure_start=at("09:00")))
    assert result.result.stages.baseline.scheduled_occupied_rooms == 2
    assert result.result.stages.disrupted.scheduled_occupied_rooms == 1
    assert result.result.stages.disrupted.available_rooms == 2
    assert result.result.stages.reassigned.scheduled_occupied_rooms == 2
    assert result.result.stages.reassigned.available_rooms == 1


@pytest.mark.parametrize("first_blocked,second_blocked", list(product((False, True), repeat=2)))
def test_small_exhaustive_fixed_time_assignments(tables, first_blocked, second_blocked):
    # Two adjacent displaced classes. Enumerate destinations independently of the engine.
    tables["room"] = tables["room"][:3]
    tables["room"][1]["capacity"] = 40
    tables["room"][2]["capacity"] = 40
    first = dict(tables["class_session"][0])
    second = dict(first, id=uid(62), starts_at=at("11:00"), ends_at=at("12:00"))
    tables["class_session"] = [first, second]
    for index, blocked in enumerate((first_blocked, second_blocked)):
        if blocked:
            tables["class_session"].append(
                dict(
                    first,
                    id=uid(70 + index),
                    offering_id=uid(51),
                    room_id=uid(11 + index),
                    starts_at=at("10:00" if index == 0 else "11:00"),
                    ends_at=at("11:00" if index == 0 else "12:00"),
                )
            )
    feasible = [
        assignment
        for assignment in product((11, 12), repeat=2)
        if not (first_blocked and assignment[0] == 11)
        and not (second_blocked and assignment[1] == 12)
    ]
    result = run(tables)
    actual = tuple(r.assigned_room_id.int for r in result.sessions.reassigned if r.affected)
    assert actual == min(feasible)
    assert result.result.impact.unresolved_sessions == 0


def test_real_generator_frozen_week_inputs_are_supported():
    generated = generate(GeneratorConfig(weeks=1, students_per_section=3))
    tables = generated["tables"]
    response, inputs = snapshot(
        tables, edition_id=generated["edition"]["id"], window_end=at("09:00", "2026-01-12")
    )
    body = closure(
        room_id=tables["class_session"][0]["room_id"],
        closure_start=at("09:00"),
        closure_end=at("17:00"),
    )
    before = deepcopy(inputs)
    result = simulate(body, response, inputs)
    assert result.result.stages.baseline.scheduled_classes == 160
    assert result.result.impact.affected_sessions > 0
    assert result.result.stages.reassigned.anomalies == []
    assert result.result.impact.reassigned_sessions + result.result.impact.unresolved_sessions == (
        result.result.impact.affected_sessions
    )
    assert inputs == before
