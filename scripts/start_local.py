"""Start both local services after read-only setup checks. Ctrl+C stops owned services."""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def check_setup():
    if sys.version_info < (3, 13):
        raise RuntimeError("Use the project Python 3.13+ environment.")
    node = shutil.which("node")
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if not node or not vite.is_file():
        raise RuntimeError("Install Node and run npm.cmd ci --prefix frontend first.")
    try:
        import uvicorn  # noqa: F401
        from alembic.config import Config
        from alembic.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.config import settings
        from sqlalchemy import create_engine, text

        config = settings()
        engine = create_engine(config.database_url, connect_args={"connect_timeout": 5})
        try:
            migration_config = Config(str(ROOT / "backend/alembic.ini"))
            migration_config.set_main_option(
                "script_location", str(ROOT / "backend/migrations")
            )
            expected = set(ScriptDirectory.from_config(migration_config).get_heads())
            with engine.connect() as conn:
                actual = set(MigrationContext.configure(conn).get_current_heads())
                if actual != expected:
                    raise RuntimeError(
                        "Run alembic upgrade head from backend, then retry."
                    )
                if not conn.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM dataset_edition)")
                ):
                    raise RuntimeError(
                        "Load the synthetic dataset using the README seed step."
                    )
                if not conn.scalar(text("SELECT EXISTS (SELECT 1 FROM app_user)")):
                    raise RuntimeError(
                        "Create a website account using the README create-user step."
                    )
        finally:
            engine.dispose()
    except RuntimeError:
        raise
    except Exception:  # noqa: BLE001 - redact configuration/connection details at CLI boundary
        # Configuration and DB exceptions can carry connection details; never echo them.
        raise RuntimeError(
            "Setup check failed. Check dependencies, local settings and PostgreSQL. See README."
        ) from None
    return node, vite


def check_ports(ports):
    if len(set(ports)) != len(ports) or any(
        not 1024 <= port <= 65535 for port in ports
    ):
        raise RuntimeError(
            "Choose distinct backend/frontend ports between 1024 and 65535."
        )
    for port in ports:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise RuntimeError(
                    f"Port {port} is occupied. Reuse or stop its existing server; nothing was stopped."
                ) from None


def wait_ready(url, processes, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError(
                "A local service exited. Review the service output above."
            )
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Service did not become ready: {url}")


@contextmanager
def services(backend_port=8000, frontend_port=5173):
    node, vite = check_setup()
    check_ports((backend_port, frontend_port))
    env = dict(
        os.environ,
        APP_ORIGIN=f"http://localhost:{frontend_port}",
        COOKIE_SECURE="false",
        TWIN_API_TARGET=f"http://127.0.0.1:{backend_port}",
    )
    processes = []
    try:
        # Direct Python/Node children avoid npm/cmd wrapper trees during shutdown.
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(backend_port),
                    "--no-proxy-headers",
                ],
                cwd=ROOT / "backend",
                env=env,
            )
        )
        wait_ready(f"http://127.0.0.1:{backend_port}/api/v1/health", processes)
        processes.append(
            subprocess.Popen(
                [
                    node,
                    str(vite),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(frontend_port),
                    "--strictPort",
                ],
                cwd=ROOT / "frontend",
                env=env,
            )
        )
        wait_ready(f"http://127.0.0.1:{frontend_port}/api/v1/health", processes)
        yield processes
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only dependencies/database/migration check; starts nothing",
    )
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()
    try:
        if args.check:
            check_setup()
            print(
                "PASS: local dependencies, database, migration head, dataset and account available."
            )
            return 0
        with services(args.backend_port, args.frontend_port) as processes:
            print(
                f"College Twin ready: http://localhost:{args.frontend_port} — Ctrl+C stops both services.",
                flush=True,
            )
            while all(process.poll() is None for process in processes):
                time.sleep(0.5)
            raise RuntimeError(
                "A service stopped; both owned services have been shut down. Restart after reviewing its output."
            )
    except KeyboardInterrupt:
        print("Stopped local services.")
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
