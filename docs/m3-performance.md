# M3 simulation performance — 1 October 2026

**PASS: default-size seven-day simulation creation meets the warm p95 under two seconds target in this local sequential API benchmark.** Browser responsiveness, network latency, cold starts and concurrent load were not measured.

| Operation | First measured call | Warm runs | Warm median | Warm p95 | Maximum warm |
|---|---:|---:|---:|---:|---:|
| Create week-long classroom closure | 387.57 ms | 20 | 360.89 ms | 407.89 ms | 575.68 ms |
| Create week-long lab closure | 340.62 ms | 20 | 409.30 ms | 449.98 ms | 459.68 ms |
| Create weekend closure, no impact | 430.48 ms | 20 | 397.54 ms | 497.85 ms | 518.66 ms |
| Read saved classroom run | 22.18 ms | 20 | 14.94 ms | 19.76 ms | 24.32 ms |
| Read affected reassigned-stage page | 28.37 ms | 20 | 14.95 ms | 18.66 ms | 36.33 ms |

## Dataset and observed outcomes

Generator 1.0.0, seed 42, default 16 weeks: 240 students, 16 faculty, 12 rooms, 32 offerings, 2,560 sessions and 76,800 attendance records. The saved planning window is 5–12 January 2026 at 00:00 Asia/Kolkata, with cutoff equal to window start. The seven-day window contains 160 classes.

- ROOM-02 closed for the full week: 19 affected classes, 30 distinct affected students; all 19 classes reassigned.
- LAB-11 closed for the full week: four affected classes, 120 distinct affected students; all four remain explicitly unresolved under the fixed-time heuristic.
- ROOM-02 closed 10–12 January: no affected classes.

Each scenario used 21 distinct run IDs and unique idempotency keys, and all 21 results had the same deterministic result hash within that scenario. Thus creation timings include allocation and persistence rather than idempotent replay. Saved-result retrieval returned the exact envelope; affected-session retrieval verified its total and affected flags. Hashes of every source domain table and the complete retrieved baseline snapshot were unchanged after all operations. The disposable schema was removed successfully.

## Method and limits

Executed `scripts/benchmark_m3.py --runs 20` against a random schema in **college_twin_test**, using actual migrations, default data loading, planner authentication and FastAPI TestClient. Creation timing includes request protection/auth checks, PostgreSQL reads, allocation, response serialization, immutable result storage, audit writes and commit. Setup, source-preservation hashing and snapshot creation are outside the timed operations. No application database or actual campus mappings were modified.

The first call per operation is recorded separately. It follows migration, seeding, login and snapshot creation, so it is **not a cold-start measurement**. Each operation then has 20 sequential warm samples; p95 is nearest-rank (19th sorted sample). Operations share a process/schema and run in the table's order; background desktop activity and cache state can influence timings. TestClient excludes HTTP network transport and browser rendering. These figures do not establish production throughput or full M3 acceptance.

Runtime: Windows 11 build 26200, AMD64 Family 25 Model 117 Stepping 2 (AuthenticAMD), 16 logical CPUs, Python 3.13.14, PostgreSQL 18.4 on the configured local PostgreSQL server. Application base revision: `b8ce04e4d075e9f0d8545c53834944f5d88a6dc2`, plus the new benchmark script; application code was unchanged. [Raw results](m3-performance.json) retain every warm sample, request, result hash, edition hash and runtime details. IDs in the report refer to the removed disposable schema and cannot be opened in the application.

The benchmark completed successfully and Ruff passed for the new script. An initial harness run failed because its source-preservation hash received native UUIDs; switching to the generator's existing UUID-aware content hash resolved the harness error. No simulation-code change was required. Existing Starlette TestClient deprecation warning remains. Prior application test-suite results are recorded in [M3 verification](m3-verification.md); they were not rerun for this script/documentation-only change.

## Reproduce

From the repository root, with the existing local PostgreSQL configuration and dedicated test database available:

```powershell
& '.\.venv\Scripts\python.exe' scripts/benchmark_m3.py --runs 20
```

The script forces the target database name to `college_twin_test`, creates only a random benchmark schema, and removes that schema in `finally`, including on assertion failure. It writes `docs/m3-performance.json` only after all checks and cleanup succeed. Refresh this narrative after rerunning. The report's `creation_p95_under_2s` field records the performance verdict; command success alone means execution and integrity checks succeeded.
