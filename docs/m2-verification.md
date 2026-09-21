# M2 first slice — verification and handoff

21 September 2026. This record covers the M2 implementation and remaining-work follow-up, not the full project or production readiness.

## Delivered

- [Snapshot contract](m2-contract.md), typed Pydantic and TypeScript models; POST creation, GET saved result, paginated saved sessions.
- Frozen PostgreSQL snapshot storage, canonical inputs/hash and edition provenance, planner/CSRF checks, concurrent idempotency and transactional audit.
- Dated attendance and coverage, scheduled occupancy, teaching-minute room utilization and faculty workload.
- Room/faculty/section overlaps, capacity violations and exact classroom/lab-type suitability.
- Injectable mock response adapter and dashboard contract tests, then real endpoint adapter. Production errors remain errors, never mock metrics.
- Planner-reviewed, revisioned campus mappings and room-filtered saved state/timetable; actual application mappings remain unconfirmed per user instruction.
- Reproducible default-size [performance benchmark](m2-performance.md) and [team review handoff](m2-review.md).

## Hand arithmetic

`backend/tests/test_state.py` defines two rooms (capacity 2), two pupils in one section, and one teacher with classes 09:00–10:00 and 09:30–10:30 in the same room on Monday. A second teacher has no classes. At 10:00:

| Quantity | Independent expectation |
|---|---|
| Scheduled classes | 2 |
| Occupied / available rooms | 1 / 1; the first class ends exactly at cutoff |
| Room booking union | 09:00–10:30 = 90 minutes |
| Available room minutes | 2 rooms × 8 hours × 60 = 960 |
| Utilization | 90 / 960 = 9.375% |
| Faculty workload | 60 + 60 = 120 minutes; idle faculty = 0 |
| Attendance | First class has 2 expected rows, 1 known present row; later absent row excluded |
| Rate / coverage | 1/1 = 100%; 1/2 = 50%; 1 unknown |
| Conflicts | One pair for each of room/faculty/section, overlapping 09:30–10:00 |

Negative fixture moves the second class to 10:00–11:00: zero overlaps, 120 booked minutes. Capacity exactly 2 passes; capacity 1 fails. Classroom/lab and differing lab subtypes fail; matching subtype passes. Other fixtures cover resource-independent conflicts, three simultaneous classes (three unordered pairs per resource), late cancellations, future status/attendance exclusion, clipped windows, weekends/null denominators, reordered input, and input immutability.

## Executed checks

- Backend: **49 passed, zero skips**, including **14 PostgreSQL integration tests**. This closes the original eight-test M1 database gap. Tests cover migrations and metadata consistency, persistence/hashes, immutable rows, role/CSRF/date errors, pagination, concurrent retries, rollback, reviewed mapping validation/edition isolation/version conflicts, and room-state filtering that preserves cross-room anomalies.
- Frontend: **28 passed**; production TypeScript/Vite build passed. Mapping tests cover explicit approval, viewer restrictions, snapshot identity, unmapped selections, edition resets and session pagination.
- Ruff and Python compilation passed. Existing dependency deprecation warnings and the large 3D bundle warning remain; no performance certification is inferred.
- The local application database was upgraded to Alembic `0003 (head)` after the isolated migration tests passed; zero approved mapping sets were confirmed.
- Fresh browser: disposable one-week PostgreSQL dataset, planner login, create 5 January 2026 / 17:00 IST snapshot, reopen the saved ID, inspect responsive layout. Display: 32 scheduled classes, 0 occupied / 12 available rooms, 1,920/5,760 room minutes = 33.3%, 52/64 present = 81.3%, 100% recorded coverage, zero anomalies. Browser smoke used the real API; positive conflicts are covered by domain fixtures and mocked dashboard tests.
- Follow-up browser: explicitly reviewed a test-only F1 → ROOM-01 link in a disposable test schema, refreshed the page, reopened the saved snapshot, and selected the linked classroom. Room panel showed the same snapshot ID, four classes, 240/480 minutes = 50% utilization, 75% attendance, 8/8 coverage and saved sessions. Narrow layout was inspected. The disposable link is not an actual approved campus mapping.

## Local upgrade and verification (PowerShell)

From `V:\college twin`, with local database settings already configured, apply the additive migration using the database owner account:

```powershell
Set-Location 'V:\college twin\backend'
& '..\.venv\Scripts\python.exe' -m alembic upgrade head
Set-Location 'V:\college twin'
& '.\.venv\Scripts\python.exe' scripts/test_local_postgres.py --create-test-database
```

The second command creates `college_twin_test` only if absent, using the configured local PostgreSQL credentials without displaying them. Each test creates and removes a random schema there; it never clears the demo database. Later runs can omit `--create-test-database`. An account without database-creation permission needs the database owner to create this dedicated database once.

If the backend uses the restricted `twin_app` role, the database owner must run the following in the **SQL shell connected to the application database**, after migration (new bootstrap installations already grant this):

```sql
GRANT SELECT, INSERT ON state_snapshot TO twin_app;
GRANT SELECT, INSERT, UPDATE ON room_mapping TO twin_app;
```

Restart the backend and frontend using the README's normal commands. Sign in as planner, select a synthetic date and cutoff, then create a snapshot. Viewers can open a saved snapshot ID. The default edition starts 5 January 2026, not today's date.

For a disposable browser check, stop the normal backend and run `& '.\.venv\Scripts\python.exe' scripts/preview_m2.py` from the repository root, alongside the usual Vite server on localhost:5173. This creates a random schema only in `college_twin_test`; the script documents its test-only account. Ctrl+C removes that schema. Do not deploy this preview helper.

To leave the normal app running, launch the preview with `--port 8001 --origin http://localhost:5174`. In a separate frontend PowerShell terminal set `$env:TWIN_API_TARGET='http://127.0.0.1:8001'`, then run `npm run dev -- --port 5174 --strictPort`. Open `http://localhost:5174`. This override changes only Vite's development proxy. A forcibly killed preview process can leave its printed random test schema behind; normal graceful exit removes it. Never approve real campus links from test-only browser fixtures.

## Remaining gates

M2 software, filtered room state and local sequential performance are verified. Human contract sign-off and actual demo mapping approval remain intentionally deferred; the user requested an empty review workflow. Teaching hours are fixed in schema version 1, and timetable revision history is unavailable. Full anomaly-seeded dataset generation remains later evaluation work. Docker and teammate-machine setup remain separate pending checks. M3 simulation is the next development milestone; M3/M4 are not implemented.
