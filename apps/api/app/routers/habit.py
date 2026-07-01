"""Habit router - /api/v1/habits.

  POST   /api/v1/habits                         create a habit
  GET    /api/v1/habits                         list habits (paginated)
  GET    /api/v1/habits/{id}                    get a single habit + stats
  PATCH  /api/v1/habits/{id}                    partial update (incl. archive)
  DELETE /api/v1/habits/{id}                    delete a habit (and its history)

  POST   /api/v1/habits/{id}/completions        mark complete (idempotent)
  GET    /api/v1/habits/{id}/completions        completion history
  DELETE /api/v1/habits/{id}/completions/{date} un-mark a date

All endpoints require authentication and operate only on the caller's data.

The `today` query parameter lets the client pass its own local calendar date
so streak / "completed today" figures are correct regardless of server time
zone.  It defaults to the server's current date when omitted.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundError
from app.models.user import User
from app.schemas.habit import (
    CompletionResponse,
    CreateHabitRequest,
    HabitCompletionsResponse,
    HabitListResponse,
    HabitResponse,
    MarkCompletionRequest,
    UpdateHabitRequest,
)
from app.services import habit_service

router = APIRouter(prefix="/api/v1/habits", tags=["habits"])


def _today_or(value: date | None) -> date:
    return value or date.today()


# ── Habit CRUD ──────────────────────────────────────────────────────────────────


@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    payload: CreateHabitRequest,
    today: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitResponse:
    return habit_service.create_habit(
        db, current_user.id, payload, today=_today_or(today)
    )


@router.get("", response_model=HabitListResponse)
def list_habits(
    include_archived: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    today: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitListResponse:
    return habit_service.list_habits(
        db,
        current_user.id,
        today=_today_or(today),
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.get("/{habit_id}", response_model=HabitResponse)
def get_habit(
    habit_id: uuid.UUID,
    today: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitResponse:
    return habit_service.get_habit(db, habit_id, current_user.id, today=_today_or(today))


@router.patch("/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: uuid.UUID,
    payload: UpdateHabitRequest,
    today: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitResponse:
    return habit_service.update_habit(
        db, habit_id, current_user.id, payload, today=_today_or(today)
    )


@router.delete(
    "/{habit_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_habit(
    habit_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not habit_service.delete_habit(db, habit_id, current_user.id):
        raise NotFoundError("Habit not found.")


# ── Completions ──────────────────────────────────────────────────────────────────


@router.post(
    "/{habit_id}/completions",
    response_model=CompletionResponse,
    status_code=status.HTTP_201_CREATED,
)
def mark_complete(
    habit_id: uuid.UUID,
    payload: MarkCompletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompletionResponse:
    on_date = payload.date or date.today()
    return habit_service.mark_complete(db, habit_id, current_user.id, on_date)


@router.get("/{habit_id}/completions", response_model=HabitCompletionsResponse)
def list_completions(
    habit_id: uuid.UUID,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HabitCompletionsResponse:
    return habit_service.list_completions(
        db, habit_id, current_user.id, date_from=date_from, date_to=date_to
    )


@router.delete(
    "/{habit_id}/completions/{on_date}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def unmark_complete(
    habit_id: uuid.UUID,
    on_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not habit_service.unmark_complete(db, habit_id, current_user.id, on_date):
        raise NotFoundError("Habit completion not found.")
