"""
Application configuration.

We use pydantic-settings so that every value can be overridden by an
environment variable (or a .env file) without changing code. Sensible
defaults mean the app boots with ZERO configuration for local dev.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- App ----
    APP_NAME: str = "ResuMate Pro"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    # ---- Security ----
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h
    ALGORITHM: str = "HS256"

    # ---- Database ----
    # Empty -> fall back to a local SQLite file (see database_url property).
    DATABASE_URL: str = ""

    # ---- AI ----
    AI_PROVIDER: str = "local"  # "local" | "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    @property
    def database_url(self) -> str:
        """Return a usable DB URL, defaulting to a local SQLite file."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return "sqlite:///./resumate.db"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (read env once)."""
    return Settings()


settings = get_settings()
