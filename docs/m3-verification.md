# M3 room-closure simulation - current verification

29 September 2026. Core simulation API and comparison screen implemented. Prior pure-engine evidence is retained below as history.

## Current delivery

- Migration `0004` adds immutable `simulation_run` storage, snapshot/edition agreement enforcement, frozen calculation inputs, provenance, saved stage rows and results. UPDATE/DELETE are blocked by a database trigger. Runtime provisioning grants only SELECT/INSERT for runs.
- Planner POST `/api/v1/simulations`, authenticated GET by ID and typed paginated stage-session GET; existing Origin/CSRF and error envelope apply. Same-key races converge on one run and one audit entry; audit failure rolls the transaction back. New keys for identical inputs preserve deterministic result hashes.
- Saved room selection comes from GET `/api/v1/snapshots/{id}/rooms`, not the current source inventory. Allocation reuses the existing exact kind/lab-type/capacity and half-open conflict rules. Candidate rejection counts and unresolved demand are explicit.
- React comparison supports planner create/retry and viewer retrieval, three stages, availability denominators, distinct affected students, original/destination IDs, paginated affected rows and rejection reasons. Historical attendance remains baseline-only. No mock fallback is shipped.
- Existing hand-calculated 51 domain cases remain in place. New PostgreSQL checks cover source/snapshot preservation after success/replay/failure, independent deterministic runs, immutable saved results, authorization, pagination, concurrency, audit rollback and a restricted NOLOGIN runtime role. The restricted role cannot update source sessions.

## Local validation

- Backend: **103 passed, zero skipped**, including **17 PostgreSQL integration tests**, using `python scripts/test_local_postgres.py` and dedicated `college_twin_test` schemas. Actual upgrade/downgrade/replay and Alembic metadata checks included.
- Frontend: **38 passed** with `npm test`; production build passed with `npm run build`. Existing large Three.js chunk warning remains.
- Ruff and Python compilation passed. Existing Starlette/httpx/AnyIO and Alembic deprecation warnings remain.
- Initial sandbox runs hit Windows pytest temporary-directory permissions and esbuild subprocess restrictions; approved outside-sandbox execution resolved those environment failures. Two new test-fixture defects (UUID serialization and disrupted utilization arithmetic) were corrected before the passing results.
- Browser: real sign-in, saved planning-baseline retrieval, room selection and closure creation against a disposable test schema. Closing ROOM-02 09:00-10:00 IST on 2026-01-05 moved one class: assigned counts **32 / 31 / 32**, booked minutes **1920 / 1860 / 1920**, available minutes **5760 / 5700 / 5700**. Rejection counts showed two wrong-type rooms, one closed room, seven occupied rooms and two feasible rooms. Baseline attendance remained unchanged.
- Narrow browser viewport (387 px): fixed checksum overflow; document no longer horizontally overflows. Comparison tables scroll within focusable labeled regions. WebGL was unavailable in this browser; the existing directory fallback rendered. This is not a 3D performance claim.

## C4 mapped selection and highlighting verification

29 September 2026 follow-up: C4 software is complete. `simulation-map.ts` projects only exact, known, same-edition reviewed links. `M3Workspace` filters mapped selection through saved inventory and collects all affected pages before publishing a destination overlay. `M2Workspace` labels the current mapping revision, which is separate from saved simulation provenance. The directory, floor plans, inspector, regular building cutaways and hall room surfaces consume the same closed/destination markers.

Seven additional regression tests pass: edition isolation/unknown geometry, exact mapped-room submission without mapping writes, saved-inventory exclusions, all-page collection with unresolved exclusion, failed-page handling without partial highlights, destination floor navigation, and revision reload removing obsolete highlights while preserving comparison results. Updated an older mapping test's saved-room-list fixture to match the API contract; malformed room lists now show an error instead of crashing.

Live browser test used two explicit disposable mappings in a random schema in `college_twin_test`: F1 to ROOM-02 and F2 to ROOM-10. Selected F1 in the reviewed-room dropdown, created a closure for 2026-01-05 09:00-10:00 IST, and observed one reassignment. Revision 1 and two mapped spaces were displayed. The destination shortcut selected IT first-floor F2; the inspector showed ROOM-10 and its destination label. Screenshot inspection verified red F1 and blue F2 room surfaces and tags in the actual 3D cutaway. The earlier browser's WebGL limitation did not recur in this follow-up. This does not measure frame rate or complete the full accessibility matrix.

The frontend production build passes; its existing Three.js chunk-size warning remains. Backend code is unchanged by this follow-up; the earlier 103-test backend result remains the backend evidence. No application mappings were created or approved. The disposable browser schema and preview servers were removed after verification.

## Honest remaining gate items

Core user-requested simulation, saved baseline preservation, API, comparison and automated verification are delivered. The broader roadmap gate stays open for team acceptance, a complete keyboard/desktop browser matrix and measured default-size seven-day API performance. No scenario performance target is claimed. Actual campus mappings remain unconfirmed. M4 prediction, Docker validation and deployment remain pending.

Only dedicated test schemas were migrated during validation. To enable M3 on an existing local application database, apply `alembic upgrade head` from `backend` and rerun the existing runtime-role provisioning workflow if using `twin_app`; then restart the API. No application database migration, source edit or mapping approval was performed by this validation.

---

# Historical pure allocation engine verification

22 September 2026. Scope: typed simulation models and pure room allocation, authorized after the M3 contract review. This is the first M3 implementation slice, not the completed milestone.

