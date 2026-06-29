"""Exercise repository - all database access for exercises."""

from __future__ import annotations

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.exercise import Exercise


def get_by_id(db: Session, exercise_id: uuid.UUID) -> Exercise | None:
    return db.query(Exercise).filter(Exercise.id == exercise_id, Exercise.is_active == True).first()  # noqa: E712


def get_visible_to_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    equipment: str | None = None,
    muscle_group: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Exercise], int]:
    """Return exercises visible to a user: all system exercises + their own custom ones.

    Returns (items, total_count).
    """
    q = db.query(Exercise).filter(
        Exercise.is_active == True,  # noqa: E712
        or_(Exercise.is_system == True, Exercise.user_id == user_id),  # noqa: E712
    )

    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(Exercise.name.ilike(pattern))

    if category:
        q = q.filter(Exercise.category == category)

    if equipment:
        q = q.filter(Exercise.equipment == equipment)

    if muscle_group:
        # CSV contains the muscle group name somewhere
        q = q.filter(Exercise.muscle_groups.ilike(f"%{muscle_group}%"))

    total = q.count()
    items = q.order_by(Exercise.name).offset(offset).limit(limit).all()
    return items, total


def create(
    db: Session,
    *,
    name: str,
    category: str,
    equipment: str,
    description: str | None = None,
    instructions: str | None = None,
    muscle_groups: list[str] | None = None,
    is_system: bool = False,
    user_id: uuid.UUID | None = None,
) -> Exercise:
    exercise = Exercise(
        name=name,
        category=category,
        equipment=equipment,
        description=description,
        instructions=instructions,
        muscle_groups=",".join(muscle_groups) if muscle_groups else None,
        is_system=is_system,
        user_id=user_id,
    )
    db.add(exercise)
    db.flush()
    return exercise


def update(
    db: Session,
    exercise: Exercise,
    *,
    name: str | None = None,
    description: str | None = None,
    instructions: str | None = None,
    category: str | None = None,
    muscle_groups: list[str] | None = None,
    equipment: str | None = None,
) -> Exercise:
    if name is not None:
        exercise.name = name
    if description is not None:
        exercise.description = description
    if instructions is not None:
        exercise.instructions = instructions
    if category is not None:
        exercise.category = category
    if muscle_groups is not None:
        exercise.muscle_groups = ",".join(muscle_groups)
    if equipment is not None:
        exercise.equipment = equipment
    db.flush()
    return exercise


def soft_delete(db: Session, exercise: Exercise) -> None:
    exercise.is_active = False
    db.flush()


def system_exists(db: Session) -> bool:
    """Return True if the system exercise library has already been seeded."""
    return db.query(Exercise).filter(Exercise.is_system == True).count() > 0  # noqa: E712
