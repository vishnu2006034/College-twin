from copy import deepcopy
from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.generator import GeneratorConfig, content_hash, generate
from app.risk_dataset import TemporalPlan, extract_examples, partition_examples, summarize


@pytest.fixture(scope="module")
def dataset():
    return generate(GeneratorConfig(weeks=16, students_per_section=1))


@pytest.fixture(scope="module")
def rows(dataset):
    return extract_examples(dataset)


def plan(rows):
    start = rows[0].cutoff
    return TemporalPlan(validation_start=start + timedelta(weeks=8),
                        test_start=start + timedelta(weeks=12),
                        test_end=start + timedelta(weeks=16))


def test_extraction_membership_counts_and_identity(dataset, rows):
    assert len(rows) == 8 * 4 * 16
    students = {str(r["id"]): r for r in dataset["tables"]["student"]}
    offerings = {str(r["id"]): r for r in dataset["tables"]["course_offering"]}
    for row in rows:
        assert students[row.student_id]["section_id"] == offerings[row.offering_id]["section_id"]
        assert row.edition_hash == dataset["edition"]["logical_content_hash"]
        assert row.label_as_of == row.horizon_end
    assert all(r.calculation.status == "insufficient_data" for r in rows[:32])
    assert all(r.calculation.label_status == "horizon_incomplete" for r in rows[-32:])


def test_independent_generated_attendance_arithmetic(dataset, rows):
    row = next(r for r in rows if r.calculation.features is not None)
    sessions = {str(s["id"]): s for s in dataset["tables"]["class_session"]
                if str(s["offering_id"]) == row.offering_id
                and row.cutoff - timedelta(days=28) <= s["starts_at"]
                and s["ends_at"] <= row.cutoff}
    records = [a for a in dataset["tables"]["attendance"]
               if str(a["student_id"]) == row.student_id and str(a["session_id"]) in sessions
               and a["recorded_at"] <= row.cutoff]
    assert row.calculation.features.observed_sessions == len(records)
    assert row.calculation.features.attendance_rate == (
        sum(a["status"] == "present" for a in records) / len(records)
    )


def test_lab_exclusions_and_exact_split_counts(dataset, rows):
    lab_courses = {r["id"] for r in dataset["tables"]["course"]
                   if r["required_room_kind"] == "lab"}
    lab_offerings = {str(r["id"]) for r in dataset["tables"]["course_offering"]
                     if r["course_id"] in lab_courses}
    assert all(r.calculation.status == "insufficient_data"
               for r in rows if r.offering_id in lab_offerings)
    split = partition_examples(rows, plan(rows))
    assert {k: len(v) for k, v in split["partitions"].items()} == {
        "train": 144, "validation": 72, "test": 72,
    }
    assert sum(map(len, split["partitions"].values())) + sum(split["exclusions"].values()) == 512
    for name, boundary in [("train", plan(rows).validation_start),
                           ("validation", plan(rows).test_start), ("test", plan(rows).test_end)]:
        assert all(r.horizon_end <= boundary for r in split["partitions"][name])
        assert any(r.horizon_end == boundary for r in split["partitions"][name])
    assert summarize(rows, split)["total_examples"] == 512


def test_reordered_source_and_inputs_preserved(dataset, rows):
    shuffled = deepcopy(dataset)
    for values in shuffled["tables"].values():
        values.reverse()
    before = content_hash(shuffled["tables"])
    assert extract_examples(shuffled) == rows
    assert content_hash(shuffled["tables"]) == before
    assert partition_examples(list(reversed(rows)), plan(rows)) == partition_examples(rows, plan(rows))


@pytest.mark.parametrize("damage", ["hash", "duplicate", "cross_edition", "wrong_section",
                                   "missing_session", "version"])
def test_reject_invalid_source(dataset, damage):
    bad = deepcopy(dataset)
    if damage == "hash":
        bad["edition"]["logical_content_hash"] = "bad"
    elif damage == "duplicate":
        bad["tables"]["attendance"].append(bad["tables"]["attendance"][0])
    elif damage == "cross_edition":
        bad["tables"]["student"][0]["edition_id"] = "other"
    elif damage == "wrong_section":
        bad["tables"]["attendance"][0]["student_id"] = bad["tables"]["student"][-1]["id"]
    elif damage == "missing_session":
        removed = bad["tables"]["class_session"].pop()
        bad["tables"]["attendance"] = [a for a in bad["tables"]["attendance"]
                                       if a["session_id"] != removed["id"]]
        bad["edition"]["logical_content_hash"] = content_hash(bad["tables"])
    else:
        bad["edition"]["generator_version"] = "future"
    with pytest.raises(ValueError):
        extract_examples(bad)


def test_split_rejects_duplicates_mixed_editions_and_invalid_plan(rows):
    with pytest.raises(ValueError, match="Duplicate"):
        partition_examples(rows + [rows[0]], plan(rows))
    with pytest.raises(ValueError, match="one edition"):
        partition_examples([rows[0], rows[1].model_copy(update={"edition_id": "other"})], plan(rows))
    with pytest.raises(ValidationError):
        TemporalPlan(validation_start=rows[0].cutoff, test_start=rows[0].cutoff,
                     test_end=rows[-1].horizon_end)


def test_label_availability_is_purged_too(rows):
    split_plan = plan(rows)
    row = next(r for r in rows if r.calculation.status == "eligible"
               and r.horizon_end == split_plan.validation_start)
    late = row.model_copy(update={"label_as_of": row.horizon_end + timedelta(seconds=1)})
    result = partition_examples([late], split_plan)
    assert result["exclusions"] == {"train:purged_horizon": 1}


def test_short_edition_retains_insufficient_and_truncated_examples():
    rows = extract_examples(generate(GeneratorConfig(weeks=1, students_per_section=1)))
    assert len(rows) == 32
    assert all(r.calculation.status == "insufficient_data" for r in rows)
    assert all(r.calculation.label_status == "horizon_incomplete" for r in rows)


def test_future_attendance_mutation_leaves_training_examples_unchanged(dataset, rows):
    changed = deepcopy(dataset)
    boundary = plan(rows).validation_start
    future_ids = {s["id"] for s in changed["tables"]["class_session"]
                  if s["starts_at"] >= boundary}
    for record in changed["tables"]["attendance"]:
        if record["session_id"] in future_ids:
            record["status"] = "absent" if record["status"] == "present" else "present"
    changed["edition"]["logical_content_hash"] = content_hash(changed["tables"])
    extracted = extract_examples(changed)
    original_train = partition_examples(rows, plan(rows))["partitions"]["train"]
    changed_train = partition_examples(extracted, plan(rows))["partitions"]["train"]
    # Provenance hash must change; all train feature/label calculations must not.
    assert [r.calculation for r in original_train] == [r.calculation for r in changed_train]
    assert original_train[0].edition_hash != changed_train[0].edition_hash


def test_empty_partition_statistics_and_invalid_horizon(rows):
    empty = summarize([], partition_examples([], plan(rows)))
    assert empty["partitions"]["train"]["prevalence"] is None
    assert empty["partitions"]["test"]["both_classes_present"] is False
    bad = rows[0].model_copy(update={"horizon_end": rows[0].cutoff})
    with pytest.raises(ValueError, match="horizon"):
        partition_examples([bad], plan(rows))
