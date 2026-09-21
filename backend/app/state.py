"""Pure dated-state calculations. No database, clock or HTTP dependencies."""

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, time, timedelta, timezone
from itertools import combinations
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

LOCAL = timezone(timedelta(hours=5, minutes=30))


class SnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edition_id: UUID
    as_of: AwareDatetime
    window_start: AwareDatetime
    window_end: AwareDatetime

    @model_validator(mode="after")
    def interval(self):
        for field in ("as_of", "window_start", "window_end"):
            setattr(self, field, getattr(self, field).astimezone(UTC))
        if not timedelta(0) < self.window_end - self.window_start <= timedelta(days=7):
            raise ValueError("Window must be positive and at most seven days")
        if not self.window_start <= self.as_of < self.window_end:
            raise ValueError("Cutoff must be inside the reporting window")
        return self


class Anomaly(BaseModel):
    rule: Literal["room_overlap", "faculty_overlap", "section_overlap", "capacity", "room_type"]
    resource_id: str
    session_ids: list[str]
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class Workload(BaseModel):
    faculty_id: str
    scheduled_minutes: float


class Metrics(BaseModel):
    scheduled_classes: int
    scheduled_occupied_rooms: int
    available_rooms: int
    booked_room_minutes: float
    available_room_minutes: float
    room_utilization: float | None
    attendance_present: int
    attendance_recorded: int
    attendance_expected: int
    attendance_rate: float | None
    faculty_workload: list[Workload]


class Coverage(BaseModel):
    attendance_ratio: float | None
    missing_attendance: int
    sessions_in_window: int


class SnapshotResponse(SnapshotRequest):
    id: UUID
    schema_version: Literal[1] = 1
    synthetic_data_only: Literal[True] = True
    input_hash: str
    edition_hash: str
    created_at: AwareDatetime
    metrics: Metrics
    coverage: Coverage
    anomalies: list[Anomaly]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def minutes(intervals):
    """Length of a union, never double-counting overlapping room bookings."""
    total = 0.0
    end = None
    for start, stop in sorted(intervals):
        start = max(start, end) if end else start
        total += max(0, (stop - start).total_seconds() / 60)
        end = max(end, stop) if end else stop
    return total


def calculate(request: SnapshotRequest, tables: dict):
    start, end, cutoff = request.window_start, request.window_end, request.as_of
    rooms = {str(r["id"]): r for r in tables["room"]}
    offerings = {str(r["id"]): r for r in tables["course_offering"]}
    courses = {str(r["id"]): r for r in tables["course"]}
    sizes = Counter(str(r["section_id"]) for r in tables["student"])
    sessions = []
    for row in tables["class_session"]:
        a, b = stamp(row["starts_at"]), stamp(row["ends_at"])
        if a >= end or b <= start:
            continue
        offering = offerings[str(row["offering_id"])]
        status = row["status"] if stamp(row["status_recorded_at"]) <= cutoff else "scheduled"
        sessions.append(
            dict(
                id=str(row["id"]),
                room_id=str(row["room_id"]),
                faculty_id=str(offering["faculty_id"]),
                section_id=str(offering["section_id"]),
                course_id=str(offering["course_id"]),
                starts_at=a.isoformat(),
                ends_at=b.isoformat(),
                status=status,
            )
        )
    sessions.sort(key=lambda r: r["id"])
    active = [s for s in sessions if s["status"] != "cancelled"]
    anomalies = []

    def add(rule, resource, rows, a, b):
        anomalies.append(
            dict(
                rule=rule,
                resource_id=resource,
                session_ids=sorted(r["id"] for r in rows),
                starts_at=a.isoformat(),
                ends_at=b.isoformat(),
            )
        )

    for left, right in combinations(active, 2):
        a = max(start, stamp(left["starts_at"]), stamp(right["starts_at"]))
        b = min(end, stamp(left["ends_at"]), stamp(right["ends_at"]))
        if a >= b:
            continue
        for resource in ("room", "faculty", "section"):
            key = resource + "_id"
            if left[key] == right[key]:
                add(resource + "_overlap", left[key], [left, right], a, b)
    for row in active:
        room, course = rooms[row["room_id"]], courses[row["course_id"]]
        a, b = max(start, stamp(row["starts_at"])), min(end, stamp(row["ends_at"]))
        if sizes[row["section_id"]] > room["capacity"]:
            add("capacity", row["room_id"], [row], a, b)
        if (
            room["kind"] != course["required_room_kind"]
            or room["lab_type"] != course["required_lab_type"]
        ):
            add("room_type", row["room_id"], [row], a, b)
    anomalies.sort(key=lambda r: (r["rule"], r["resource_id"], r["session_ids"]))

    teaching = []
    day = start.astimezone(LOCAL).date()
    while day <= end.astimezone(LOCAL).date():
        a = max(start, datetime.combine(day, time(9), LOCAL))
        b = min(end, datetime.combine(day, time(17), LOCAL))
        if day.weekday() < 5 and a < b:
            teaching.append((a, b))
        day += timedelta(days=1)
    booked = 0.0
    for room_id in rooms:
        intervals = []
        for row in active:
            if row["room_id"] == room_id:
                for a, b in teaching:
                    a, b = max(a, stamp(row["starts_at"])), min(b, stamp(row["ends_at"]))
                    if a < b:
                        intervals.append((a, b))
        booked += minutes(intervals)
    available = minutes(teaching) * len(rooms)
    occupied = {
        s["room_id"] for s in active if stamp(s["starts_at"]) <= cutoff < stamp(s["ends_at"])
    }
    held = {s["id"]: s for s in active if s["status"] == "held" and stamp(s["ends_at"]) <= cutoff}
    records = [
        r
        for r in tables["attendance"]
        if str(r["session_id"]) in held and stamp(r["recorded_at"]) <= cutoff
    ]
    expected = sum(sizes[s["section_id"]] for s in held.values())
    present = sum(r["status"] == "present" for r in records)
    workload = Counter({str(f["id"]): 0.0 for f in tables["faculty"]})
    for row in active:
        workload[row["faculty_id"]] += (
            min(end, stamp(row["ends_at"])) - max(start, stamp(row["starts_at"]))
        ).total_seconds() / 60
    return dict(
        metrics=dict(
            scheduled_classes=len(active),
            scheduled_occupied_rooms=len(occupied),
            available_rooms=len(rooms) - len(occupied),
            booked_room_minutes=booked,
            available_room_minutes=available,
            room_utilization=booked / available if available else None,
            attendance_present=present,
            attendance_recorded=len(records),
            attendance_expected=expected,
            attendance_rate=present / len(records) if records else None,
            faculty_workload=[
                dict(faculty_id=k, scheduled_minutes=v) for k, v in sorted(workload.items())
            ],
        ),
        coverage=dict(
            attendance_ratio=len(records) / expected if expected else None,
            missing_attendance=expected - len(records),
            sessions_in_window=len(sessions),
        ),
        anomalies=anomalies,
        sessions=sessions,
    )