## Delivered

- `backend/app/simulation.py`: strict request and typed output models, saved-snapshot verification, planning restrictions, deterministic allocation, candidate rejection counts and unresolved teaching demand.
- Baseline/disrupted/reassigned summaries and ordered session rows; distinct affected-student counts; required versus assigned faculty minutes; closure-adjusted availability and utilization; immutable baseline attendance context; deterministic input/result hashes and recommendations.
- Existing M2 temporal reconstruction and all five conflict rules are reused. The engine projects assigned rows for calculation without deleting demand from its result or changing source inputs. It excludes future final statuses according to the saved cutoff.
- Shared `teaching_intervals()` in `state.py` retains the existing weekday 09:00–17:00 policy for both M2 and M3.
- `backend/tests/test_simulation.py`: 51 tests, including independent arithmetic, exhaustive tiny assignments, corruption/eligibility failures, temporal cases and a generated one-week/160-class dataset.

Entry point: `simulate(request, snapshot_response, canonical_inputs) -> SimulationCalculation`. It has no database access, HTTP dependency, wall-clock input or source-data writes. `SimulationError` exposes domain reason and intended HTTP status for the future adapter. `SimulationResponse` defines the future envelope; no simulation route is registered yet.

## Independently checked outcomes

The fixture has four rooms, 40 and 30 students in separate sections, and two simultaneous one-hour classes. One class loses its 40-seat room; the 50-seat room is occupied; the free 45-seat room is selected; a 20-seat room is too small.

| Value | Baseline | Disrupted | Reassigned |
| --- | --- | --- | --- |
| Scheduled demand | 2 | 2 | 2 |
| Assigned / unassigned classes | 2 / 0 | 1 / 1 | 2 / 0 |
| Booked room-minutes | 120 | 60 | 120 |
| Available room-minutes | 1,920 | 1,800 | 1,800 |
| Utilization | 6.25% | 3.3333% | 6.6667% |

The 10:00–12:00 closure subtracts 120 minutes from one room's eight-hour availability. Removing the 45-seat room preserves one unresolved class and its 40 affected students. Closing the only room for the whole teaching day leaves zero availability and null utilization, while retaining unmet demand.

Other checks cover exact capacity, exact lab subtype, least spare capacity before UUID tie-breaking, candidate-count partitions, adjacent and partial intervals, distinct students across repeated classes, cancelled-session visibility, future cancellation at cutoff, occupied/available rooms at cutoff, weekends, teaching-hour clipping, offset-equivalent requests, all five baseline anomalies and unchanged caller-owned inputs after success or rejection. Shuffled source arrays preserve ordered result rows and result hashes; the M2 source checksum still records the exact stored input order.

## Executed checks

Tested working tree based on commit `145064a`, with the files above and the updated M3 documentation. No commit was created by this task.

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -m 'not integration' -p no:cacheprovider
..\.venv\Scripts\ruff.exe check app tests migrations
..\.venv\Scripts\python.exe -m compileall -q app
```

- **86 passed, 14 deselected** in the complete non-integration backend suite, including **51 M3 cases**. The 14 PostgreSQL tests were explicitly excluded; this is not a new database verification claim.
- Ruff passed for application, tests and migrations; compilation passed.
- Initial focused M3/M2 run: 62 passed before three additional edge-case tests were added. The final full-suite result above includes those additions.
- Initial full-suite attempt passed 83 tests but three existing configuration fixtures failed to create pytest temporary directories due to Windows sandbox permissions. The same suite was rerun outside the sandbox with approved escalation and all 86 passed. No product-code change was needed for that environment issue.
- Two existing Starlette/httpx/AnyIO deprecation warnings remain; they did not fail tests.
- No frontend files or API/database schema changed. Browser, database concurrency and scenario API performance checks belong to the next slice.

## Review corrections and ownership

| Finding | Why it mattered | Resolution | Owner |
| --- | --- | --- | --- |
| Draft required a greedy-failure fixture and competing displaced classes | One closed room in a conflict-free baseline cannot contain overlapping displaced classes. Destination assignments therefore do not compete in time in this scope. | Replaced the impossible fixture with four exhaustive tiny fixed-time assignment cases. Documented limits on moving unaffected classes, times and multiple closures. | B: backend/simulation; C: evaluation review |
| M2 metrics assume every noncancelled class has a room and no closures | Reusing totals unchanged would hide unmet demand or misstate available minutes. | Recalculate assigned rows with existing rules, retain original demand separately and subtract only teaching-time closure intersections. | B: backend/simulation |
| Cancelled rows and result hash coverage needed precision | A null assignment must not imply unmet demand for an already cancelled class; summary-only hashes would omit exact assignments. | Preserve cancelled rows as unchanged/non-demand; hash `{result, sessions}` with ordered stage rows. | B: backend/API; A: UI integration |

## Remaining M3 work

1. Add migration, immutable run storage, transactional audit, idempotent creation and saved-result/session retrieval; enforce existing planner/viewer and CSRF/Origin rules.
2. Run PostgreSQL migration, concurrency, rollback, restricted-role and baseline-preservation checks in the dedicated test database.
3. Build the comparison screen and campus highlighting with explicit handling for unmapped rooms; then verify real endpoints in the browser.
4. Measure scenario performance at default data size and complete the team demo/acceptance gate.

Actual campus mappings remain unconfirmed. No database content, mapping approvals or source timetable records were changed by this task.
