# M3 room-closure contract

29 September 2026 · **Status: core engine, immutable persistence/API and synthetic-room comparison implemented and locally verified; broader acceptance pending.** See [verification](m3-verification.md).

This contract specifies one-room closure and deterministic room reassignment using a saved synthetic planning snapshot. It refines the [blueprint](blueprint.md) and builds on the [M2 contract](m2-contract.md). It does not approve actual campus mappings or claim team acceptance of domain assumptions.

## 1. Scope and planning baseline

The planner selects a saved snapshot, one synthetic room and a closure interval. The application compares baseline, disrupted and reassigned schedules without changing the source timetable, attendance or snapshot. Class times, faculty, sections and courses stay fixed. One request contains one closure; scenario chaining, time rescheduling, optimization and attendance effects are outside M3.

Proposed v1 baseline rules:

- Require a supported snapshot schema (`1`) and verify its canonical-input hash before use. Load all operational inputs from that snapshot, never current source tables or current mappings.
- Require `as_of == window_start`. This makes the entire comparison window a planning window, rather than mixing historical observations and future reassignment. The existing M2 API already allows creating this snapshot. A historical snapshot with a later cutoff remains viewable but cannot be used for M3 v1.
- Require every noncancelled saved session to be fully contained in the snapshot window and have effective status `scheduled`. Otherwise return 409 with instructions to create a suitable planning snapshot. M2 saves only sessions overlapping its window; moving a boundary-crossing session outside that window could miss competing bookings that were not saved.
- Reject a baseline with any of M2's five anomalies across the full comparison window. Return 409 and direct the user to the saved baseline anomaly list. No partial simulation is persisted.
- Use effective status reconstructed at the saved cutoff. A cancellation recorded after the cutoff must not influence the simulation. Never consult raw future final status to decide eligibility.
- Keep M2's positive, at-most-seven-day window and teaching hours: weekdays 09:00–17:00 Asia/Kolkata. Accept a zero-session baseline and closures outside teaching hours within the window.

These explicit v1 restrictions are implemented and unit-tested without changing M2 snapshot behavior. Team domain acceptance remains pending.

## 2. Creation and retrieval API

`POST /api/v1/simulations` requires a planner session, valid Origin and CSRF, and an `Idempotency-Key` of 1–128 characters. Unknown body fields are rejected.

```json
{
  "snapshot_id": "00000000-0000-0000-0000-000000000001",
  "type": "room_unavailability",
  "room_id": "00000000-0000-0000-0000-000000000002",
  "closure_start": "2026-01-05T10:00:00+05:30",
  "closure_end": "2026-01-05T12:00:00+05:30"
}
```

UUIDs above are illustrative. Offset-aware timestamps normalize to UTC before hashing. Require `window_start <= closure_start < closure_end <= window_end`. Intervals are half-open: a class ending at closure start or starting at closure end is unaffected. The room must exist in the snapshot's saved room inventory; the edition is derived from the snapshot rather than supplied independently.

Success returns 201 with the persisted run envelope. An identical replay returns the same envelope and 201, following M2. `GET /api/v1/simulations/{id}` returns 200 for authenticated viewers or planners without recomputation.

`GET /api/v1/simulations/{id}/sessions?stage=reassigned&limit=50&offset=0` returns `{items,total,limit,offset}`. `stage` is required and is `baseline`, `disrupted` or `reassigned`; limit is 1–200, offset is nonnegative. Optional `room_id` filters effective assignments. Optional `affected_only=true` includes all displaced sessions, including unresolved ones. Both filters combine with AND; the UI uses affected-only without a room filter to show unresolved demand. Sort by start time then session ID before pagination.

Errors use the existing `{code,message,field_errors,request_id}` envelope:

| Status | Condition |
| --- | --- |
| 401 / 403 | Unauthenticated / wrong role or failed request protection |
| 404 | Missing snapshot/run, or room absent from the saved inventory |
| 409 | Idempotency mismatch, unsupported/corrupt snapshot, infeasible or unsuitable planning baseline |
| 422 | Invalid fields, type, offsets, interval or pagination |
| 503 | Database failure; retry with the same key |

Authenticate and authorize before disclosing saved data. Follow existing application-wide viewer/planner read scope; this milestone does not introduce a different ownership model. Validation failures do not reserve a key. Database failures leave neither a completed run nor its success audit record.

## 3. Deterministic allocation

