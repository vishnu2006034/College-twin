# M2 snapshot performance — 21 September 2026

The default-size snapshot computation and persistence meet the **p95 under two seconds** target in this local, sequential API benchmark. This is not a concurrent-load, browser-rendering or production deployment claim.

| Operation | First measured call | Warm runs | Warm median | Warm p95 | Maximum warm |
|---|---:|---:|---:|---:|---:|
| Create one-day snapshot | 107.14 ms | 20 | 88.40 ms | 94.75 ms | 99.69 ms |
| Create seven-day snapshot | 463.34 ms | 20 | 376.88 ms | 481.94 ms | 490.32 ms |
| Read saved room state | Not measured separately | 20 | 33.37 ms | 41.97 ms | 49.80 ms |

Dataset: seed 42, generator 1.0.0, 16 weeks, 240 students, 16 faculty, 12 rooms, 32 offerings, 2,560 sessions and 76,800 attendance records. Logical hash is preserved in [raw results](m2-performance.json). One-day requests report 5 January; seven-day requests cover 5–12 January with a 9 January cutoff.

Machine/runtime: Windows 11 build 26200, AMD Ryzen 7 8845HS with Radeon 780M (8 cores / 16 logical CPUs; AMD64 Family 25 Model 117 Stepping 2), Python 3.13.14, PostgreSQL 18.4 on local loopback.

Method: `scripts/benchmark_m2.py` creates a random schema in `college_twin_test`, migrates it, loads the complete default dataset, signs in through the real authentication endpoint, and issues unique-key snapshot requests. Timing includes authentication checks, SQL reads, calculations, JSON serialization, saved inputs/results, audit writes and commit. It uses FastAPI TestClient, so excludes network transport and browser rendering. Each creation therefore measures new work, not an idempotent cached response. After the first request, 20 sequential warm requests are measured; p95 uses the nearest-rank value. Every response must succeed and the clean seed must return zero anomalies. The schema is removed afterward.

The first-call values are **not cold-start measurements**: dataset generation/loading and login already warmed process and database caches. No OS cache flushing, service restart or concurrent-load isolation was performed. Background desktop activity can affect timings. Scenario and prediction performance are deferred to M3/M4.

Reproduce in PowerShell from the repository root, after creating the separate test database using the verification guide:

```powershell
& '.\.venv\Scripts\python.exe' scripts/benchmark_m2.py --runs 20
```

The command updates `docs/m2-performance.json`; refresh this narrative if measurements change.
