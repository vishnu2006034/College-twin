# College Twin

Synthetic-data college digital-twin prototype. M1 provides a React frontend shell, FastAPI authentication and reference-data reads, a PostgreSQL schema/migration, and a reproducible relational generator. State metrics, anomalies, simulations and ML are later milestones, not implemented features.

The design, responsibilities and 12-week plan live in [docs/blueprint.md](docs/blueprint.md). The frontend/integration owner starts against mocked responses in **week 4**, not week 9.

## Run without Docker

Requirements: Python 3.13 and Node.js 24. PostgreSQL 17 is required only for the database-backed API, migrations and integration tests. Docker setup is deferred at the user's request.

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock
npm.cmd ci --prefix frontend
```

With an activated Python 3.13 environment, the backend also supports installing as a local package:

```powershell
Set-Location backend
uv pip install .
```

Use `uv pip install -e .` for an editable development install. Dependencies come from `requirements.in`, including the M1 test tools; add `-c requirements.lock` to use the verified exact versions. Package discovery includes only `app` and its subpackages. Alembic migrations remain in the source checkout, so run migration commands from `backend` as documented below.

Generate and validate the full dataset without a database:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m app.cli generate --seed 42 --weeks 16 --output ..\data\seed-42.json
```

The default dataset contains 240 students, 16 faculty, 12 rooms, 2,560 dated class sessions and 76,800 attendance rows. The command prints counts and a logical hash. Same seed, generator version, configuration and locked dependencies produce the same logical data. Generated JSON is ignored by Git; commit the generator and lockfiles instead.

Start the frontend shell in a separate root terminal:

```powershell
npm.cmd run dev --prefix frontend
```

Open http://localhost:5173. Without the backend, the shell shows a connection message and login form; it does not fabricate a logged-in dashboard. UI tests use mocked responses without requiring PostgreSQL. In week 4, expand those mocks for M2 contracts before implementing state screens.

## Connect an existing PostgreSQL database

Create a dedicated database and administrative account using your existing PostgreSQL installation. Supply its SQLAlchemy connection string as `DATABASE_URL` through your local environment, never a committed file. URL-encode special characters in credentials. From `backend`:

```powershell
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\python.exe -m app.cli seed --seed 42 --weeks 16
..\.venv\Scripts\python.exe -m app.cli create-user planner --role planner
..\.venv\Scripts\python.exe -m app.cli create-user viewer --role viewer
```

The account commands securely prompt for a password of at least 16 characters. They do not overwrite existing users. For the frontend dev server, set `APP_ORIGIN` to `http://localhost:5173` before starting the API:

```powershell
..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The frontend proxies `/api` to port 8000. Cookies remain same-origin. Session tokens and CSRF tokens are hashed in the database; logout requires origin and CSRF validation. The API includes `/api/v1/health`, `/auth/login`, `/auth/me`, `/auth/logout`, `/datasets`, and `/rooms`; interactive documentation is at http://127.0.0.1:8000/api/docs.

Use a restricted runtime database role for shared demos. `python -m app.cli bootstrap` creates local planner/viewer accounts, provisions the fixed `twin_app` role, and seeds the default edition. It requires admin `DATABASE_URL` and separate `PLANNER_PASSWORD`, `VIEWER_PASSWORD`, `API_DB_PASSWORD` environment values. It must run only against the dedicated project database/cluster because the PostgreSQL role is cluster-scoped. Restart the API with `DATABASE_URL` using `twin_app`; it has SELECT-only domain permissions plus the auth/audit permissions it needs. Do not run the public API with an administrative database account outside personal local development.

## Verification

Backend checks independent of PostgreSQL, from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q -m "not integration" -p no:cacheprovider
..\.venv\Scripts\ruff.exe check app tests migrations
```

Frontend checks, from the root:

```powershell
npm.cmd run build --prefix frontend
npm.cmd test --prefix frontend
```

For PostgreSQL integration tests, set `TEST_DATABASE_URL` to a dedicated database whose name ends in `_test`, then run all backend tests. Each test creates an isolated random schema, applies the actual Alembic migration, and removes only that schema afterward. Tests require a database account allowed to create schemas/functions. They verify migration replay, atomic rollback, composite foreign keys, immutable editions, login/session expiry, CSRF, role enforcement and pagination. They deliberately skip when no test database is configured; skipped is not passed. SQLite is not used as a substitute.

## Deferred container setup

Container files are supplied but Docker startup/build and PostgreSQL integration verification remain pending. When Docker work is resumed:

```powershell
python scripts\setup_env.py
docker compose up --build -d
```

The setup script creates `.env` with independent random secrets without printing or overwriting them. Open that local file to retrieve the `planner` and `viewer` passwords. Compose is designed to migrate, bootstrap and seed before the API starts, then serve the frontend at http://localhost:8080. Only the frontend port is published; the database remains internal. Existing datasets are preserved by idempotent seed loading. Container base tags still need digest locking after a verified build.

Optional later PostgreSQL tests: `docker compose --profile test up -d test-db`, followed by `.\.venv\Scripts\python.exe scripts\run_backend_tests.py`. This uses a separate disposable test database. Avoid removing the demo volume unless you intentionally want to erase its local data.

## Boundaries

- All generated records are synthetic and visibly labelled. No contact information is generated.
- M1's clean generator has complete attendance and feasible timetables. Sparse, shifted and deliberate-anomaly fixtures are later evaluation work.
- Historical sessions are stored as held with recording timestamps. M2 must respect those timestamps when reconstructing an earlier cutoff.
- No AI provider is called and no simulation modifies source data.
- Login throttling is per process. Keep the planned single API worker; redesign throttling before scaling out.
- No integration test or Docker result is claimed until it actually runs successfully.
