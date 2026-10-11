# M0/M1 local foundation verification — 1 October 2026

M0's agreed design is recorded in [the blueprint](blueprint.md). M1's local startup, database and authentication software checks pass on this Windows machine. Teammate-machine acceptance remains open. Docker is explicitly deferred at the user's request and is not part of this delivery.

## Delivered

- `scripts/start_local.py` provides one-command startup of FastAPI and Vite after initial README setup. It reads the existing private configuration, checks database connectivity, migration head, a dataset and an account, and rejects occupied or duplicate ports. Checks do not migrate, seed, create users or stop unrelated processes.
- The launcher binds both services to loopback, sets matching local Origin/proxy configuration, waits for backend health through the frontend proxy, and stops its own children on shutdown or startup failure. It uses the invoking Python interpreter; run it with the project's `.venv` as documented. It uses plain HTTP/local cookies and is for local development.
- `scripts/verify_m1_startup.py` verifies the same launcher against real HTTP services and a random schema in `college_twin_test`. It creates temporary planner/viewer accounts without printing their generated password and removes its schema and servers afterward. It does not reuse or reset application accounts.
- Six launcher regression cases cover backend/frontend startup failure, KeyboardInterrupt cleanup, duplicate ports and out-of-range ports.
- The saved local application database was at `0003`; the existing additive `0004` migration was applied to create immutable simulation storage. `alembic current` now reports `0004 (head)`, and the launcher's read-only setup check passes. This upgrade creates a table/function/triggers; it does not seed, rewrite timetable data or approve campus links.

## Executed checks

Tested application base revision `b8ce04e4d075e9f0d8545c53834944f5d88a6dc2` with the new launcher, smoke script, six regression cases and documentation changes. Prior M3 benchmark changes remain in the working tree.

| Check | Result | Evidence / scope |
|---|---|---|
| Full backend suite | PASS — **109 passed, zero skipped** | `python scripts/test_local_postgres.py`; dedicated PostgreSQL test schemas, including all 17 integration tests |
| Frontend suite | PASS — **38 passed** | `npm.cmd test --prefix frontend` |
| Frontend production build | PASS | `npm.cmd run build --prefix frontend`; existing large Three.js chunk warning remains |
| Launcher and smoke-script lint | PASS | Ruff on both scripts and the new test file |
| Launcher/script compilation | PASS | Python compileall |
| Real local startup lifecycle | PASS | [Raw smoke results](m1-startup-verification.json) |
| Existing application configuration | PASS | `python scripts/start_local.py --check`, after migration `0004` |
| Teammate's independent installation | NOT TESTED | Requires that machine and teammate; use the checklist below |
| Interactive browser startup/login rehearsal | NOT TESTED in this follow-up | Smoke uses real HTTP through Vite; no new visual/keyboard claim |
| Docker | DEFERRED | Explicit user instruction; no container validation claimed |

The HTTP smoke verifies idempotent seeding, both servers running, port-collision rejection, frontend HTML and proxied database health, anonymous access denial, planner and viewer login, `/auth/me`, dataset selection by ID, twelve-room inventory, logout rejected without CSRF, successful protected logout, and revoked access afterward. Both child processes stopped and their ports became available; the disposable schema was removed. The smoke fixture uses one week and two students per section; default-size performance is covered separately by M2/M3 reports.

Initial sandbox runs hit Vite/esbuild process restrictions and pytest temporary-directory permissions. Approved execution outside the sandbox passed. Existing Starlette/httpx/AnyIO and Alembic deprecation warnings remain. No dependencies were changed to silence warnings.

## Reproduce locally

After the README's one-time dependencies, database, migration, seed and account setup:

```powershell
Set-Location 'V:\college twin'
.\.venv\Scripts\python.exe scripts/start_local.py --check
.\.venv\Scripts\python.exe scripts/start_local.py
```

Open `http://localhost:5173` and use your existing website account. Keep the terminal open; Ctrl+C stops both services. If another server occupies either port, reuse that server or stop it yourself. Optional alternate ports are `--backend-port 8001 --frontend-port 5174`; the launcher aligns the proxy and Origin automatically. `--check` checks setup only, not port availability or credentials for a particular account.

To repeat the isolated smoke after configuring the dedicated `college_twin_test` database:

```powershell
.\.venv\Scripts\python.exe scripts/verify_m1_startup.py
```

## Independent teammate acceptance record

Each teammate should complete this on their own machine and attach the actual output; do not mark it complete based on this machine's results.

- [ ] Record teammate, machine/OS, date and checked-out revision.
- [ ] Follow README dependencies and one-time database/migration/seed/account setup without copying another person's private settings or passwords.
- [ ] Run `start_local.py --check` successfully, then start both services with `start_local.py`.
- [ ] Sign in, select the synthetic edition, open room inventory and campus, and confirm synthetic/provisional labels.
- [ ] Log out and confirm authenticated data requires sign-in again.
- [ ] Stop with Ctrl+C, restart using the same command and confirm saved data/account remain available.
- [ ] Record actual result and any setup correction. Reviewer/date: __________.

M0/team decisions still requiring people—owner names, deadline, weekly availability and submission format—remain in [the team roadmap](team-roadmap.md). Campus geometry review and exact mapping approval also remain human actions. No design decisions or mappings were invented to close those checkboxes.
