"""Exercise library router — /api/v1/exercises/*

Endpoints:
  GET    /           — List exercises (system + own custom), with search/filter
  POST   /           — Create a custom exercise
  GET    /{id}       — Get a single exercise
  PATCH  /{id}       — Update a custom exercise (owner only)
  DELETE /{id}       — Soft-delete a custom exercise (owner only)
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exercises import (
    CreateExerciseRequest,
    ExerciseListResponse,
    ExerciseResponse,
    UpdateExerciseRequest,
)
from app.services import exercise_service

router = APIRouter(prefix="/api/v1/exercises", tags=["exercises"])


@router.get("", response_model=ExerciseListResponse, summary="List exercises")
def list_exercises(
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
    equipment: str | None = Query(default=None),
    muscle_group: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseListResponse:
    items, total = exercise_service.list_exercises(
        db,
        current_user.id,
        search=search,
        category=category,
        equipment=equipment,
        muscle_group=muscle_group,
        page=page,
        page_size=page_size,
    )
    pages = max(1, math.ceil(total / page_size))
    return ExerciseListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.post(
    "",
    response_model=ExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom exercise",
)
def create_exercise(
    body: CreateExerciseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseResponse:
    return exercise_service.create_exercise(
        db,
        current_user.id,
        name=body.name,
        category=body.category.value,
        equipment=body.equipment.value,
        description=body.description,
        instructions=body.instructions,
        muscle_groups=body.muscle_groups or None,
    )


@router.get("/{exercise_id}", response_model=ExerciseResponse, summary="Get an exercise")
def get_exercise(
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseResponse:
    return exercise_service.get_exercise(db, exercise_id, current_user.id)


@router.patch("/{exercise_id}", response_model=ExerciseResponse, summary="Update a custom exercise")
def update_exercise(
    exercise_id: uuid.UUID,
    body: UpdateExerciseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseResponse:
    return exercise_service.update_exercise(
        db,
        exercise_id,
        current_user.id,
        name=body.name,
        description=body.description,
        instructions=body.instructions,
        category=body.category.value if body.category else None,
        muscle_groups=body.muscle_groups,
        equipment=body.equipment.value if body.equipment else None,
    )


@router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a custom exercise",
)
def delete_exercise(
    exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    exercise_service.delete_exercise(db, exercise_id, current_user.id)