1. Validate the baseline. A session is affected if its original room is the closed room and its full interval overlaps the closure. Displace the whole session, even for a partial overlap.
2. Build the disrupted schedule: retain unaffected assignments and leave every affected session unassigned. Preserve its original room and original effective status in the result.
3. Sort affected sessions by descending enrolled section size, then start time, then canonical session UUID. Section size comes from saved student membership; affected-student totals count distinct student IDs, not summed class sizes.
4. For each session, consider rooms whose kind and lab subtype exactly match the saved course requirements and whose capacity is at least section size. Sort by ascending spare capacity, then canonical room UUID.
5. A candidate must be available for the entire class interval, outside the closure, and free of overlapping unaffected or already reassigned sessions. Recheck faculty and section constraints using the same half-open overlap rules. With a feasible baseline and unchanged times these constraints should remain satisfied.
6. Assign the first valid room; otherwise retain an explicit unresolved row. Earlier assignments reserve rooms for subsequent classes. Do not move unaffected sessions to make space.
7. Recheck all five M2 anomaly rules on assigned rows and independently verify no assignment intersects the closure. An unexpected violation is an internal calculation failure: persist no successful run and return a sanitized error.

The algorithm is `greedy_room_v1`. Under this v1 scope, affected classes cannot overlap: they came from one room in a baseline with no room conflicts. Their destination choices therefore do not compete in time. Tiny exhaustive fixtures verify the supported fixed-time choices. More general optimization that moves unaffected classes, changes times or closes several rooms is outside scope. Unresolved wording remains **“No room found by this heuristic.”** It must not claim that no solution exists under a broader set of changes.

Every affected row carries a deterministic candidate summary: `total_rooms`, `rejected_type`, `rejected_capacity`, `rejected_closure`, `rejected_room_busy`, `rejected_faculty_busy`, `rejected_section_busy`, `feasible_count`. Classify each room once by the first failed check in that order; feasible rooms are counted before the choice for this session is reserved. Counts partition the saved room inventory. An unresolved row has `reason_code=no_feasible_candidate`; the summary explains its constraints without a large per-room trace.

## 4. Persisted response and comparisons

The run envelope contains:

| Field | Meaning |
| --- | --- |
| `id`, `created_at`, `created_by` | Run identity and actor provenance |
| `schema_version=1`, `algorithm_version=greedy_room_v1` | Result and calculation versions |
| `synthetic_data_only=true` | Mandatory synthetic-data label |
| `snapshot_id`, `edition_id`, `edition_hash`, `baseline_input_hash` | Frozen source identity |
| `as_of`, `window_start`, `window_end` | Copied baseline time context |
| `request` | Normalized creation body |
| `input_hash`, `result_hash` | Hash of calculation inputs; hash of deterministic result |
| `result` | Three stage summaries, impact totals, deltas and recommendation |

`result` excludes generated run ID, actor, key and creation time. `result_hash` hashes the object `{result, sessions}`, where `sessions` contains all three ordered stage-row arrays; it therefore covers both summary values and exact assignments. `input_hash` covers normalized request, baseline hash, schema and algorithm version. The pure engine returns a `SimulationCalculation` with those hashes, versions, result and sessions. The persistence layer saves the normalized request and frozen snapshot inputs/response alongside the result and per-stage rows. Array ordering is explicit and stable before result hashing; database row order must not affect results. The original M2 input checksum still identifies its exact saved array order. Retrieval will read persisted results even after an algorithm upgrade.

Each stage row contains the saved M2 session fields plus `original_room_id`, nullable `assigned_room_id`, `allocation_status` (`unchanged`, `displaced`, `reassigned`, `unresolved`) and `affected`. Keep `status` as the original effective timetable status. For affected rows also include the candidate summary on the reassigned stage; otherwise it is null. Original `room_id` remains source provenance; scenario calculations and room filters use `assigned_room_id`.

Cancelled rows remain visible with `allocation_status=unchanged`, `assigned_room_id=null` and `affected=false`; they do not contribute to scheduled or unassigned teaching demand. The result contains `stages` (baseline/disrupted/reassigned summaries), `impact`, `deltas`, `observed_attendance` and `recommendation`. Each faculty-minute list uses M2's `{faculty_id, scheduled_minutes}` row shape, distinguished by its required/assigned parent field.

Each stage summary exposes:

