# M4 attendance-risk contract — v1

11 October 2026. D1 temporal builder, D2 clean-edition extraction/purged splits and D3 offline baseline/logistic comparison implemented. Broader D4 evaluation, model storage, API and UI remain unfinished. Team review remains open.

## Objective

Forecast whether a student's recorded attendance in one course offering will be **below 75% during the next 14 calendar days**. This configurable demonstration threshold is not an institutional rule. Predictions concern synthetic data and are not confirmed future outcomes. Room-closure simulation does not change attendance risk.

## Input and time semantics

`backend/app/attendance_risk.py` accepts an aware cutoff and a complete stream of scheduled session events for exactly one student/offering. The future dataset adapter must enforce edition, student/section/offering membership and provide complete session inventory, not only attendance rows. Membership and timetable are fixed and known at cutoff in generator v1; evolving enrollment/timetable is unsupported. IDs identify events and never enter predictors. No database or HTTP access occurs in this module.

- History: sessions starting at or after cutoff minus 28 days and ending at or before cutoff.
- Known cancellations are excluded; cancellation recorded after cutoff cannot remove historical demand.
- Attendance is observed only when session status is held and both status/attendance timestamps are at or before cutoff. Missing or late observations are unknown, never absent.
- Eligibility: at least five observed sessions and at least 80% coverage of noncancelled historical scheduled sessions. Empty history has null coverage and returns `insufficient_data`.
- Features: observed attendance fraction, observed-session count, trailing consecutive absences, recent-minus-prior attendance rate and coverage. Trend splits history by session end at cutoff minus 14 days; either empty half gives null trend. An unknown session interrupts the absence streak. Future preprocessing must handle null trend using training data only.
- Weekly labs have at most four historical observations in this window and therefore remain insufficient under v1. Do not relax this silently.

## Labels are separate from features

Label extraction is optional and requires explicit `label_as_of` and `source_window_end`. Both must cover the full 14-day horizon; the latter certifies a complete source timetable window and prevents truncation at an edition's end. The adapter must obtain this from edition coverage, never infer it from the latest attendance row.

The label cohort contains sessions starting in `[cutoff, cutoff + 14 days)`. All session outcomes must be final and known at label observation time. Cancelled sessions do not count. At least three held sessions and complete attendance coverage are required. A rate exactly 75% is negative; a rate below it is positive. Unfinished horizons/outcomes, too few sessions and missing observations produce distinct ineligible states and null labels. A valid label does not override insufficient historical features.

Cutoffs are aware timestamps; durations are 28/14 days. Planned extraction uses midnight Asia/Kolkata cutoffs, which has no daylight-saving transition. No wall clock is consulted. Changing future events or label observation time must not alter historical features.

## D2 extraction and temporal splits — implemented

`backend/app/risk_dataset.py` accepts clean in-memory generator-v1 artifacts. It reuses generator validation for hashes, edition boundaries, references, membership, duplicate attendance and completeness; additionally checks every section's timetable against all configured weekday periods. Partial exports, altered schedules and unsupported versions are rejected. This is not yet a database adapter or sparse-edition importer. The D1 event builder still supports missing/late observations independently.

Every configured Monday at midnight IST produces one row per student/course offering. Edition/hash/generator version, student/offering IDs, cutoff, horizon end and policy are separate from `calculation.features`. Outcome visibility is exactly the horizon end; later attendance cannot retroactively supply the label. Ineligible rows remain in extraction output for audit. Sorting is deterministic and caller data is unchanged.

Partitions use cutoff intervals: train before validation start, validation before test start, and test before test end. A row is purged when its horizon end **or label observation time** exceeds the partition's end. Equality is allowed because future-session starts use a half-open interval. Remaining rows must have eligible history and labels. Exclusion counts are mutually exclusive, with boundary purging before history/label eligibility; the separate history/label summaries count every extracted row. Duplicate example identities and mixed editions/policies are rejected.

Default fixed boundaries are 2 March / 30 March / 27 April 2026 at midnight IST (weeks 8/12/16 after 5 January). These were selected by calendar positions, not model results. No preprocessing is fitted in D2. D3 must fit imputation/scaling only on training rows and select thresholds only on validation rows. Test data has been summarized for eligibility/prevalence, but has not been used for model selection or fitting.

Reproduce with `.\.venv\Scripts\python.exe scripts/prepare_m4.py` from the repository root. It generates seed 42 with 240 students and 16 weeks, writes [the aggregate evidence](m4-dataset-verification.json), and performs no database writes or training.

| Partition | Eligible examples | Positive labels | Prevalence | Retained cutoff dates |
| --- | ---: | ---: | ---: | --- |
| Train | 4,320 | 1,759 | 40.72% | 12 January–16 February |
| Validation | 2,160 | 873 | 40.42% | 2–16 March |
| Test | 2,160 | 805 | 37.27% | 30 March–13 April |

All 15,360 extracted rows are accounted for: 8,640 retained, 2,880 boundary-purged, and 3,840 otherwise excluded for insufficient history. Independently, 4,560 rows have insufficient history, 3,600 labels have too few held sessions, and 960 labels have incomplete horizons; these independent status counts overlap and must not be added as split exclusions. Weekly labs remain ineligible. Repeated students and overlapping within-partition horizons mean examples are not independent; these splits forecast known students, not unseen cohorts. Shifted-seed evaluation remains for the evaluation slice.

Verification: 15 D2 tests plus 19 D1 tests pass. The combined generator/M2-state/M3-domain/M4 run passed **111 tests**; Ruff passed. Tests include independently counted memberships/arithmetic, exact split totals, boundary equality, delayed label visibility, duplicate/mixed-source rejection, removed-session detection despite a recomputed hash, deterministic ordering, and changing post-training attendance without changing training calculations. No model-accuracy claim is made.

D3 now compares a dummy prior, current-rate rule and logistic regression with training-only preprocessing and validation-only threshold selection. See [measured results and limits](m4-evaluation.md). Next is D4: uncertainty and shifted-data evaluation; no prediction service is delivered yet.

## Verification

Hand-calculated fixtures cover arithmetic, strict threshold equality, history/horizon boundaries, future outcome isolation, late observations/status, missing labels, cancellations, source truncation, sparse history, exact 80% coverage, weekly labs, input immutability, duplicate IDs, aware timestamps and identifier exclusion. See the current execution result in the project blueprint. No model accuracy, database/API, browser or production-readiness claim follows from these pure tests.
