"""Health and readiness endpoints.

/health  — Lightweight liveness probe. Returns immediately without touching
           the database.  Used by load balancers and container orchestrators
           to decide whether to send traffic to this instance.

/ready   — Readiness probe. Verifies database connectivity before reporting
           ready.  Used by orchestrators to decide whether the instance can
           handle requests (e.g., after a cold start or migration).

Both endpoints follow the standard { "status": "ok"|"degraded", ... } shape.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import check_database_connection

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get(
    "/health",
    summary="Liveness check",
    description=(
        "Returns 200 immediately if the application process is running. "
        "Does not verify database connectivity."
    ),
    response_description="Application is alive",
)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "fittrack-api",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description=(
        "Returns 200 when the application is ready to serve requests. "
        "Checks database connectivity. Returns 503 if any dependency is unavailable."
    ),
    response_description="Application is ready",
)
def ready() -> JSONResponse:
    db_ok = check_database_connection()

    checks: dict[str, str] = {
        "database": "ok" if db_ok else "unavailable",
    }
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    if not all_ok:
        logger.warning("Readiness check failed: %s", checks)

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
        },
    )