- `scheduled_classes`: original teaching demand; constant across all stages.
- `assigned_classes`, `unassigned_classes`: split the same demand. Displaced/unresolved rows do not disappear or become cancelled.
- `scheduled_occupied_rooms`, `available_rooms`: at the snapshot cutoff, count only assigned classes; exclude rooms closed at that instant from availability.
- `booked_room_minutes`, `available_room_minutes`, `room_utilization`: union of assigned bookings clipped to teaching hours/window. For disrupted and reassigned stages subtract only the closure's intersection with teaching hours from the closed room's availability. Baseline availability has no closure. Zero denominator returns null. State the denominator beside utilization.
- `required_faculty_minutes`, `assigned_faculty_minutes`: per-faculty planned demand versus room-assigned teaching minutes clipped to the window. Required demand is unchanged; unassigned demand remains explicit. Include zero-load faculty.
- `anomalies`: the five existing M2 rules applied to assigned rows. Unassigned demand is reported separately and must not be presented as a conflict-free successful repair.

Historical attendance and coverage are displayed once from the baseline with the label “Observed at baseline cutoff; unchanged by simulation.” Do not calculate attendance improvements, future attendance or ML risk from a room move.

Impact fields: `affected_sessions`, `affected_students`, `reassigned_sessions`, `unresolved_sessions`, `unresolved_students`. Student counts are distinct within each category. Deltas contain disrupted-minus-baseline and reassigned-minus-baseline changes in assigned classes, unassigned classes, booked minutes, available minutes and utilization; utilization delta is null if either ratio is null and otherwise is a fraction difference, displayed as percentage points.

Recommendation is a deterministic template with code `no_affected_sessions`, `all_reassigned` or `partially_unresolved` (including zero successful moves). Include counts and the heuristic limitation. No LLM call is required.

## 5. Persistence and concurrency

Add a new Alembic migration after the current head and a `simulation_run` table following M2's persistence pattern: primary UUID; snapshot, edition and actor references; key/request hash; canonical inputs; response; saved stage rows. Verify snapshot/edition agreement. Completed runs are immutable through database enforcement and expose no update/delete API.

Use a unique constraint on `(created_by,idempotency_key)` in this table, independently of snapshot keys. Concurrent identical requests converge on one completed run and one `simulation.create` success audit entry; a different normalized request with the same key returns 409. Check existing keys before calculating; handle the insertion race using the existing conflict/replay approach. Insert run and audit in one transaction. Idempotent retries return the stored algorithm version even if a later deployment changes the current version.

Use existing authentication, request IDs and CSRF middleware. Include runtime database grants in the migration/bootstrap review; an administrative local connection alone does not verify restricted-role operation. Never write scenario assignments into domain tables or campus mappings.

## 6. Frontend flow

1. Open a saved planning snapshot. Show cutoff, window and edition. If unsuitable, explain the restriction and offer explicit creation of a new planning snapshot through M2; do not silently replace the baseline.
2. A planner chooses a room from saved synthetic inventory, or from an explicitly reviewed campus link for the same edition, then supplies closure times. Unmapped physical spaces retain “No linked dataset record”; no links are guessed or approved automatically.
3. Submit once using a stable key for that attempt; retry the same request with that key after an uncertain response. Changing inputs starts a new attempt. Show loading, validation and server errors; never substitute mock results in production.
4. Display baseline/disrupted/reassigned summaries, affected rows, old/new rooms, unresolved reasons and availability denominators. Viewers can open saved runs by ID but cannot submit.
5. Highlight affected and destination spaces only where current reviewed links exist. Identify the displayed mapping revision separately from immutable run provenance. Saved synthetic room IDs remain usable when mappings change or are absent; historical geometry/mapping replay is not implied.

Actual room links remain intentionally unconfirmed. Software development and automated checks use synthetic-room selection and disposable mapping fixtures. The team approves real demo links separately.

## 7. Acceptance fixtures and completion evidence

