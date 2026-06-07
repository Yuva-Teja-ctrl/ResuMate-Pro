"""
Database engine and session management.

The engine is built from settings.database_url, which transparently falls
back to a local SQLite file when no DATABASE_URL is provided. This lets the
project run instantly in dev, and switch to Postgres in production purely
through an environment variable.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# SQLite needs a special flag when used with FastAPI's threaded server.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Imports models so they register on the metadata."""
    from app.models import user, job, candidate  # noqa: F401

    Base.metadata.create_all(bind=engine)
