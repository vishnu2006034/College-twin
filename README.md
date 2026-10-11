# College Twin

M4 now includes an offline attendance-risk evaluation pipeline; prediction API/UI remain pending. To run it or the full backend test suite, first install the additional ML lock with `uv pip install --python .venv/Scripts/python.exe -r backend/requirements-ml.lock`. Then run `.\.venv\Scripts\python.exe scripts/evaluate_m4.py`. See [results, limitations and reproduction](docs/m4-evaluation.md).

Synthetic-data college digital-twin prototype. M1 provides authentication, reference data and reproducible generation. M2 adds saved dated snapshots, state metrics, deterministic conflicts, reviewed campus-room links and filtered room state. M3 adds saved room-closure simulations and baseline comparisons, with verified local sequential API performance. Actual mappings remain unconfirmed until you approve them in the review screen. Offline ML comparison is implemented; prediction serving and UI remain pending. See [M2 review instructions](docs/m2-review.md), [verification and migration setup](docs/m2-verification.md), [M3 performance](docs/m3-performance.md), and the [milestone tracker](docs/blueprint.md#current-progress-tracker).

The authenticated workspace now includes an interactive 3D Jeppiaar campus model with IT/ECE floor and room exploration. Geometry is approximate; room assignments follow user-confirmed details. Physical spaces remain separate from synthetic records until explicitly mapped. See [campus model guide](docs/campus-model.md) for the layout, configuration, limitations, and verification instructions.

The design, responsibilities and 12-week plan live in [docs/blueprint.md](docs/blueprint.md). The frontend/integration owner starts against mocked responses in **week 4**, not week 9.

## New developer setup — Windows, without Docker

Follow these steps in order. Run each command separately; if one fails, resolve that error before continuing. The examples use `V:\college twin` as the checkout folder. Replace that path with your own checkout location wherever it appears.

There are three parts to run:

| Part | What it does | Where it runs |
|---|---|---|
| PostgreSQL | Stores the college data and login accounts | Windows service, normally port 5432 |
| Backend | Handles login and reads the database | Terminal 1, port 8000 |
| Frontend | Displays the website | Terminal 2, port 5173 |

### 1. Check the required software

Use **PowerShell 7.1 or newer** for these instructions; the hidden password prompt uses `Read-Host -MaskInput`. Install Python 3.13, Node.js 24, and PostgreSQL Server with its command-line tools if they are missing. PostgreSQL 17 is the original project target; the current developer machine has PostgreSQL 18 running, and the paths below use version 18. If you installed version 17, change `18` to `17` in the PostgreSQL executable paths. Docker is not needed for this guide.

In **PowerShell**, check:

```powershell
$PSVersionTable.PSVersion
python --version
node --version
npm.cmd --version
Get-Service -Name '*postgres*'
```

Your PostgreSQL service should show `Running`. If it is stopped, start the matching PostgreSQL service through Windows Services. Keep the PostgreSQL `postgres` account password you chose during installation available; you will need it below.

### 2. Install project dependencies — Terminal 1

In **PowerShell**, enter the project folder and create its Python environment once:

```powershell
Set-Location 'V:\college twin'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock
npm.cmd ci --prefix frontend
```

If `.venv` already exists, skip creating it again. All Python commands below name its interpreter explicitly, so you do not need to activate the environment.

**If you already use uv**, replace the pip installation command with this command from the project root:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -e .\backend -c .\backend\requirements.lock
```

Alternatively, `uv pip install .` works from `backend` with an activated environment. The editable form (`-e`) picks up code changes without reinstalling. The constraint file selects the project's locked dependency versions. Alembic migration files remain in the checkout; run migrations from `backend`.

### 3. Create the database — one time only

Run this command in **PowerShell**, not inside PostgreSQL:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -p 5432 -U postgres -d postgres
```

When prompted, enter your **PostgreSQL installation password**. Nothing appears while typing. A successful connection shows `postgres=#`.

You are now inside **PostgreSQL's SQL shell**. Copy only this SQL command, without a prompt prefix or a backslash before the underscore:

```sql
CREATE DATABASE college_twin;
```

Expected result: `CREATE DATABASE`. If it says `database "college_twin" already exists`, use that existing project database and continue; do not delete it.

Exit the SQL shell by typing:

```text
\q
```

You should now see a PowerShell prompt beginning with `PS`. All remaining setup commands run in PowerShell.

### 4. Connect the backend to PostgreSQL — Terminal 1

In **the same PowerShell terminal**, run:

```powershell
Set-Location 'V:\college twin\backend'
$dbPassword = Read-Host 'Your PostgreSQL installation password' -MaskInput
$env:DATABASE_URL = "postgresql+psycopg://postgres:$([Uri]::EscapeDataString($dbPassword))@localhost:5432/college_twin"
Remove-Variable dbPassword
$env:APP_ORIGIN = 'http://localhost:5173'
$env:COOKIE_SECURE = 'false'
```

This sets the backend's database connection for **this terminal only**. The password is encoded automatically, so characters such as `@`, `:` and `#` work. Do not print or share `DATABASE_URL`. Keep this terminal open through steps 5–7. If your PostgreSQL server uses another port or administrator username, change `5432` or `postgres` accordingly.

### 5. Create tables and load synthetic college data — Terminal 1

First create the tables inside the database:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
```

This must return without an error. If migrations have already been applied, it may produce no output. Next load the reproducible dataset:

```powershell
..\.venv\Scripts\python.exe -m app.cli seed --seed 42 --weeks 16
```

Expected result: `Loaded new edition`, followed by counts including **240 students, 16 faculty, 12 rooms, 2,560 classes and 76,800 attendance records**. On a repeat run, `Edition already loaded; unchanged` is normal. Do not recreate the database to rerun this step.

### 6. Create your website login — Terminal 1

```powershell
..\.venv\Scripts\python.exe -m app.cli create-user planner --role planner
```

Choose and remember a **new password of at least 16 characters**. It is hidden while you type. This is the website password, separate from the PostgreSQL installation password. The command returns to PowerShell after creating the account. Repeating it does not reset an existing account's password.

| Login | Username | Password |
|---|---|---|
| PostgreSQL connection | `postgres` | Password chosen during PostgreSQL installation |
| College Twin website | `planner` | Password chosen in this step |

Optional: create a read-only website account with:

```powershell
..\.venv\Scripts\python.exe -m app.cli create-user viewer --role viewer
```

### 7. Start the backend — Terminal 1

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Expected output includes `Uvicorn running on http://127.0.0.1:8000`. **Leave this terminal running.** Open [backend health](http://127.0.0.1:8000/api/v1/health); a working database connection returns JSON containing `"status":"ok"`. API documentation is at [backend API docs](http://127.0.0.1:8000/api/docs).

### 8. Start the frontend and sign in — Terminal 2

Open a **second PowerShell terminal** and run:

```powershell
Set-Location 'V:\college twin'
npm.cmd run dev --prefix frontend -- --port 5173 --strictPort
```

Leave this terminal running too. Open [College Twin](http://localhost:5173) and sign in with `planner` and the **website password from step 6**. You should see the dataset edition and room inventory. Saved planning snapshots support the M3 room-closure comparison described below; prediction is a later milestone.

Use `localhost:5173` consistently. The frontend forwards `/api` requests to the backend on port 8000. The strict port option prevents Vite from silently choosing a different port that would no longer match `APP_ORIGIN`. If the frontend is already running at this address, reuse it rather than launching a second copy.

### Starting again the next day

After one-time setup, start **both backend and frontend with one command** from the project root:

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py
```

Open [College Twin](http://localhost:5173) and use your existing website account. Keep the terminal open; Ctrl+C stops both services started by this command. The launcher checks configuration, database connectivity, migration head, dataset/account presence and free ports first. It does not create or reset data/accounts. If it requests a migration, run `alembic upgrade head` from `backend` as in step 5 and retry. To check setup without starting services, add `--check`. See [M1 verification and teammate checklist](docs/m1-verification.md).

For a previously configured local database, save your connection once in `backend/local-settings.json` (copy `backend/local-settings.example.json` if absent). Enter the PostgreSQL installation password in `database.password`; host, port, database and username are already supplied. Password special characters are URL-encoded automatically. This private file is ignored by Git. It also supplies the local frontend origin, so terminal environment variables are unnecessary. Explicit environment variables still override local defaults for deployments and tests.

With the saved file configured, use the one-command launcher above. For separate terminals, `& 'V:\college twin\scripts\start_backend.ps1'` remains available for backend-only startup, followed by step 8 for the frontend. When using the saved-file method, skip the environment-variable setup in step 4; migrations and CLI commands run from `backend` read the same file.

The database, tables, synthetic data and accounts remain saved when terminals close. You do **not** repeat database creation, seeding or account creation every day.

1. Confirm the PostgreSQL service is running.
2. Use your saved local configuration, or repeat **step 4** to set connection variables in the terminal you will use.
3. From the project root, run `start_local.py` using the command above.
4. After pulling code changes, run `alembic upgrade head` as in step 5 before starting services. Reinstall dependencies only when the dependency files change.

Press `Ctrl+C` in each terminal to stop its development server. Closing Terminal 1 clears its connection environment variables; PostgreSQL keeps the data.

### Common setup problems

| What you see | What to do |
|---|---|
| `syntax error at or near "&"` or a prompt ending in `-#` | A PowerShell command was pasted into the SQL shell, or SQL input is unfinished. Press `Ctrl+C` to clear the pending input. At `postgres=#`, run only the SQL in step 3; use `\q` before running PowerShell commands. |
| `database "college_twin" already exists` | Continue to step 4. Do not drop the database. |
| `password authentication failed for user "postgres"` | Repeat step 4 with the PostgreSQL installation password, not the website password. |
| `connection refused` on port 5432 | Check that the intended PostgreSQL service is running and that its configured port matches step 4. |
| `database_url` is missing | Repeat step 4 in the exact terminal used to run the backend or migration command. |
| `No module named ...` | Use the explicit `.venv` interpreter shown above and finish dependency installation in step 2. |
| `relation ... does not exist` | Run `alembic upgrade head` from `backend`, using the same database connection as the API. |
| `Origin not allowed` | Set `APP_ORIGIN` to `http://localhost:5173` in Terminal 1, restart the backend, and open that exact frontend address. |
| `Invalid username or password` on the website | Use `planner` and the password from step 6. Rerunning `create-user` does not change an existing password. |
| `Too many login attempts` | Wait one minute, then retry with the website credentials. |
| Frontend cannot reach the server | Keep Terminal 1 running and check the backend health link in step 7. |
| Port 8000 or 5173 is already in use | Reuse the existing project server or stop your previous copy with `Ctrl+C`; do not start duplicate servers. |

## Optional: generate data without a database

From `backend` in PowerShell:

```powershell
..\.venv\Scripts\python.exe -m app.cli generate --seed 42 --weeks 16 --output ..\data\seed-42.json
```

This validates and exports JSON; it does not load PostgreSQL. Same seed, generator version, configuration and locked dependencies produce the same logical data. Generated JSON is ignored by Git; commit the generator and lockfiles instead.

## Database permissions for shared demos

The walkthrough above uses `postgres` for personal local development. For shared demos, use a restricted runtime database role. `python -m app.cli bootstrap` creates local planner/viewer accounts, provisions the fixed `twin_app` role, and seeds the default edition. It requires admin `DATABASE_URL` and separate `PLANNER_PASSWORD`, `VIEWER_PASSWORD`, `API_DB_PASSWORD` environment values. It must run only against the dedicated project database/cluster because the PostgreSQL role is cluster-scoped. Restart the API with `DATABASE_URL` using `twin_app`; it has SELECT-only domain permissions plus the auth/audit permissions it needs. Do not run the public API with an administrative database account outside personal local development.

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

Container files are supplied but Docker startup/build remain pending. PostgreSQL integration verification passed locally on 2026-09-21 without Docker. When Docker work is resumed:

```powershell
python scripts\setup_env.py
docker compose up --build -d
```

The setup script creates `.env` with independent random secrets without printing or overwriting them. Open that local file to retrieve the `planner` and `viewer` passwords. Compose is designed to migrate, bootstrap and seed before the API starts, then serve the frontend at http://localhost:8080. Only the frontend port is published; the database remains internal. Existing datasets are preserved by idempotent seed loading. Container base tags still need digest locking after a verified build.

Optional later PostgreSQL tests: `docker compose --profile test up -d test-db`, followed by `.\.venv\Scripts\python.exe scripts\run_backend_tests.py`. This uses a separate disposable test database. Avoid removing the demo volume unless you intentionally want to erase its local data.

## Boundaries

- All generated records are synthetic and visibly labelled. No contact information is generated.
- M1's clean generator has complete attendance and feasible timetables. Sparse, shifted and deliberate-anomaly fixtures are later evaluation work.
- Historical sessions are stored as held with recording timestamps. M2 respects those timestamps when reconstructing an earlier cutoff; before the recorded final status it assumes the original timetable was scheduled.
- No AI provider is called and no simulation modifies source data.
- Login throttling is per process. Keep the planned single API worker; redesign throttling before scaling out.
- No integration test or Docker result is claimed until it actually runs successfully.


## M3 room-closure simulation

Core M3 now provides immutable saved runs and a React comparison screen. Apply the new local migration from `backend` with `..\.venv\Scripts\python.exe -m alembic upgrade head`, then restart the API. If using the restricted `twin_app` role, rerun the documented role-provisioning command to grant simulation SELECT/INSERT access.

Create a dated M2 snapshot with cutoff **00:00** (its window start), or open an existing suitable planning snapshot. Select a saved synthetic room and closure interval in **Compare a room closure**. The screen shows baseline, disrupted and reassigned demand, availability denominators, destination IDs and explicit candidate rejection reasons. Viewers can open a saved simulation ID. Source timetables and snapshots are never changed by a simulation.

Classes retain their times. The baseline must be conflict-free and contain complete scheduled classes; unresolved means no room was found under these fixed-time constraints. Actual campus links remain unconfirmed. See [M3 verification](docs/m3-verification.md) and [contract](docs/m3-contract.md) for tests and pending acceptance work.

C4 also supports selecting a reviewed campus room from the saved inventory. After a run, the campus shows labeled red closed rooms and blue reassignment destinations, with shortcuts to their floors. Highlights use the displayed **current mapping revision**, not a historical geometry replay. Only exact approved links for the run's edition are used; unmapped rooms remain identifiable by synthetic ID. This feature does not approve actual campus mappings.
