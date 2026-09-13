"""Reproducible, clearly synthetic relational data. No wall-clock inputs."""

import hashlib
import json
import random
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from faker import Faker
from pydantic import BaseModel, Field, model_validator

VERSION = "1.0.0"
LOCAL = timezone(timedelta(hours=5, minutes=30))


class GeneratorConfig(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    weeks: int = Field(default=16, ge=1, le=52)
    students_per_section: int = Field(default=30, ge=1, le=40)
    start_date: date = date(2026, 1, 5)

    @model_validator(mode="after")
    def monday(self):
        if self.start_date.weekday() != 0:
            raise ValueError("start_date must be a Monday")
        return self


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(tables: dict) -> str:
    ordered = {name: sorted(rows, key=lambda row: str(row["id"])) for name, rows in tables.items()}
    return hashlib.sha256(canonical(ordered).encode()).hexdigest()


def generate(config: GeneratorConfig) -> dict:
    edition_id = uuid5(
        NAMESPACE_URL, f"college-twin:{VERSION}:{canonical(config.model_dump(mode='json'))}"
    )
    rng = random.Random(config.seed)
    fake = Faker("en_US")
    fake.seed_instance(config.seed)
    tables: dict[str, list[dict]] = {
        name: []
        for name in (
            "department",
            "program",
            "batch",
            "section",
            "student",
            "faculty",
            "course",
            "term",
            "room",
            "course_offering",
            "class_session",
            "attendance",
        )
    }

    def add(table, key, **fields):
        row = {"id": uuid5(edition_id, f"{table}:{key}"), "edition_id": edition_id, **fields}
        tables[table].append(row)
        return row["id"]

    term_id = add(
        "term",
        0,
        start_date=config.start_date,
        end_date=config.start_date + timedelta(weeks=config.weeks),
    )
    rooms = [
        add(
            "room",
            n,
            code=f"{'LAB' if n >= 10 else 'ROOM'}-{n + 1:02}",
            capacity=40 if n >= 10 else 40 + n % 3 * 5,
            kind="lab" if n >= 10 else "classroom",
            lab_type="computing" if n >= 10 else None,
        )
        for n in range(12)
    ]
    student_number = 0
    for dep in range(2):
        dep_id = add("department", dep, code=f"DEPT-{dep + 1}")
        prog_id = add("program", dep, department_id=dep_id, code=f"PROG-{dep + 1}")
        teachers = [
            add(
                "faculty",
                dep * 8 + n,
                department_id=dep_id,
                synthetic_label=f"Faculty-{dep * 8 + n + 1:03}",
            )
            for n in range(8)
        ]
        courses = [
            add(
                "course",
                dep * 4 + n,
                department_id=dep_id,
                code=f"COURSE-{dep + 1}-{n + 1}",
                required_room_kind="lab" if n == 3 else "classroom",
                required_lab_type="computing" if n == 3 else None,
            )
            for n in range(4)
        ]
        for batch_n in range(2):
            batch_id = add(
                "batch", dep * 2 + batch_n, program_id=prog_id, start_year=2024 + batch_n
            )
            for section_n in range(2):
                local_section = batch_n * 2 + section_n
                section_index = dep * 4 + local_section
                sec_id = add("section", section_index, batch_id=batch_id, code=f"S-{section_n + 1}")
                students = []
                for _ in range(config.students_per_section):
                    student_number += 1
                    # Faker supplies an obviously artificial suffix; never generate real-looking PII.
                    sid = add(
                        "student",
                        student_number,
                        section_id=sec_id,
                        synthetic_label=f"Student-{student_number:03}-{fake.bothify('??').upper()}",
                    )
                    students.append((sid, rng.uniform(0.60, 0.98)))
                offerings = [
                    add(
                        "course_offering",
                        section_index * 4 + n,
                        course_id=courses[n],
                        section_id=sec_id,
                        faculty_id=teachers[local_section * 2 + n % 2],
                        term_id=term_id,
                    )
                    for n in range(4)
                ]
                for week in range(config.weeks):
                    week_effect = rng.uniform(-0.10, 0.06)
                    for day in range(5):
                        # Four daily periods; theory rotates, with one lab per section/week.
                        for period in range(4):
                            subject = (day + period) % 4
                            # Each section's lab has its own period on Friday. Other days use theory.
                            if subject == 3 and day != 4:
                                subject = day % 3
                            if day == 4:
                                subject = 3 if period == local_section else period % 3
                            start = datetime.combine(
                                config.start_date + timedelta(weeks=week, days=day),
                                datetime.min.time(),
                                LOCAL,
                            ).replace(hour=9 + period)
                            start = start.astimezone(UTC)
                            end = start + timedelta(hours=1)
                            room_id = rooms[10 + dep] if subject == 3 else rooms[section_index]
                            key = f"{section_index}:{week}:{day}:{period}"
                            session_id = add(
                                "class_session",
                                key,
                                offering_id=offerings[subject],
                                room_id=room_id,
                                starts_at=start,
                                ends_at=end,
                                status="held",
                                status_recorded_at=end,
                            )
                            for sid, tendency in students:
                                present = rng.random() < max(
                                    0.05, min(0.99, tendency + week_effect)
                                )
                                add(
                                    "attendance",
                                    f"{session_id}:{sid}",
                                    session_id=session_id,
                                    student_id=sid,
                                    status="present" if present else "absent",
                                    recorded_at=end + timedelta(minutes=5),
                                )
    return {
        "edition": {
            "id": edition_id,
            "seed": config.seed,
            "generator_version": VERSION,
            "config": config.model_dump(mode="json"),
            "logical_content_hash": content_hash(tables),
        },
        "tables": tables,
    }


def validate_dataset(dataset: dict) -> dict[str, int]:
    """Validate SQL-like integrity and clean timetable invariants before any writes."""
    tables = dataset["tables"]
    edition_id = dataset["edition"]["id"]
    expected_tables = {
        "department",
        "program",
        "batch",
        "section",
        "student",
        "faculty",
        "course",
        "term",
        "room",
        "course_offering",
        "class_session",
        "attendance",
    }
    if set(tables) != expected_tables:
        raise ValueError("Unexpected or missing domain tables")
    indexed = {}
    for name, rows in tables.items():
        indexed[name] = {row["id"]: row for row in rows}
        if len(indexed[name]) != len(rows):
            raise ValueError(f"Duplicate ID in {name}")
        if any(row["edition_id"] != edition_id for row in rows):
            raise ValueError(f"Cross-edition row in {name}")
    references = {
        "program": {"department_id": "department"},
        "batch": {"program_id": "program"},
        "section": {"batch_id": "batch"},
        "student": {"section_id": "section"},
        "faculty": {"department_id": "department"},
        "course": {"department_id": "department"},
        "course_offering": {
            "course_id": "course",
            "section_id": "section",
            "faculty_id": "faculty",
            "term_id": "term",
        },
        "class_session": {"offering_id": "course_offering", "room_id": "room"},
        "attendance": {"session_id": "class_session", "student_id": "student"},
    }
    for table, refs in references.items():
        for row in tables[table]:
            for field, parent in refs.items():
                if row[field] not in indexed[parent]:
                    raise ValueError(f"Missing {table}.{field}")
    section_sizes: dict[UUID, int] = {}
    for row in tables["student"]:
        section_sizes[row["section_id"]] = section_sizes.get(row["section_id"], 0) + 1
    bookings: dict[tuple, list] = {}
    for row in tables["class_session"]:
        offering = indexed["course_offering"][row["offering_id"]]
        room = indexed["room"][row["room_id"]]
        course = indexed["course"][offering["course_id"]]
        term = indexed["term"][offering["term_id"]]
        start, end = row["starts_at"], row["ends_at"]
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("Invalid session interval")
        if not term["start_date"] <= start.astimezone(LOCAL).date() < term["end_date"]:
            raise ValueError("Session outside term")
        if row["status"] != "held" or row["status_recorded_at"] < end:
            raise ValueError("Generated sessions must be held and recorded after end")
        if room["capacity"] < section_sizes[offering["section_id"]]:
            raise ValueError("Room over capacity")
        if (room["kind"], room["lab_type"]) != (
            course["required_room_kind"],
            course["required_lab_type"],
        ):
            raise ValueError("Incompatible room")
        for kind, entity in (
            ("room", row["room_id"]),
            ("faculty", offering["faculty_id"]),
            ("section", offering["section_id"]),
        ):
            bookings.setdefault((kind, entity), []).append((start, end))
    for (kind, _), intervals in bookings.items():
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            if previous[1] > current[0]:
                raise ValueError(f"Overlapping {kind} sessions")
    seen = set()
    for row in tables["attendance"]:
        session = indexed["class_session"][row["session_id"]]
        offering = indexed["course_offering"][session["offering_id"]]
        if indexed["student"][row["student_id"]]["section_id"] != offering["section_id"]:
            raise ValueError("Attendance student belongs to another section")
        if row["status"] not in ("present", "absent") or row["recorded_at"] < session["ends_at"]:
            raise ValueError("Invalid attendance record")
        key = (row["session_id"], row["student_id"])
        if key in seen:
            raise ValueError("Duplicate attendance")
        seen.add(key)
    expected_count = sum(
        section_sizes[indexed["course_offering"][s["offering_id"]]["section_id"]]
        for s in tables["class_session"]
    )
    if len(seen) != expected_count:
        raise ValueError("Incomplete clean attendance dataset")
    if content_hash(tables) != dataset["edition"]["logical_content_hash"]:
        raise ValueError("Content hash mismatch")
    return {name: len(rows) for name, rows in tables.items()}