| Case | Required evidence |
| --- | --- |
| Basic reassignment | Two simultaneous classes of 30 and 40 students. The 40-person class loses its room; an occupied 50-seat room is rejected; a free matching 45-seat room is chosen. One move, 40 distinct affected students, no unresolved demand. |
| No room found | Remove the 45-seat room; preserve one unresolved class and its 40 students, with deterministic rejection counts. |
| Suitability | Wrong room kind/lab subtype and insufficient capacity reject; exact capacity passes. |
| Multiple displaced classes | Adjacent displaced classes can reuse destination rooms; spare-capacity ties use stable room IDs. Include distinct-student deduplication across repeated classes. Overlapping classes in the closed room are rejected as baseline conflicts. |
| Temporal edges | Adjacent intervals, partial closure overlap, offset equivalence, cutoff cancellation, out-of-window closure, boundary-crossing baseline and nonplanning cutoff. |
| Empty/zero availability | No affected classes is a successful run; weekend and all-room availability removed yield null utilization when denominator is zero. |
| Baseline conflicts | Positive cases for all five M2 rules reject with 409; do not create a scenario. |
| Determinism | Shuffled input rows and repeated calculation preserve assignments, ordering and result hash; UUID tie behavior is fixed. |
| Preservation | Source timetable/attendance, snapshot inputs/hash and mappings remain identical after success, replay and failure. |
| PostgreSQL integrity | Actual migration/replay, immutable rows, same-key races, different-request conflicts, audit rollback and restricted-role operation. Use only the dedicated test database. |
| API protections | Authentication, viewer prohibition on creation, CSRF/Origin, missing/cross-edition room, malformed body and pagination. |
| UI/browser | Real create/retrieve/retry, viewer read, unresolved/no-impact/error states, unmapped synthetic selection and disposable linked highlighting. Check narrow screen and keyboard use. |
| Allocation scope | Tiny exhaustively enumerated fixed-time assignments agree with the engine. Do not manufacture a greedy-failure case that requires overlapping displaced classes or multiple closures outside this contract. |
| Performance | Measure default-size seven-day scenario API p95 against the under-two-second target. Record hardware, counts, warm/cold conditions and sample size; separately inspect browser responsiveness. |

For hand arithmetic on a single weekday 09:00–17:00 window with four rooms, baseline availability is 1,920 room-minutes. Closing one room 10:00–12:00 reduces it to 1,800 in both scenario stages. A one-hour displaced class removes 60 booked minutes from disrupted state; successful reassignment restores those 60 minutes without restoring the closed room's availability. Use these independent expectations in tests.

## 8. Implementation sequence and review record

- [x] Inspect M2 storage, temporal reconstruction, API errors and existing blueprint rules.
- [x] Draft API, baseline restrictions, allocation, metrics, persistence and verification contract.
- [x] Implement typed models and pure allocation with independent hand-calculated fixtures.
- [x] Add migration, persistence/API and PostgreSQL concurrency/security tests.
- [x] Build comparison components against contract fixtures, then connect real endpoints.
- [x] Measure default-size seven-day local sequential API performance; see `m3-performance.md` and raw samples.
- [ ] Complete the broader browser matrix and browser responsiveness checks; record evidence in `m3-verification.md`.
- [ ] Obtain team acceptance of planning restrictions and verify reviewed demo mappings when the team supplies them.

The design review found two M2 reuse limits: `calculate()` counts every noncancelled row as assigned and assumes no closure in availability; saved inputs also contain raw final statuses that must remain hidden until the cutoff. M3 needs explicit scenario assignment/availability handling while preserving M2 temporal semantics. Do not implement displacement by deleting demand or marking classes cancelled.

The pure engine is implemented in `backend/app/simulation.py`; immutable persistence and routes are in `backend/app/simulations.py`, and the comparison is in `frontend/src/M3Workspace.tsx`. Prior suite evidence is 103 backend and 38 frontend tests. Core M3 and default-size local sequential API performance are verified; broader browser coverage, browser responsiveness and team acceptance remain open. See [verification](m3-verification.md).

### C4 reviewed mapping integration (29 September 2026)

The comparison includes a reviewed-campus-room selector filtered against the saved inventory and an explicit action to use the campus inspector's selected room. Synthetic-room selection remains available when links are absent. This workflow does not create or approve mappings.

Saved runs collect all affected reassigned-session pages for destination highlights, independently of table pagination. A failed page publishes no partial overlay. Cross-edition runs do not highlight the current campus; snapshot/edition changes and unavailable mappings clear obsolete highlights. The current reviewed mapping revision is labeled independently of immutable run provenance. Reloading or changing reviewed links updates the projection without altering saved results.

Closed rooms and reassignment destinations have distinct text labels and colors in the campus jump list, searchable directory, floor plans, inspector and 3D room surfaces (including hall rooms). Selection remains an independent outline. Unmapped rooms remain visible by synthetic ID in the comparison. Actual links still require human review; browser fixtures are disposable and are not domain approvals.
