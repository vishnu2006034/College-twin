from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest

from app.generator import GeneratorConfig, content_hash, generate, validate_dataset


@pytest.fixture
def dataset():
    return generate(GeneratorConfig(weeks=1, students_per_section=3))


def test_reproducible_and_seed_sensitive(dataset):
    repeated = generate(GeneratorConfig(weeks=1, students_per_section=3))
    assert dataset == repeated
    different = generate(GeneratorConfig(seed=43, weeks=1, students_per_section=3))
    assert (
        dataset["edition"]["logical_content_hash"] != different["edition"]["logical_content_hash"]
    )


def test_clean_counts_and_feasibility(dataset):
    counts = validate_dataset(dataset)
    assert counts["student"] == 24
    assert counts["room"] == 12
    assert counts["class_session"] == 160
    assert counts["attendance"] == 480


def test_hash_independent_of_row_order(dataset):
    original = content_hash(dataset["tables"])
    for rows in dataset["tables"].values():
        rows.reverse()
    assert content_hash(dataset["tables"]) == original


@pytest.mark.parametrize(
    "corruption,match",
    [
        ("orphan", "Missing"),
        ("cross_edition", "Cross-edition"),
        ("wrong_student", "another section"),
        ("early_attendance", "Invalid attendance"),
        ("overlap", "Overlapping"),
        ("capacity", "capacity"),
        ("missing_attendance", "Incomplete"),
        ("duplicate", "Duplicate"),
    ],
)
def test_rejects_invalid_data(dataset, corruption, match):
    bad = deepcopy(dataset)
    tables = bad["tables"]
    if corruption == "orphan":
        tables["student"][0]["section_id"] = uuid4()
    elif corruption == "cross_edition":
        tables["room"][0]["edition_id"] = uuid4()
    elif corruption == "wrong_student":
        tables["attendance"][0]["student_id"] = tables["student"][-1]["id"]
    elif corruption == "early_attendance":
        tables["attendance"][0]["recorded_at"] -= timedelta(days=1)
    elif corruption == "overlap":
        tables["class_session"][1]["starts_at"] = tables["class_session"][0]["starts_at"]
    elif corruption == "capacity":
        tables["room"][0]["capacity"] = 1
    elif corruption == "missing_attendance":
        tables["attendance"].pop()
    else:
        tables["attendance"].append(dict(tables["attendance"][0]))
    with pytest.raises(ValueError, match=match):
        validate_dataset(bad)


def test_no_realistic_contact_fields(dataset):
    assert all(s["synthetic_label"].startswith("Student-") for s in dataset["tables"]["student"])
    assert all(
        set(s) == {"id", "edition_id", "section_id", "synthetic_label"}
        for s in dataset["tables"]["student"]
    )
