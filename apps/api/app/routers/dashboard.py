"""Dashboard router - /api/v1/dashboard/summary.

Single read-only endpoint that aggregates all widgets into one response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Return all dashboard widget data for the authenticated user."""
    return dashboard_service.get_dashboard_summary(db, user_id=current_user.id)
