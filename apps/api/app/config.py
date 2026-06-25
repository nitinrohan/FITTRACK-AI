"""Application configuration loaded from environment variables.

Uses pydantic-settings so every value is validated at startup.
Override any setting by exporting the corresponding env var or placing
it in a .env file at the project root.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Treat empty string env vars as None so fields fall back to their defaults.
        # Prevents pydantic_settings from crashing on BACKEND_CORS_ORIGINS="" etc.
        env_parse_none_str="",
    )

    # ── Application ─────────────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    app_secret_key: str = "change-this-secret"
    log_level: str = "INFO"

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql://fittrack:changeme@localhost:5432/fittrack"

    # ── JWT ─────────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ── CORS ────────────────────────────────────────────────────────────
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # Accept a JSON array string or a comma-separated string.
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(origin) for origin in parsed]
            except (json.JSONDecodeError, ValueError):
                return [origin.strip() for origin in v.split(",")]
        return list(v)

    # ── AI ───────────────────────────────────────────────────────────────
    ai_provider: Literal["anthropic", "openai", "ollama", "none"] = "none"
    ai_model: str = "claude-3-5-haiku-20241022"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    # Ollama runs models locally; no API key needed. Used mainly for local dev.
    ollama_base_url: str = "http://localhost:11434"

    # ── Derived helpers ──────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def ai_enabled(self) -> bool:
        if self.ai_provider == "none":
            return False
        if self.ai_provider == "anthropic" and not self.anthropic_api_key:
            return False
        if self.ai_provider == "openai" and not self.openai_api_key:
            return False
        if self.ai_provider == "ollama" and not self.ollama_base_url:
            return False
        return True


def _normalise_cors_env() -> None:
    """Normalise BACKEND_CORS_ORIGINS before pydantic_settings reads it.

    pydantic_settings calls json.loads() on list[str] fields automatically.
    If the env var contains single quotes, unquoted URLs, or is empty it will
    crash before our field_validator ever runs.  We fix the raw os.environ
    value in-place so Settings() always receives valid JSON.
    """
    raw = os.environ.get("BACKEND_CORS_ORIGINS", "").strip()
    if not raw:
        return  # empty → pydantic uses field default

    try:
        json.loads(raw)
        return  # already valid JSON, nothing to do
    except (json.JSONDecodeError, ValueError):
        pass

    # Best-effort recovery: strip outer brackets/quotes, split by comma,
    # strip per-item quotes, re-serialise as valid JSON array.
    inner = raw.strip("[]").strip()
    items = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
    if items:
        os.environ["BACKEND_CORS_ORIGINS"] = json.dumps(items)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Use FastAPI's Depends(get_settings) to inject settings into routes,
    or call directly in non-request contexts.
    """
    _normalise_cors_env()
    return Settings()
