"""Repository functions for the habit domain.

All functions accept a SQLAlchemy Session and return ORM objects.
No business logic lives here - streak/adherence calculations belong in
habit_service.py.  Every query is scoped by user_id for data isolation.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.habit import Habit, HabitCompletion

# ── Habit ─────────────────────────────────────────────────────────────────────


def create_habit(db: Session, **kwargs: object) -> Habit:
    habit = Habit(**kwargs)
    db.add(habit)
    db.flush()
    return habit


def get_habit_by_id(db: Session, habit_id: uuid.UUID, user_id: uuid.UUID) -> Habit | None:
    stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    return db.scalars(stmt).first()


def list_habits(
    db: Session,
    user_id: uuid.UUID,
    *,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Habit], int]:
    stmt = select(Habit).where(Habit.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(Habit.is_archived.is_(False))

    total = len(db.execute(stmt.with_only_columns(Habit.id).order_by(None)).all())

    offset = (page - 1) * page_size
    habits = list(
        db.scalars(
            stmt.order_by(Habit.is_archived.asc(), Habit.created_at.asc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return habits, total


def update_habit_fields(db: Session, habit: Habit, **fields: object) -> Habit:
    for key, val in fields.items():
        setattr(habit, key, val)
    db.flush()
    return habit


def delete_habit(db: Session, habit: Habit) -> None:
    db.delete(habit)
    db.flush()


# ── HabitCompletion ───────────────────────────────────────────────────────────


def get_completion(
    db: Session, habit_id: uuid.UUID, on_date: date
) -> HabitCompletion | None:
    stmt = select(HabitCompletion).where(
        HabitCompletion.habit_id == habit_id,
        HabitCompletion.date == on_date,
    )
    return db.scalars(stmt).first()


def create_completion(
    db: Session, *, habit_id: uuid.UUID, user_id: uuid.UUID, on_date: date
) -> HabitCompletion:
    completion = HabitCompletion(habit_id=habit_id, user_id=user_id, date=on_date)
    db.add(completion)
    db.flush()
    return completion


def delete_completion(db: Session, completion: HabitCompletion) -> None:
    db.delete(completion)
    db.flush()


def list_completions(
    db: Session,
    habit_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[HabitCompletion]:
    """Return completions for a habit, newest first.

    Used by the service to compute streaks and adherence, and by the
    completions endpoint to render a history/calendar.
    """
    stmt = select(HabitCompletion).where(HabitCompletion.habit_id == habit_id)
    if date_from:
        stmt = stmt.where(HabitCompletion.date >= date_from)
    if date_to:
        stmt = stmt.where(HabitCompletion.date <= date_to)
    return list(db.scalars(stmt.order_by(HabitCompletion.date.desc())).all())
