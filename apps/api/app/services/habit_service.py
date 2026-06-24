"""Business logic for the habit domain — CRUD, completions, and the
derived streak / adherence calculations.

Domain calculations (pure, unit-tested):
  - compute_current_streak  : consecutive completed days up to today.
  - compute_longest_streak  : longest run of consecutive completed days ever.
  - completions_in_week      : completions in the current (Mon-today) week.
  - weekly_adherence_pct     : completions_this_week / target, capped at 100%.

All derived figures are explicitly that — derived.  They are never stored.
The "current streak" is intentionally forgiving: not having completed *today*
does not immediately zero the streak, because the day is not over yet.

Services follow the commit-then-re-fetch pattern used across the codebase so
they remain testable with MagicMock sessions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.habit import Habit
from app.repositories import habit_repository
from app.schemas.habit import (
    CompletionResponse,
    CreateHabitRequest,
    HabitCompletionsResponse,
    HabitListResponse,
    HabitResponse,
    UpdateHabitRequest,
)

# ── Pure domain calculations ────────────────────────────────────────────────────


def compute_current_streak(completed: set[date], today: date) -> int:
    """Number of consecutive completed days ending at today (or yesterday).

    If today is completed, the streak includes today.  If today is not yet
    completed but yesterday was, the streak counts up to yesterday (today is
    still in progress).  Otherwise the streak is 0.
    """
    if today in completed:
        cursor = today
    elif (today - timedelta(days=1)) in completed:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in completed:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_longest_streak(completed: set[date]) -> int:
    """Longest run of consecutive completed days in the full history."""
    if not completed:
        return 0
    ordered = sorted(completed)
    longest = 1
    current = 1
    for prev, curr in pairwise(ordered):
        if (curr - prev).days == 1:
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest


def completions_in_week(completed: set[date], today: date) -> int:
    """Count completions from Monday of the current week up to and including today."""
    week_start = today - timedelta(days=today.weekday())  # Monday
    return sum(1 for d in completed if week_start <= d <= today)


def weekly_adherence_pct(completions_this_week: int, target_days_per_week: int) -> int:
    """Percentage of the weekly target met so far, capped at 100.

    Guards against a non-positive target (which validation should prevent).
    """
    if target_days_per_week <= 0:
        return 0
    pct = round(100 * completions_this_week / target_days_per_week)
    return min(100, max(0, pct))


# ── Response assembly ────────────────────────────────────────────────────────────


def _completed_dates(habit: Habit) -> set[date]:
    return {c.date for c in habit.completions}


def _habit_response(habit: Habit, today: date) -> HabitResponse:
    completed = _completed_dates(habit)
    this_week = completions_in_week(completed, today)
    return HabitResponse(
        id=habit.id,
        user_id=habit.user_id,
        name=habit.name,
        description=habit.description,
        color=habit.color,
        target_days_per_week=habit.target_days_per_week,
        is_archived=habit.is_archived,
        archived_at=habit.archived_at,
        created_at=habit.created_at,
        updated_at=habit.updated_at,
        completed_today=today in completed,
        current_streak=compute_current_streak(completed, today),
        longest_streak=compute_longest_streak(completed),
        completions_this_week=this_week,
        weekly_adherence_pct=weekly_adherence_pct(this_week, habit.target_days_per_week),
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Habit CRUD ──────────────────────────────────────────────────────────────────


def create_habit(
    db: Session, user_id: uuid.UUID, payload: CreateHabitRequest, *, today: date
) -> HabitResponse:
    habit = habit_repository.create_habit(
        db,
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        color=payload.color,
        target_days_per_week=payload.target_days_per_week,
    )
    db.commit()
    fetched = habit_repository.get_habit_by_id(db, habit.id, user_id)
    assert fetched is not None
    return _habit_response(fetched, today)


def list_habits(
    db: Session,
    user_id: uuid.UUID,
    *,
    today: date,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> HabitListResponse:
    habits, total = habit_repository.list_habits(
        db, user_id, include_archived=include_archived, page=page, page_size=page_size
    )
    return HabitListResponse(
        items=[_habit_response(h, today) for h in habits],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_habit(
    db: Session, habit_id: uuid.UUID, user_id: uuid.UUID, *, today: date
) -> HabitResponse:
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        raise NotFoundError("Habit not found.")
    return _habit_response(habit, today)


def update_habit(
    db: Session,
    habit_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateHabitRequest,
    *,
    today: date,
) -> HabitResponse:
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        raise NotFoundError("Habit not found.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationError("No fields provided to update.")

    # Maintain archived_at alongside the is_archived flag.
    if "is_archived" in updates:
        if updates["is_archived"] and not habit.is_archived:
            updates["archived_at"] = _utcnow()
        elif not updates["is_archived"]:
            updates["archived_at"] = None

    habit_repository.update_habit_fields(db, habit, **updates)
    db.commit()
    fetched = habit_repository.get_habit_by_id(db, habit_id, user_id)
    assert fetched is not None
    return _habit_response(fetched, today)


def delete_habit(db: Session, habit_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        return False
    habit_repository.delete_habit(db, habit)
    db.commit()
    return True


# ── Completions ──────────────────────────────────────────────────────────────────


def mark_complete(
    db: Session, habit_id: uuid.UUID, user_id: uuid.UUID, on_date: date
) -> CompletionResponse:
    """Mark a habit complete for a date.  Idempotent: an existing completion
    for that date is returned unchanged rather than duplicated."""
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        raise NotFoundError("Habit not found.")

    existing = habit_repository.get_completion(db, habit_id, on_date)
    if existing:
        return CompletionResponse.model_validate(existing)

    habit_repository.create_completion(
        db, habit_id=habit_id, user_id=user_id, on_date=on_date
    )
    db.commit()
    fetched = habit_repository.get_completion(db, habit_id, on_date)
    assert fetched is not None
    return CompletionResponse.model_validate(fetched)


def unmark_complete(
    db: Session, habit_id: uuid.UUID, user_id: uuid.UUID, on_date: date
) -> bool:
    """Remove a habit's completion for a date.  Returns False if the habit
    doesn't belong to the user or there was no completion to remove."""
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        return False
    existing = habit_repository.get_completion(db, habit_id, on_date)
    if not existing:
        return False
    habit_repository.delete_completion(db, existing)
    db.commit()
    return True


def list_completions(
    db: Session,
    habit_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> HabitCompletionsResponse:
    habit = habit_repository.get_habit_by_id(db, habit_id, user_id)
    if not habit:
        raise NotFoundError("Habit not found.")
    entries = habit_repository.list_completions(
        db, habit_id, date_from=date_from, date_to=date_to
    )
    return HabitCompletionsResponse(
        habit_id=habit_id,
        items=[CompletionResponse.model_validate(e) for e in entries],
    )
