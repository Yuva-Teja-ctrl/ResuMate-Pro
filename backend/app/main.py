"""
ResuMate Pro - FastAPI application entry point.

Creates the app, configures CORS for the frontend, registers routers, and
initializes the database on startup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, candidates, jobs
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (simple approach; use Alembic for real migrations).
    init_db()
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)


@app.get("/health", tags=["health"])
def health():
    """Liveness probe + shows which AI provider is active."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "database": "postgres" if settings.is_postgres else "sqlite",
    }


@app.get("/", tags=["health"])
def root():
    return {"message": "ResuMate Pro API. See /docs for interactive API docs."}
