"""
ResuMate Pro - FastAPI application entry point.

Creates the app, configures CORS for the frontend, registers routers, and
initializes the database on startup.
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.routes import auth, candidates, jobs
from app.core.config import settings
from app.db.session import engine, init_db

logger = logging.getLogger("resumate")


def _init_db_with_retry(attempts: int = 5, delay: float = 3.0) -> bool:
    """
    Create tables, retrying while the database wakes up.

    If the database is unreachable (e.g. an expired/deleted managed Postgres
    instance) we log the error and keep the API running instead of crashing
    on boot -- so /health can report the real problem and the frontend gets a
    proper error response rather than a dead host.
    """
    for i in range(1, attempts + 1):
        try:
            init_db()
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Database init failed (attempt %d/%d)", i, attempts)
            if i < attempts:
                time.sleep(delay)
    logger.error("Database is unreachable. Check the DATABASE_URL env var.")
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (simple approach; use Alembic for real migrations).
    _init_db_with_retry()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-based recruitment assistant: parse resumes, match to job "
    "descriptions, rank candidates, and generate interview questions.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # Browsers forbid credentials with a wildcard origin. We use Bearer tokens
    # (not cookies), so it's safe to disable credentials when allowing "*".
    allow_credentials="*" not in settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)


@app.exception_handler(OperationalError)
async def db_unavailable_handler(request: Request, exc: OperationalError):
    """Report a DB outage as 503 with a clear message (instead of a bare 500)."""
    logger.error("Database error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is unavailable. Please try again later."},
    )


@app.middleware("http")
async def cors_safe_errors(request: Request, call_next):
    """
    Guarantee CORS headers on *every* response, including unhandled 500s.

    Starlette's default 500 handler runs above the CORS middleware, so an
    unhandled exception would otherwise return a response with no CORS headers
    -- which browsers surface as a confusing "Load failed" instead of the real
    error. This wrapper catches anything that slips through and re-attaches the
    appropriate Access-Control-Allow-Origin header.
    """
    try:
        return await call_next(request)
    except Exception:
        origins = settings.cors_origins_list
        origin = request.headers.get("origin", "")
        allow = "*" if "*" in origins else (origin if origin in origins else "")
        headers = {"Access-Control-Allow-Origin": allow} if allow else {}
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again."},
            headers=headers,
        )


@app.get("/health", tags=["health"])
def health():
    """Liveness probe + shows which AI provider is active."""
    from app.services.ai.embeddings import active_backend

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "unreachable"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "embedding_backend": active_backend(),
        "database": "postgres" if settings.is_postgres else "sqlite",
        "database_status": db_status,
    }


@app.get("/", tags=["health"])
def root():
    return {"message": "ResuMate Pro API. See /docs for interactive API docs."}
