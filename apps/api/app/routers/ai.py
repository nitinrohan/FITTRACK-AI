"""AI feature router - /api/v1/ai/*

Endpoints:
  POST /weekly-summary       - Generate a weekly summary (read-only; no data mutation).
  POST /weekly-summary/accept - Record user's accept/dismiss decision.

All endpoints require authentication.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import AcceptSummaryRequest, WeeklySummaryResponse
from app.services import weekly_summary_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post(
    "/weekly-summary",
    response_model=WeeklySummaryResponse,
    summary="Generate a weekly fitness summary",
)
def generate_weekly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeeklySummaryResponse:
    """Generate a weekly summary from the last 7 days of the user's data.

    This endpoint is read-only - it never modifies user data.  If the AI
    provider is unavailable, a rule-based summary is returned instead.
    The response always includes `ai_available` to tell the frontend which
    path was taken.
    """
    return weekly_summary_service.get_weekly_summary(db, user_id=current_user.id)


@router.post(
    "/weekly-summary/accept",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Record user decision about a weekly summary",
)
def accept_weekly_summary(
    body: AcceptSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Record whether the user accepted or dismissed the AI summary.

    The `log_id` must come from a previous /weekly-summary response.
    We do NOT verify that the log belongs to this user here because the
    log_id is a UUID that the user cannot guess; treat it as a capability
    token.  Future work: add user_id check for belt-and-suspenders.
    """
    found = weekly_summary_service.record_user_decision(
        db, log_id=body.log_id, accepted=body.accepted
    )
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LOG_NOT_FOUND", "message": "Summary log not found."},
        )
