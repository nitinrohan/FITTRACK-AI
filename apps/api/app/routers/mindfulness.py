"""Mindfulness router - /api/v1/mindfulness.

  GET    /api/v1/mindfulness/sessions        list library sessions (+ optional category)
  POST   /api/v1/mindfulness/sessions        create a custom session
  POST   /api/v1/mindfulness/logs            log mindful minutes
  GET    /api/v1/mindfulness/logs            list logs (paginated, newest first)
  GET    /api/v1/mindfulness/summary         today's minutes, sessions count, streak
  DELETE /api/v1/mindfulness/logs/{id}       delete a log

All endpoints require authentication. Logs and custom sessions are scoped to the
caller; system sessions are shared library content.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.mindfulness import (
    CreateSessionRequest,
    LogMindfulnessRequest,
    MindfulnessDailySummary,
    MindfulnessLogListResponse,
    MindfulnessLogResponse,
    MindfulnessSessionListResponse,
    MindfulnessSessionResponse,
)
from app.services import mindfulness_service

router = APIRouter(prefix="/api/v1/mindfulness", tags=["mindfulness"])


# ── Sessions ────────────────────────────────────────────────────────────────────


@router.get("/sessions", response_model=MindfulnessSessionListResponse)
def list_sessions(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MindfulnessSessionListResponse:
    return mindfulness_service.list_sessions(db, current_user.id, category=category)


@router.post(
    "/sessions",
    response_model=MindfulnessSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MindfulnessSessionResponse:
    return mindfulness_service.create_session(db, current_user.id, payload)


# ── Logs ────────────────────────────────────────────────────────────────────────


@router.post(
    "/logs", response_model=MindfulnessLogResponse, status_code=status.HTTP_201_CREATED
)
def log_minutes(
    payload: LogMindfulnessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MindfulnessLogResponse:
    return mindfulness_service.log_minutes(db, current_user.id, payload)


@router.get("/logs", response_model=MindfulnessLogListResponse)
def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MindfulnessLogListResponse:
    return mindfulness_service.list_logs(
        db, current_user.id, page=page, page_size=page_size
    )


@router.get("/summary", response_model=MindfulnessDailySummary)
def summary(
    on_date: date = Query(default_factory=date.today, alias="date"),
    tz: str = Query(default="UTC"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MindfulnessDailySummary:
    return mindfulness_service.daily_summary(
        db, current_user.id, on_date=on_date, tz=tz
    )


@router.delete(
    "/logs/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_log(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    mindfulness_service.delete_log(db, entry_id, current_user.id)
