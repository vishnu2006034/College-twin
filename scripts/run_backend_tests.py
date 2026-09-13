"""Run local tests against the separate Compose test database without echoing secrets."""
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
config = dotenv_values(root / ".env")
env = dict(os.environ)
env["TEST_DATABASE_URL"] = f"postgresql+psycopg://twin_test:{config['POSTGRES_PASSWORD']}@127.0.0.1:55432/college_twin_test"
raise SystemExit(subprocess.call([str(root / ".venv/Scripts/python.exe"), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                                 cwd=root / "backend", env=env))
