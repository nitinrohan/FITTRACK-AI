"""Application configuration loaded from environment variables.

Uses pydantic-settings so every value is validated at startup.
Override any setting by exporting the corresponding env var or placing
it in a .env file at the project root.
"""

from __future__ import annotations

import json
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
    ai_provider: Literal["anthropic", "openai", "none"] = "none"
    ai_model: str = "claude-3-5-haiku-20241022"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

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
        return True


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Use FastAPI's Depends(get_settings) to inject settings into routes,
    or call directly in non-request contexts.
    """
    return Settings()
