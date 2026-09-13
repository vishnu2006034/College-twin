"""Generate local-only credentials without printing or overwriting them."""
import secrets
from pathlib import Path

target = Path(__file__).resolve().parents[1] / ".env"
if target.exists():
    print(".env already exists; left unchanged")
else:
    names = ("POSTGRES_PASSWORD", "API_DB_PASSWORD", "PLANNER_PASSWORD", "VIEWER_PASSWORD")
    content = "\n".join(f"{name}={secrets.token_urlsafe(32)}" for name in names)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content + "\nAPP_ORIGIN=http://localhost:8080\nCOOKIE_SECURE=false\n")
    print("Created .env. Open it locally to retrieve planner/viewer passwords; do not commit it.")
