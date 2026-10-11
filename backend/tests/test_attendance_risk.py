from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.attendance_risk import AttendanceEvent, RiskExampleRequest, build_example

CUTOFF = datetime(2026, 2, 2, tzinfo=UTC)


def event(day, present=True, **changes):
    start = CUTOFF + timedelta(days=day)
    return AttendanceEvent(**(dict(
        session_id=str(day), starts_at=start, ends_at=start + timedelta(hours=1),
        status="held", status_recorded_at=start + timedelta(hours=1),
        attendance="present" if present else "absent",
        recorded_at=start + timedelta(hours=2),
    ) | changes))


def example(events, **changes):
    if "label_as_of" in changes:
        changes.setdefault("source_window_end", CUTOFF + timedelta(days=30))
    return build_example(RiskExampleRequest(cutoff=CUTOFF, events=events, **changes))


def history():
    return [event(-25), event(-20), event(-10), event(-5, False), event(-1, False)]


def test_hand_calculated_features_and_label():
    rows = history() + [event(1), event(2, False), event(3, False)]
    result = example(rows, label_as_of=CUTOFF + timedelta(days=14))
    assert result.status == "eligible"
    assert result.features.attendance_rate == 3 / 5
    assert result.features.attendance_trend == pytest.approx(1 / 3 - 1)
    assert result.features.consecutive_absences == 2
    assert result.features.coverage == 1
    assert result.label is True
    assert result.label_held_sessions == 3


def test_future_outcomes_and_order_cannot_change_features():
    baseline = example(history())
    rows = history() + [event(1, False), event(15)]
    assert example(list(reversed(rows))).features == baseline.features
    assert example(rows, label_as_of=CUTOFF + timedelta(days=20)).features == baseline.features


def test_late_history_observation_excluded_not_absent():
    rows = history() + [event(-0.5, recorded_at=CUTOFF + timedelta(days=1))]
    result = example(rows)
    assert result.features.observed_sessions == 5
    assert result.features.coverage == 5 / 6
    assert result.features.consecutive_absences == 0


def test_future_cancellation_does_not_remove_history_denominator():
    row = event(-2, status="cancelled", status_recorded_at=CUTOFF + timedelta(days=1),
                attendance=None, recorded_at=None)
    result = example(history() + [row])
    assert result.expected_history_sessions == 6
    assert result.history_coverage == 5 / 6
    known_cancel = row.model_copy(update={"status_recorded_at": CUTOFF})
    assert example(history() + [known_cancel]).expected_history_sessions == 5


@pytest.mark.parametrize("rows", [[], history()[:4], history() + [
    event(-2, attendance=None, recorded_at=None), event(-3, attendance=None, recorded_at=None),
]])
def test_insufficient_history(rows):
    result = example(rows)
    assert result.status == "insufficient_data"
    assert result.features is None


def test_exact_coverage_boundary_and_history_start():
    rows = [event(day) for day in range(-10, -2)] + [
        event(-28, attendance=None, recorded_at=None), event(-1, attendance=None, recorded_at=None),
        event(-29),
    ]
    result = example(rows)
    assert result.features.coverage == 0.8
    assert result.expected_history_sessions == 10


def test_label_boundary_and_strict_threshold():
    rows = history() + [event(0), event(1), event(2), event(3, False), event(14, False)]
    result = example(rows, label_as_of=CUTOFF + timedelta(days=14))
    assert result.label is False  # Exactly 75%, not below 75%.
    assert result.label_held_sessions == 4


@pytest.mark.parametrize("future,days,status", [
    ([event(1), event(2), event(3)], 13, "horizon_incomplete"),
    ([event(1), event(2)], 14, "too_few_held_sessions"),
    ([event(1), event(2), event(3, attendance=None, recorded_at=None)], 14, "missing_attendance"),
    ([event(1), event(2), event(3, recorded_at=CUTOFF + timedelta(days=15))],
     14, "missing_attendance"),
    ([event(1), event(2), event(3, status="scheduled")], 14, "incomplete_outcomes"),
])
def test_ineligible_labels_are_unknown(future, days, status):
    result = example(history() + future, label_as_of=CUTOFF + timedelta(days=days))
    assert result.label_status == status
    assert result.label is None


def test_input_validation():
    with pytest.raises(ValidationError, match="Duplicate"):
        example([event(-1), event(-1)])
    with pytest.raises(ValidationError):
        RiskExampleRequest(cutoff=datetime(2026, 2, 2), events=[])
    with pytest.raises(ValidationError):
        event(-1, recorded_at=None)
    with pytest.raises(ValidationError):
        event(-1, recorded_at=CUTOFF - timedelta(days=2))


def test_inputs_unchanged_and_no_identifiers_in_features():
    request = RiskExampleRequest(cutoff=CUTOFF, events=history())
    before = request.model_dump_json()
    result = build_example(request)
    assert request.model_dump_json() == before
    assert set(result.features.model_dump()) == {
        "attendance_rate", "observed_sessions", "consecutive_absences",
        "attendance_trend", "coverage",
    }


def test_truncated_source_cannot_supply_complete_label():
    result = example(history() + [event(1), event(2), event(3)],
                     label_as_of=CUTOFF + timedelta(days=30),
                     source_window_end=CUTOFF + timedelta(days=7))
    assert result.label_status == "horizon_incomplete"
    assert result.label is None
    with pytest.raises(ValidationError, match="source window end"):
        RiskExampleRequest(cutoff=CUTOFF, events=history(),
                           label_as_of=CUTOFF + timedelta(days=30))


def test_unknown_status_and_cancelled_future_labels():
    rows = history() + [event(1), event(2), event(3),
                        event(4, status="cancelled", attendance=None, recorded_at=None)]
    assert example(rows, label_as_of=CUTOFF + timedelta(days=14)).label is False
    late = event(-1, status_recorded_at=CUTOFF + timedelta(days=1))
    assert example(history()[:-1] + [late]).status == "insufficient_data"


def test_weekly_lab_is_insufficient_under_frozen_policy():
    result = example([event(day) for day in (-28, -21, -14, -7)])
    assert result.status == "insufficient_data"
    assert result.observed_history_sessions == 4
