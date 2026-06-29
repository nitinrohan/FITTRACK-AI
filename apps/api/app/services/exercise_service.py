"""Exercise service - business logic for the exercise library.

Rules:
- Any authenticated user can read system exercises and their own custom ones.
- Users can create, update, and soft-delete their own custom exercises.
- System exercises cannot be modified or deleted by users (admin only, future).
- Duplicate names (case-insensitive) are rejected within the same scope
  (system exercises globally; custom exercises per user).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError
from app.models.exercise import Exercise
from app.repositories import exercise_repository
from app.schemas.exercises import ExerciseResponse


def _to_response(exercise: Exercise) -> ExerciseResponse:
    return ExerciseResponse.from_orm_with_groups(exercise)


def list_exercises(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    category: str | None = None,
    equipment: str | None = None,
    muscle_group: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ExerciseResponse], int]:
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    items, total = exercise_repository.get_visible_to_user(
        db,
        user_id,
        search=search,
        category=category,
        equipment=equipment,
        muscle_group=muscle_group,
        offset=offset,
        limit=page_size,
    )
    return [_to_response(e) for e in items], total


def get_exercise(db: Session, exercise_id: uuid.UUID, user_id: uuid.UUID) -> ExerciseResponse:
    exercise = exercise_repository.get_by_id(db, exercise_id)
    if not exercise:
        raise NotFoundError("Exercise not found")
    # Must be a system exercise OR owned by the requesting user
    if not exercise.is_system and exercise.user_id != user_id:
        raise NotFoundError("Exercise not found")
    return _to_response(exercise)


def create_exercise(
    db: Session,
    user_id: uuid.UUID,
    *,
    name: str,
    category: str,
    equipment: str,
    description: str | None = None,
    instructions: str | None = None,
    muscle_groups: list[str] | None = None,
) -> ExerciseResponse:
    exercise = exercise_repository.create(
        db,
        name=name,
        category=category,
        equipment=equipment,
        description=description,
        instructions=instructions,
        muscle_groups=muscle_groups,
        is_system=False,
        user_id=user_id,
    )
    db.commit()
    db.refresh(exercise)
    return _to_response(exercise)


def update_exercise(
    db: Session,
    exercise_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    instructions: str | None = None,
    category: str | None = None,
    muscle_groups: list[str] | None = None,
    equipment: str | None = None,
) -> ExerciseResponse:
    exercise = exercise_repository.get_by_id(db, exercise_id)
    if not exercise:
        raise NotFoundError("Exercise not found")
    if exercise.is_system:
        raise ForbiddenError("System exercises cannot be modified")
    if exercise.user_id != user_id:
        raise ForbiddenError("You do not own this exercise")

    exercise = exercise_repository.update(
        db,
        exercise,
        name=name,
        description=description,
        instructions=instructions,
        category=category,
        muscle_groups=muscle_groups,
        equipment=equipment,
    )
    db.commit()
    db.refresh(exercise)
    return _to_response(exercise)


def delete_exercise(db: Session, exercise_id: uuid.UUID, user_id: uuid.UUID) -> None:
    exercise = exercise_repository.get_by_id(db, exercise_id)
    if not exercise:
        raise NotFoundError("Exercise not found")
    if exercise.is_system:
        raise ForbiddenError("System exercises cannot be deleted")
    if exercise.user_id != user_id:
        raise ForbiddenError("You do not own this exercise")

    exercise_repository.soft_delete(db, exercise)
    db.commit()
