"""Database engine and session management.

All database interaction goes through the SQLAlchemy session returned by
get_db().  Routes and services should use Depends(get_db) — never import
the engine or SessionLocal directly.

Internal canonical units (stored in the DB):
  - Weight:    kilograms (float, 3 decimal places)
  - Distance:  meters    (float, 3 decimal places)
  - Volume:    milliliters (float, 1 decimal place)
  - Energy:    kilocalories (float, 1 decimal place)
  - Timestamps: UTC (stored without timezone info; assumed UTC)
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level engine and session factory — created lazily on first access
# so that tests can override DATABASE_URL before import.
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Detect stale connections before checkout.
            pool_size=10,
            max_overflow=20,
            echo=settings.app_env == "development",
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the SQLAlchemy session factory (public alias for scripts/seeds)."""
    return _get_session_factory()


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session, then close it."""
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """Verify that the database is reachable.

    Returns True if a trivial query succeeds, False otherwise.
    Used by the /ready health endpoint.
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connectivity check failed")
        return False


def reset_engine_for_testing() -> None:
    """Dispose of the current engine so tests can inject a different URL.

    Call this in test teardown if you need a clean slate between test modules.
    Not intended for production use.
    """
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
