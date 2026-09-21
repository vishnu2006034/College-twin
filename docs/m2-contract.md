# M2 snapshot contract — 21 September 2026

First vertical slice: persisted dated state, deterministic anomalies, and a read-only dashboard. Synthetic data only. No live presence, simulation, or prediction is implied.

`POST /api/v1/snapshots` requires planner authentication, Origin, CSRF and an `Idempotency-Key` (1–128 characters). Body:

```json
{"edition_id":"00000000-0000-0000-0000-000000000001","as_of":"2026-01-05T10:00:00+05:30","window_start":"2026-01-05T09:00:00+05:30","window_end":"2026-01-05T17:00:00+05:30"}
```

Offsets are mandatory; values normalize to UTC. Windows are positive and at most seven days, within the edition term; cutoff must be inside the half-open window. A reporting window may include planned future sessions. Session inclusion uses overlap, not start-date equality. Before a final status is recorded, a session is treated as scheduled: M1 stores one final status, so this reconstruction assumes the original timetable was known throughout the edition. Historical timetable revisions are unsupported.

201 returns `id`, request fields, `schema_version=1`, `synthetic_data_only=true`, `input_hash`, `edition_hash`, `created_at`, `metrics`, `coverage`, and sorted `anomalies`. Same user/key/request replays the saved result; different request returns 409. `GET /snapshots/{id}` allows viewer/planner access to saved results. `GET /snapshots/{id}/sessions?limit=50&offset=0` returns saved timetable rows (max 200/page). Canonical inputs and computed outputs are saved atomically with an audit record; reads never recompute them.

Metrics:

- `scheduled_classes`: noncancelled sessions overlapping the window.
- `scheduled_occupied_rooms` / `available_rooms`: distinct room use at cutoff; planned use, not measured presence.
- `booked_room_minutes` / `available_room_minutes` / `room_utilization`: union of bookings per room clipped to weekdays 09:00–17:00 Asia/Kolkata and the reporting window. Denominator includes every room. Zero denominator gives null.
- `attendance_present`, `attendance_recorded`, `attendance_expected`, `attendance_rate`: held sessions ending by cutoff, status known by cutoff, records known by cutoff. Expected counts section membership; missing rows are unknown. Coverage includes `attendance_ratio` (recorded/expected, null for zero expected), `missing_attendance`, and session count.
- `faculty_workload`: scheduled minutes per faculty clipped to the reporting window; overlapping assignments sum because they represent separate teaching obligations. Includes zero-load faculty.

Anomalies have `rule`, `resource_id`, `session_ids`, `starts_at`, `ends_at`. Rules: `room_overlap`, `faculty_overlap`, `section_overlap`, `capacity`, `room_type`. Every overlapping unordered pair produces one result per shared resource. Intervals are half-open. Capacity compares section size to room capacity; room type checks exact kind and required lab subtype. Cancellation is evaluated at cutoff. Stable resource/session ordering makes output independent of database row order.

Frontend contract fixtures are used first in component tests; the production adapter calls real endpoints. No silent fallback from failed endpoints to mocks. Viewer can open a saved snapshot by ID; only planners can create one.

## Reviewed room mapping and saved room-state extension

`GET /api/v1/room-mappings/{edition_id}` requires authentication and returns `edition_id`, `version`, `bindings`, `reviewed_by`, `reviewed_at`, `review_note`. An edition with no review returns version 0, empty bindings and null review fields. No mapping is inferred or seeded.

`POST /api/v1/room-mappings/{edition_id}` requires planner, Origin and CSRF. Example body:

```json
{"expected_version":0,"bindings":[{"space_id":"it-ece-l1-room-1","room_id":"00000000-0000-0000-0000-000000000002"}],"review_note":"Example only: replace with identities actually reviewed by the team"}
```

The example is not a real approved mapping. Use stable IDs from the campus catalog and the selected edition. The server checks known teaching-space IDs, matching classroom/lab kind, room membership in the frozen edition, unique space/room assignments, maximum 200 entries and a nonblank 5–1,000 character review note. The full set is replaced atomically and its version increments. Empty sets clear reviewed links. Stale `expected_version` returns 409; invalid links return 422. Every successful review is audited with actor and timestamp. Lab subtype and physical capacity require human review because the physical catalog does not assert them.

`GET /api/v1/snapshots/{id}/rooms/{room_id}` returns `snapshot_id`, `edition_id`, cutoff/window, schema version, synthetic label, input hash, saved room metadata, room-scoped metrics/coverage and room-related anomalies. Calculations use only frozen snapshot inputs. Related anomalies include cross-room faculty/section conflicts when either session belongs to the selected room. Room not in the saved edition returns 404. This does not mutate the saved snapshot or its campus-wide totals.

`GET /api/v1/snapshots/{id}/sessions` accepts optional `room_id`; pagination is applied after filtering and sorting by start time then ID. Unfiltered requests also use this chronological order. `total` is the filtered count. Mapping revisions are separate presentation metadata; the panel displays the current reviewed revision and saved snapshot ID. Editing mappings does not rewrite historical snapshot inputs.

Teaching-space IDs are synchronized with `node scripts/sync_campus_catalog.mjs`; use `--check` to detect drift after physical catalog edits. Preserve stable IDs and provisional labels.
