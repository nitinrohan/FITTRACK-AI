"""Progress router - /api/v1/progress.

  GET /api/v1/progress?days=N   time-series for weight, workouts and calories
                                over the last N days (7-365, default 30).

Requires authentication; returns only the caller's data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.progress import ProgressResponse
from app.services import progress_service

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("", response_model=ProgressResponse)
def get_progress(
    days: int = Query(default=progress_service.DEFAULT_DAYS, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressResponse:
    return progress_service.get_progress(db, user_id=current_user.id, days=days)
