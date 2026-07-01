"""FitTrack AI - FastAPI application entry point.

This module creates the FastAPI app, registers middleware, mounts routers,
and attaches exception handlers.  It is the only place that wires all the
pieces together.  Domain logic lives in services and repositories, not here.

Startup order:
  1. configure_logging() - set up structured logging first so that any
     errors during subsequent startup steps are captured.
  2. Log the active configuration summary (no secrets).
  3. The app is now ready to accept requests; Alembic migrations are run
     by the container entrypoint (see docker-compose.yml) before uvicorn
     starts, so by the time this lifespan runs the DB schema is current.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.logging_config import configure_logging
from app.routers import (
    ai,
    auth,
    dashboard,
    exercises,
    goals,
    habit,
    health,
    measurements,
    mindfulness,
    nutrition,
    privacy,
    progress,
    recipes,
    stress,
    users,
    weight,
    wellness,
    workouts,
)

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ────────────────────────────────────────────────────────
    configure_logging(
        level=settings.log_level,
        json_output=settings.is_production,
    )
    logger.info(
        "FitTrack API starting",
        extra={
            "env": settings.app_env,
            "ai_enabled": settings.ai_enabled,
            "ai_provider": settings.ai_provider,
        },
    )
    yield
    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("FitTrack API shutting down")


def create_app() -> FastAPI:
    """Application factory.  Returns a configured FastAPI instance."""

    app = FastAPI(
        title="FitTrack AI",
        description=(
            "AI-powered personal fitness tracker - workouts, nutrition, "
            "measurements, wellness, habits, goals, and progress insights."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Restrict which Host headers are accepted in production.
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Replace with real domain(s) in production.
        )

    # ── Exception handlers ─────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ────────────────────────────────────────────────────────
    # Health/readiness probes at root - no auth required.
    app.include_router(health.router)

    # ── API v1 ─────────────────────────────────────────────────────────
    # auth router mounts its own /api/v1/auth prefix internally.
    app.include_router(auth.router)

    # users router - profile, preferences, onboarding.
    app.include_router(users.router)

    # goals router - create, list, get, update, delete.
    app.include_router(goals.router)

    # weight router - log, list, get, update, delete weight entries.
    app.include_router(weight.router)

    # exercises router - system library + user custom exercises.
    app.include_router(exercises.router)

    # workouts router - templates + workout logging.
    app.include_router(workouts.router)

    # nutrition router - food library, food log, water log.
    app.include_router(nutrition.router)

    # recipes router - saved food combinations, re-loggable with scaling.
    app.include_router(recipes.router)

    # measurements router - body circumference measurements.
    app.include_router(measurements.router)

    # dashboard router - aggregated summary for the dashboard page.
    app.include_router(dashboard.router)

    # ai router - weekly summary and user decision recording.
    app.include_router(ai.router)

    # wellness router - sleep, steps, and wellness check-in.
    app.include_router(wellness.router)

    # habit router - habits and daily completions.
    app.include_router(habit.router)

    # progress router - time-series for charts.
    app.include_router(progress.router)

    # privacy router - data export, record summary, account deletion.
    app.include_router(privacy.router)

    # stress router - 0-100 stress readings + daily summary.
    app.include_router(stress.router)

    # mindfulness router - session library + mindful-minute logs.
    app.include_router(mindfulness.router)

    return app


app = create_app()


# Expose app metadata at root for quick sanity checks.
@app.get("/", include_in_schema=False)
def root() -> dict[str, Any]:
    return {
        "service": "fittrack-api",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
