"""Pytest configuration and shared fixtures.

Fixtures are organised by scope:
  - session-scoped: expensive setup that can be shared across all tests
    (e.g. creating the test database engine).
  - function-scoped: per-test setup/teardown (e.g. a clean DB transaction
    that is rolled back after each test so tests stay isolated).

Environment override strategy:
  Tests set APP_ENV=test and DATABASE_URL before importing app modules,
  because app.config uses @lru_cache.  The reset_engine_for_testing()
  helper lets us swap database URLs without restarting the process.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Set test env vars before any app module is imported.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://fittrack:testpassword@localhost:5432/fittrack_test",
)
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production")

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    """Return the test settings instance."""
    # Clear the lru_cache so test env vars take effect.
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session")
def client():
    """HTTP test client for the FastAPI app.

    Session-scoped: the app startup/shutdown lifespan runs once for the
    entire test session rather than per test.
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
