# M2 review and acceptance

Implementation status: **M2 software and local validation complete; human mapping approval intentionally deferred.** The user requested the review screen and asked to leave actual mappings unconfirmed. No physical-to-synthetic assignments are prepopulated in the application database.

## Review decisions already encoded

| Topic | Implemented decision | Evidence |
|---|---|---|
| Temporal reconstruction | Original timetable assumed known; final status and attendance become visible at recorded time | Future-status/attendance and late-cancellation fixtures |
| Intervals | Half-open, clipped to the reporting window | Adjacent and clipped fixtures |
| Utilization | Per-room booking union, weekdays 09:00–17:00 IST; null with no availability | 90/960 hand arithmetic and empty-weekend fixtures |
| Coverage | Missing attendance is unknown; expose recorded and expected totals | 1/2 coverage fixture |
| Conflicts | One unordered pair per shared room/faculty/section; exact room kind/subtype and capacity checks | Positive/negative and three-way fixtures |
| Saved results | Immutable canonical inputs/results with hashes, idempotency and transactional audit | PostgreSQL persistence, concurrency and rollback tests |
| Campus mapping | Explicit edition-specific planner review, one-to-one teaching-space links, optimistic revision checks | Mapping API/UI and edition-isolation tests |
| Room filtering | Saved snapshot inputs, chronological paginated sessions; preserve cross-room faculty/section conflicts | Room API fixtures and browser smoke |
| Performance | Local sequential default-size snapshot p95 below 2 seconds | [Measured report](m2-performance.md) |

## How the team approves mappings

1. Select the intended dataset under **Dataset workspace & room inventory**.
2. Open **Review campus room mappings**. It starts with zero approved links.
3. Choose a physical teaching space and an exact synthetic room. The room selector includes its type, capacity and UUID. Provisional spaces remain labelled provisional; offices, restrooms and stairs cannot be mapped to teaching rooms.
4. Add links to the draft. Confirm the selected identities and synthetic suitability with the team. No link is inferred from equal labels or row order, and no physical capacity is invented.
5. Add a review note, acknowledge the review and click **Approve and save mappings**. Only planners can save; viewers can inspect.
6. Create or open a dated snapshot, then select the linked space in the scene or directory. The inspector shows the same snapshot ID, room metrics, saved timetable and relevant anomalies. Campus-wide totals above remain campus-wide.
7. To revise links, remove/add draft entries and review again. The server rejects stale revisions; reload mappings and repeat the review if another planner changed them. Editing links does not mutate frozen snapshots or source datasets.

The current mapping revision labels the room panel; mappings are separately reviewed presentation metadata and are not frozen into snapshots. Historical mapping-revision replay is outside this scope. Synthetic room IDs and immutable snapshot inputs remain the source of calculated state.

## Acceptance record

- [x] Contracts, implementation and automated checks completed.
- [x] Browser checked a disposable approved test link, persisted across refresh, with real saved-room metrics.
- [x] Actual application mappings remain empty, per user instruction.
- [ ] Team accepts the temporal assumptions and fixed teaching-hours policy.
- [ ] Team supplies and approves actual demo room links in the review screen.

These last two items require domain decisions from the team; they are not missing software. M3 room-closure implementation is the next development milestone. Docker and teammate-machine startup remain separate project gates.
