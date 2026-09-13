import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import (
    DUMMY_HASH,
    current_user,
    digest,
    limiter,
    require_csrf,
    require_origin,
    verify_password,
)
from app.config import settings
from app.db import get_db
from app.schema import audit, auth_session, edition, room, user

app = FastAPI(
    title="College Twin", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
)
logger = logging.getLogger("college_twin")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    # Also enforced by the reverse proxy; guard ordinary direct API requests.
    size = request.headers.get("content-length")
    if size and (not size.isdigit() or int(size) > 16384):
        return error(request, 413, "Request body too large")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        "request id=%s method=%s path=%s status=%s",
        request.state.request_id,
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


def error(request: Request, status: int, message: str, fields=None):
    codes = {
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "request_too_large",
        422: "validation_error",
        429: "rate_limited",
        503: "unavailable",
    }
    return JSONResponse(
        status_code=status,
        content={
            "code": codes.get(status, "request_error"),
            "message": message,
            "field_errors": fields or [],
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not reflect request inputs (passwords) in validation errors.
    fields = [
        {"field": ".".join(map(str, item["loc"])), "message": item["msg"]} for item in exc.errors()
    ]
    return error(request, 422, "Invalid request", fields)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logger.error(
        "database failure request=%s type=%s", request.state.request_id, type(exc).__name__
    )
    return error(request, 503, "Database unavailable; please retry")


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=1, max_length=256)


def audit_event(db, request, actor_id, action):
    db.execute(
        audit.insert().values(
            id=uuid4(),
            actor_id=actor_id,
            action=action,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
            outcome="success",
        )
    )


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "milestone": "M1", "synthetic_data_only": True}


@app.post("/api/v1/auth/login")
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    require_origin(request)
    limiter.check(request.client.host if request.client else "unknown")
    actor = db.execute(select(user).where(user.c.username == body.username)).mappings().first()
    valid = verify_password(actor["password_hash"] if actor else DUMMY_HASH, body.password)
    if not actor or not valid:
        raise HTTPException(401, "Invalid username or password")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    old_token = request.cookies.get("twin_session", "")
    db.execute(
        delete(auth_session).where(
            (auth_session.c.expires_at <= datetime.now(UTC))
            | (auth_session.c.token_hash == digest(old_token))
        )
    )
    db.execute(
        auth_session.insert().values(
            token_hash=digest(token),
            user_id=actor["id"],
            csrf_hash=digest(csrf),
            expires_at=datetime.now(UTC) + timedelta(hours=settings().session_hours),
        )
    )
    audit_event(db, request, actor["id"], "login")
    db.commit()
    options = dict(
        secure=settings().cookie_secure,
        samesite="strict",
        path="/",
        max_age=settings().session_hours * 3600,
    )
    response.set_cookie("twin_session", token, httponly=True, **options)
    response.set_cookie("twin_csrf", csrf, httponly=False, **options)
    return {"id": actor["id"], "username": actor["username"], "role": actor["role"]}


@app.get("/api/v1/auth/me")
def me(actor=Depends(current_user)):
    return {key: actor[key] for key in ("id", "username", "role")}


@app.post("/api/v1/auth/logout", status_code=204)
def logout(
    request: Request, response: Response, actor=Depends(require_csrf), db: Session = Depends(get_db)
):
    db.execute(
        delete(auth_session).where(
            auth_session.c.token_hash == digest(request.cookies["twin_session"])
        )
    )
    audit_event(db, request, actor["id"], "logout")
    db.commit()
    response.delete_cookie("twin_session", path="/")
    response.delete_cookie("twin_csrf", path="/")


@app.get("/api/v1/datasets")
def datasets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor=Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(edition).where(edition.c.frozen_at.is_not(None))
    rows = (
        db.execute(stmt.order_by(edition.c.created_at, edition.c.id).limit(limit).offset(offset))
        .mappings()
        .all()
    )
    total = db.scalar(
        select(func.count()).select_from(edition).where(edition.c.frozen_at.is_not(None))
    )
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "synthetic_data_only": True,
    }


@app.get("/api/v1/rooms")
def rooms(
    edition_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not db.scalar(
        select(edition.c.id).where(edition.c.id == edition_id, edition.c.frozen_at.is_not(None))
    ):
        raise HTTPException(404, "Dataset not found")
    stmt = select(room).where(room.c.edition_id == edition_id)
    rows = db.execute(stmt.order_by(room.c.code).limit(limit).offset(offset)).mappings().all()
    total = db.scalar(select(func.count()).select_from(room).where(room.c.edition_id == edition_id))
    return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}
