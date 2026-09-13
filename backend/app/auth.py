import hashlib
import secrets
from collections import defaultdict, deque
from datetime import UTC, datetime
from threading import Lock
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.schema import auth_session, user

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except VerificationError:
        return False


def require_origin(request: Request):
    if request.headers.get("origin") != settings().app_origin:
        raise HTTPException(403, "Origin not allowed")


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("twin_session", "")
    if not token or len(token) > 128:
        raise HTTPException(401, "Sign in required")
    row = (
        db.execute(
            select(user.c.id, user.c.username, user.c.role, auth_session.c.csrf_hash)
            .join(auth_session, user.c.id == auth_session.c.user_id)
            .where(
                auth_session.c.token_hash == digest(token),
                auth_session.c.expires_at > datetime.now(UTC),
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(401, "Session expired or invalid")
    return row


def require_csrf(request: Request, actor=Depends(current_user)):
    require_origin(request)
    token = request.headers.get("x-csrf-token", "")
    if not token or not secrets.compare_digest(digest(token), actor["csrf_hash"]):
        raise HTTPException(403, "Invalid CSRF token")
    return actor


def require_planner(actor=Depends(require_csrf)):
    if actor["role"] != "planner":
        raise HTTPException(403, "Planner role required")
    return actor


class LoginLimiter:
    """Single-process MVP limiter. Proxy forwards no client-supplied IP headers."""

    def __init__(self):
        self.attempts = defaultdict(deque)
        self.lock = Lock()

    def check(self, address: str):
        now = monotonic()
        with self.lock:
            # Bounded by recent clients; remove expired entries on each request.
            for key in list(self.attempts):
                while self.attempts[key] and self.attempts[key][0] <= now - 60:
                    self.attempts[key].popleft()
                if not self.attempts[key]:
                    del self.attempts[key]
            attempts = self.attempts[address]
            if len(attempts) >= 10:
                raise HTTPException(429, "Too many login attempts; retry in one minute")
            attempts.append(now)


limiter = LoginLimiter()
