"""Hand-calculated fixtures: two rooms, two pupils, two one-hour classes."""

from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.state import SnapshotRequest, calculate


def request(**changes):
    return SnapshotRequest(
        **(
            dict(
                edition_id=UUID(int=1),
                as_of="2026-01-05T10:00:00+05:30",
                window_start="2026-01-05T09:00:00+05:30",
                window_end="2026-01-05T17:00:00+05:30",
            )
            | changes
        )
    )


@pytest.fixture
def rows():
    return {
        "room": [dict(id=r, capacity=2, kind="classroom", lab_type=None) for r in ("r1", "r2")],
        "faculty": [dict(id="f1"), dict(id="f2")],
        "student": [dict(id=p, section_id="g1") for p in ("p1", "p2")],
        "course": [dict(id="c1", required_room_kind="classroom", required_lab_type=None)],
        "course_offering": [dict(id="o1", course_id="c1", faculty_id="f1", section_id="g1")],
        "class_session": [
            dict(
                id="s1",
                offering_id="o1",
                room_id="r1",
                starts_at="2026-01-05T09:00:00+05:30",
                ends_at="2026-01-05T10:00:00+05:30",
                status="held",
                status_recorded_at="2026-01-05T10:00:00+05:30",
            ),
            dict(
                id="s2",
                offering_id="o1",
                room_id="r1",
                starts_at="2026-01-05T09:30:00+05:30",
                ends_at="2026-01-05T10:30:00+05:30",
                status="scheduled",
                status_recorded_at="2026-01-01T00:00:00+05:30",
            ),
        ],
        "attendance": [
            dict(
                id="a1",
                session_id="s1",
                student_id="p1",
                status="present",
                recorded_at="2026-01-05T10:00:00+05:30",
            ),
            dict(
                id="a2",
                session_id="s1",
                student_id="p2",
                status="absent",
                recorded_at="2026-01-05T11:00:00+05:30",
            ),
        ],
    }


def test_hand_calculated_positive_and_order_independence(rows):
    result = calculate(request(), rows)
    assert result["metrics"] == dict(
        scheduled_classes=2,
        scheduled_occupied_rooms=1,
        available_rooms=1,
        booked_room_minutes=90,
        available_room_minutes=960,
        room_utilization=90 / 960,
        attendance_present=1,
        attendance_recorded=1,
        attendance_expected=2,
        attendance_rate=1,
        faculty_workload=[
            dict(faculty_id="f1", scheduled_minutes=120),
            dict(faculty_id="f2", scheduled_minutes=0),
        ],
    )
    assert result["coverage"] == dict(
        attendance_ratio=0.5, missing_attendance=1, sessions_in_window=2
    )
    assert [a["rule"] for a in result["anomalies"]] == [
        "faculty_overlap",
        "room_overlap",
        "section_overlap",
    ]
    assert all(a["session_ids"] == ["s1", "s2"] for a in result["anomalies"])
    assert calculate(request(), {k: list(reversed(v)) for k, v in rows.items()}) == result


def test_adjacent_intervals_negative_for_all_overlap_rules(rows):
    rows["class_session"][1].update(
        starts_at="2026-01-05T10:00:00+05:30", ends_at="2026-01-05T11:00:00+05:30"
    )
    result = calculate(request(), rows)
    assert result["anomalies"] == []
    assert result["metrics"]["booked_room_minutes"] == 120


@pytest.mark.parametrize("resource", ["room", "faculty", "section"])
def test_each_resource_independent(rows, resource):
    rows["course_offering"].append(dict(id="o2", course_id="c1", faculty_id="f2", section_id="g2"))
    rows["class_session"][1].update(offering_id="o2", room_id="r2")
    if resource == "room":
        rows["class_session"][1]["room_id"] = "r1"
    else:
        rows["course_offering"][1][resource + "_id"] = "f1" if resource == "faculty" else "g1"
    assert [a["rule"] for a in calculate(request(), rows)["anomalies"]] == [resource + "_overlap"]


def test_capacity_and_room_kind_positive_negative(rows):
    rows["class_session"] = rows["class_session"][:1]
    assert calculate(request(), rows)["anomalies"] == []  # size == capacity
    rows["room"][0].update(capacity=1, kind="lab", lab_type="computing")
    assert [a["rule"] for a in calculate(request(), rows)["anomalies"]] == ["capacity", "room_type"]
    rows["room"][0]["capacity"] = 2
    rows["course"][0].update(required_room_kind="lab", required_lab_type="computing")
    assert calculate(request(), rows)["anomalies"] == []
    rows["course"][0]["required_lab_type"] = "physics"
    assert [a["rule"] for a in calculate(request(), rows)["anomalies"]] == ["room_type"]


def test_future_status_and_attendance_do_not_leak(rows):
    early = calculate(request(as_of="2026-01-05T09:45:00+05:30"), rows)
    assert early["metrics"]["attendance_expected"] == 0
    assert early["metrics"]["attendance_rate"] is None
    rows["class_session"][1].update(
        status="cancelled", status_recorded_at="2026-01-05T11:00:00+05:30"
    )
    assert len(calculate(request(), rows)["anomalies"]) == 3
    late = calculate(request(as_of="2026-01-05T11:00:00+05:30"), rows)
    assert late["anomalies"] == []
    assert late["metrics"]["scheduled_classes"] == 1
    assert late["metrics"]["attendance_rate"] == 0.5
    assert late["coverage"]["attendance_ratio"] == 1


def test_three_way_pairs_are_unique(rows):
    third = dict(rows["class_session"][1], id="s3")
    rows["class_session"].append(third)
    assert len(calculate(request(), rows)["anomalies"]) == 9
    assert calculate(request(), rows)["metrics"]["booked_room_minutes"] == 90


def test_window_clipping_and_empty_weekend(rows):
    result = calculate(
        request(window_start="2026-01-05T09:45:00+05:30", window_end="2026-01-05T10:15:00+05:30"),
        rows,
    )
    assert result["metrics"]["booked_room_minutes"] == 30
    assert result["metrics"]["available_room_minutes"] == 60
    weekend = calculate(
        request(
            window_start="2026-01-10T00:00:00+05:30",
            window_end="2026-01-11T00:00:00+05:30",
            as_of="2026-01-10T12:00:00+05:30",
        ),
        rows,
    )
    assert weekend["metrics"]["room_utilization"] is None
    assert weekend["metrics"]["scheduled_classes"] == 0
    assert weekend["anomalies"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of": "2026-01-05T10:00:00"},
        {"as_of": "2026-01-05T17:00:00+05:30"},
        {"window_end": "2026-01-05T09:00:00+05:30"},
        {"window_end": "2026-01-13T17:00:00+05:30"},
    ],
)
def test_invalid_contract(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_inputs_not_mutated(rows):
    before = deepcopy(rows)
    calculate(request(), rows)
    assert rows == before
