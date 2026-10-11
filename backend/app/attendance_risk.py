"""M4 v1 temporal examples; pure calculations, no model or database writes."""

from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class RiskPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["attendance_risk_v1"] = "attendance_risk_v1"
    history_days: Literal[28] = 28
    horizon_days: Literal[14] = 14
    minimum_observations: Literal[5] = 5
    minimum_coverage: Literal[0.8] = 0.8
    minimum_label_sessions: Literal[3] = 3
    risk_threshold: float = Field(default=0.75, gt=0, lt=1)


class AttendanceEvent(BaseModel):
    """One scheduled session for one student/offering, including missing observations."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    session_id: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    status: Literal["scheduled", "held", "cancelled"]
    status_recorded_at: AwareDatetime
    attendance: Literal["present", "absent"] | None = None
    recorded_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Session end must follow start")
        if (self.attendance is None) != (self.recorded_at is None):
            raise ValueError("Attendance and its timestamp must both be present or absent")
        if self.recorded_at is not None and self.recorded_at < self.ends_at:
            raise ValueError("Attendance cannot be observed before session end")
        return self


class RiskExampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cutoff: AwareDatetime
    label_as_of: AwareDatetime | None = None
    source_window_end: AwareDatetime | None = None
    events: tuple[AttendanceEvent, ...]
    policy: RiskPolicy = RiskPolicy()

    @model_validator(mode="after")
    def unique(self):
        if len({event.session_id for event in self.events}) != len(self.events):
            raise ValueError("Duplicate session IDs")
        if self.label_as_of is not None and self.label_as_of < self.cutoff:
            raise ValueError("Label observation time must not precede cutoff")
        if self.label_as_of is not None and self.source_window_end is None:
            raise ValueError("Label construction requires the complete source window end")
        return self


class RiskFeatures(BaseModel):
    attendance_rate: float
    observed_sessions: int
    consecutive_absences: int
    attendance_trend: float | None
    coverage: float


class RiskExample(BaseModel):
    policy_version: str
    status: Literal["eligible", "insufficient_data"]
    features: RiskFeatures | None
    expected_history_sessions: int
    observed_history_sessions: int
    history_coverage: float | None
    label_status: Literal[
        "not_requested", "horizon_incomplete", "incomplete_outcomes",
        "too_few_held_sessions", "missing_attendance", "eligible",
    ]
    label: bool | None = None
    label_held_sessions: int = 0
    label_observed_sessions: int = 0


def build_example(request: RiskExampleRequest) -> RiskExample:
    """No future outcome can affect features, including future cancellation status.

    Input membership/timetable is assumed fixed and known at cutoff (v1 generator).
    Unknown historical outcomes count toward coverage, never as absences.
    """
    cutoff, policy = request.cutoff, request.policy
    history_start = cutoff - timedelta(days=policy.history_days)
    middle = cutoff - timedelta(days=14)
    events = sorted(request.events, key=lambda event: (event.ends_at, event.session_id))
    history = [
        event for event in events
        if history_start <= event.starts_at and event.ends_at <= cutoff
        and not (event.status == "cancelled" and event.status_recorded_at <= cutoff)
    ]

    def observed(event, as_of):
        return (
            event.status == "held" and event.status_recorded_at <= as_of
            and event.recorded_at is not None and event.recorded_at <= as_of
        )

    known = [event for event in history if observed(event, cutoff)]
    coverage = len(known) / len(history) if history else None
    features = None
    if len(known) >= policy.minimum_observations and coverage >= policy.minimum_coverage:
        prior = [event for event in known if event.ends_at <= middle]
        recent = [event for event in known if event.ends_at > middle]

        def rate(rows):
            return sum(event.attendance == "present" for event in rows) / len(rows)

        streak = 0
        for event in reversed(history):
            if not observed(event, cutoff) or event.attendance != "absent":
                break
            streak += 1
        features = RiskFeatures(
            attendance_rate=rate(known), observed_sessions=len(known),
            consecutive_absences=streak,
            attendance_trend=rate(recent) - rate(prior) if recent and prior else None,
            coverage=coverage,
        )
    result = RiskExample(
        policy_version=policy.version,
        status="eligible" if features else "insufficient_data", features=features,
        expected_history_sessions=len(history), observed_history_sessions=len(known),
        history_coverage=coverage, label_status="not_requested",
    )
    if request.label_as_of is None:
        return result
    horizon_end = cutoff + timedelta(days=policy.horizon_days)
    if request.label_as_of < horizon_end or request.source_window_end < horizon_end:
        return result.model_copy(update={"label_status": "horizon_incomplete"})
    future = [event for event in events if cutoff <= event.starts_at < horizon_end]
    if any(
        event.ends_at > request.label_as_of or event.status_recorded_at > request.label_as_of
        or event.status == "scheduled" for event in future
    ):
        return result.model_copy(update={"label_status": "incomplete_outcomes"})
    held = [event for event in future if event.status == "held"]
    known_future = [event for event in held if observed(event, request.label_as_of)]
    result.label_held_sessions = len(held)
    result.label_observed_sessions = len(known_future)
    if len(held) < policy.minimum_label_sessions:
        result.label_status = "too_few_held_sessions"
    elif len(known_future) != len(held):
        result.label_status = "missing_attendance"
    else:
        result.label_status = "eligible"
        result.label = (
            sum(event.attendance == "present" for event in held) / len(held)
            < policy.risk_threshold
        )
    return result
