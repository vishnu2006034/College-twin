"""Reproducible M4 extraction and purged temporal partitioning for generator v1."""

from collections import Counter, defaultdict
from datetime import datetime, time, timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from app.attendance_risk import (
    AttendanceEvent,
    RiskExample,
    RiskExampleRequest,
    RiskPolicy,
    build_example,
)
from app.generator import LOCAL, VERSION, GeneratorConfig, validate_dataset


class TemporalPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    validation_start: AwareDatetime
    test_start: AwareDatetime
    test_end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self):
        if not self.validation_start < self.test_start < self.test_end:
            raise ValueError("Split boundaries must be strictly increasing")
        return self


class ExampleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    edition_id: str
    edition_hash: str
    generator_version: str
    student_id: str
    offering_id: str
    cutoff: AwareDatetime
    horizon_end: AwareDatetime
    label_as_of: AwareDatetime
    policy: RiskPolicy
    calculation: RiskExample


def extract_examples(dataset: dict, policy: RiskPolicy = RiskPolicy()) -> list[ExampleRow]:
    """Accept clean in-memory generator artifacts, not database rows or partial exports.

    Every Monday at midnight is retained, including insufficient history/horizons.
    Outcome visibility is evaluated at each horizon end, never at extraction time.
    """
    validate_dataset(dataset)
    edition, tables = dataset["edition"], dataset["tables"]
    if edition["generator_version"] != VERSION:
        raise ValueError("Unsupported generator version")
    config = GeneratorConfig.model_validate(edition["config"])
    source_start = datetime.combine(config.start_date, time(), LOCAL)
    source_end = source_start + timedelta(weeks=config.weeks)
    offerings = {row["id"]: row for row in tables["course_offering"]}
    # Prove full timetable coverage, rather than trusting the last attendance row.
    expected_slots = {
        (source_start + timedelta(weeks=week, days=day, hours=9 + period),
         source_start + timedelta(weeks=week, days=day, hours=10 + period))
        for week in range(config.weeks) for day in range(5) for period in range(4)
    }
    slots = defaultdict(set)
    sessions = defaultdict(list)
    for row in tables["class_session"]:
        slots[offerings[row["offering_id"]]["section_id"]].add(
            (row["starts_at"], row["ends_at"])
        )
        sessions[row["offering_id"]].append(row)
    if any(slots[row["id"]] != expected_slots for row in tables["section"]):
        raise ValueError("Incomplete or incompatible generator timetable coverage")
    attendance = {
        (row["student_id"], row["session_id"]): row for row in tables["attendance"]
    }
    students = defaultdict(list)
    for row in tables["student"]:
        students[row["section_id"]].append(row)
    output = []
    for offering in sorted(offerings.values(), key=lambda row: str(row["id"])):
        for student in sorted(students[offering["section_id"]], key=lambda row: str(row["id"])):
            events = []
            for session in sessions[offering["id"]]:
                record = attendance.get((student["id"], session["id"]))
                events.append(AttendanceEvent(
                    session_id=str(session["id"]), starts_at=session["starts_at"],
                    ends_at=session["ends_at"], status=session["status"],
                    status_recorded_at=session["status_recorded_at"],
                    attendance=record["status"] if record else None,
                    recorded_at=record["recorded_at"] if record else None,
                ))
            for week in range(config.weeks):
                cutoff = source_start + timedelta(weeks=week)
                horizon_end = cutoff + timedelta(days=policy.horizon_days)
                output.append(ExampleRow(
                    edition_id=str(edition["id"]), edition_hash=edition["logical_content_hash"],
                    generator_version=edition["generator_version"], student_id=str(student["id"]),
                    offering_id=str(offering["id"]), cutoff=cutoff, horizon_end=horizon_end,
                    label_as_of=horizon_end, policy=policy,
                    calculation=build_example(RiskExampleRequest(
                        cutoff=cutoff, label_as_of=horizon_end, source_window_end=source_end,
                        events=tuple(events), policy=policy,
                    )),
                ))
    return sorted(output, key=lambda row: (row.cutoff, row.student_id, row.offering_id))


def partition_examples(rows: list[ExampleRow], plan: TemporalPlan) -> dict:
    """Partition by cutoff and purge crossing horizons; fit no preprocessing here."""
    identities = {(row.edition_id, row.student_id, row.offering_id, row.cutoff) for row in rows}
    if len(identities) != len(rows):
        raise ValueError("Duplicate example identity")
    if len({(row.edition_id, row.edition_hash, row.generator_version,
             row.policy.model_dump_json()) for row in rows}) > 1:
        raise ValueError("Partition one edition and policy at a time")
    partitions = {name: [] for name in ("train", "validation", "test")}
    exclusions = Counter()
    for row in rows:
        if row.horizon_end != row.cutoff + timedelta(days=row.policy.horizon_days):
            raise ValueError("Example horizon does not match policy")
        if row.label_as_of < row.horizon_end:
            raise ValueError("Example label visibility precedes horizon end")
        if row.cutoff >= plan.test_end:
            exclusions["outside_test_window"] += 1
            continue
        if row.cutoff < plan.validation_start:
            name, end = "train", plan.validation_start
        elif row.cutoff < plan.test_start:
            name, end = "validation", plan.test_start
        else:
            name, end = "test", plan.test_end
        if row.horizon_end > end or row.label_as_of > end:
            exclusions[f"{name}:purged_horizon"] += 1
        elif row.calculation.status != "eligible":
            exclusions[f"{name}:insufficient_data"] += 1
        elif row.calculation.label_status != "eligible":
            exclusions[f"{name}:{row.calculation.label_status}"] += 1
        elif row.calculation.features is None or row.calculation.label is None:
            raise ValueError("Eligible example is missing features or label")
        else:
            partitions[name].append(row)
    for values in partitions.values():
        values.sort(key=lambda row: (row.cutoff, row.student_id, row.offering_id))
    return {"partitions": partitions, "exclusions": dict(sorted(exclusions.items()))}


def summarize(rows: list[ExampleRow], split: dict) -> dict:
    """All-example eligibility counts are independent; split exclusions are exclusive."""
    partitions = {}
    for name, values in split["partitions"].items():
        positives = sum(row.calculation.label is True for row in values)
        partitions[name] = {
            "examples": len(values), "positive_labels": positives,
            "prevalence": positives / len(values) if values else None,
            "both_classes_present": 0 < positives < len(values),
            "first_cutoff": values[0].cutoff.isoformat() if values else None,
            "last_cutoff": values[-1].cutoff.isoformat() if values else None,
        }
    return {
        "total_examples": len(rows),
        "history_status": dict(sorted(Counter(r.calculation.status for r in rows).items())),
        "label_status": dict(sorted(Counter(r.calculation.label_status for r in rows).items())),
        "partitions": partitions, "exclusions": split["exclusions"],
    }
