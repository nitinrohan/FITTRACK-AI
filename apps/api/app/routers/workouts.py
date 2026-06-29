"""Workouts router - /api/v1/workouts/* and /api/v1/templates/*

Template endpoints:
  POST   /api/v1/templates/                              - Create a template
  GET    /api/v1/templates/                              - List templates
  GET    /api/v1/templates/{template_id}                 - Get a template
  PUT    /api/v1/templates/{template_id}                 - Update a template
  DELETE /api/v1/templates/{template_id}                 - Delete a template

Workout session endpoints:
  POST   /api/v1/workouts/                               - Start a workout
  GET    /api/v1/workouts/                               - List workouts
  GET    /api/v1/workouts/{workout_id}                   - Get a workout
  POST   /api/v1/workouts/{workout_id}/complete          - Complete a workout
  PATCH  /api/v1/workouts/{workout_id}                   - Update name/notes
  DELETE /api/v1/workouts/{workout_id}                   - Delete a workout

Exercise management within a workout:
  POST   /api/v1/workouts/{workout_id}/exercises         - Add an exercise
  DELETE /api/v1/workouts/{workout_id}/exercises/{we_id} - Remove an exercise

Set logging:
  POST   /api/v1/workouts/{workout_id}/exercises/{we_id}/sets        - Log a set
  PATCH  /api/v1/workouts/{workout_id}/exercises/{we_id}/sets/{s_id} - Update a set
  DELETE /api/v1/workouts/{workout_id}/exercises/{we_id}/sets/{s_id} - Delete a set

All endpoints require authentication.
Ownership is enforced in the service layer - users can only touch their own data.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.workouts import (
    AddExerciseRequest,
    CompleteWorkoutRequest,
    CreateTemplateRequest,
    LogSetRequest,
    SetResponse,
    StartWorkoutRequest,
    TemplateListResponse,
    TemplateResponse,
    UpdateSetRequest,
    UpdateTemplateRequest,
    UpdateWorkoutRequest,
    WorkoutListResponse,
    WorkoutResponse,
)
from app.services import workout_service

# Two routers - separate prefixes, same module.
# NOTE: router.include_router() is called at the BOTTOM of this file, after all
# route functions are defined, so routes are not missed due to copy-at-call-time.
template_router = APIRouter(prefix="/api/v1/templates", tags=["workout-templates"])
workout_router = APIRouter(prefix="/api/v1/workouts", tags=["workouts"])


# ── Templates ─────────────────────────────────────────────────────────────────


@template_router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workout template",
)
def create_template(
    body: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return workout_service.create_template(db, current_user.id, body)


@template_router.get(
    "",
    response_model=TemplateListResponse,
    summary="List workout templates (own + system)",
)
def list_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateListResponse:
    return workout_service.list_templates(db, current_user.id, page=page, page_size=page_size)


@template_router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get a single workout template",
)
def get_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    result = workout_service.get_template(db, current_user.id, template_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    return result


@template_router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Update a workout template",
)
def update_template(
    template_id: uuid.UUID,
    body: UpdateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    result = workout_service.update_template(db, current_user.id, template_id, body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    return result


@template_router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a workout template",
)
def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = workout_service.delete_template(db, current_user.id, template_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")


# ── Workout sessions ──────────────────────────────────────────────────────────


@workout_router.post(
    "",
    response_model=WorkoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a workout session",
)
def start_workout(
    body: StartWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutResponse:
    return workout_service.start_workout(db, current_user.id, body)


@workout_router.get(
    "",
    response_model=WorkoutListResponse,
    summary="List workout sessions",
)
def list_workouts(
    completed_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutListResponse:
    return workout_service.list_workouts(
        db,
        current_user.id,
        completed_only=completed_only,
        page=page,
        page_size=page_size,
    )


@workout_router.get(
    "/{workout_id}",
    response_model=WorkoutResponse,
    summary="Get a workout session with all exercises and sets",
)
def get_workout(
    workout_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutResponse:
    result = workout_service.get_workout(db, current_user.id, workout_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found.")
    return result


@workout_router.post(
    "/{workout_id}/complete",
    response_model=WorkoutResponse,
    summary="Complete a workout session",
)
def complete_workout(
    workout_id: uuid.UUID,
    body: CompleteWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutResponse:
    result = workout_service.complete_workout(db, current_user.id, workout_id, body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found.")
    return result


@workout_router.patch(
    "/{workout_id}",
    response_model=WorkoutResponse,
    summary="Update workout name or notes",
)
def update_workout(
    workout_id: uuid.UUID,
    body: UpdateWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutResponse:
    result = workout_service.update_workout(db, current_user.id, workout_id, body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found.")
    return result


@workout_router.delete(
    "/{workout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a workout session",
)
def delete_workout(
    workout_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = workout_service.delete_workout(db, current_user.id, workout_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found.")


# ── Exercises within a workout ────────────────────────────────────────────────


@workout_router.post(
    "/{workout_id}/exercises",
    response_model=WorkoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exercise to an in-progress workout",
)
def add_exercise(
    workout_id: uuid.UUID,
    body: AddExerciseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutResponse:
    result = workout_service.add_exercise_to_workout(db, current_user.id, workout_id, body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found.")
    return result


@workout_router.delete(
    "/{workout_id}/exercises/{workout_exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove an exercise (and its sets) from a workout",
)
def remove_exercise(
    workout_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = workout_service.remove_exercise_from_workout(db, current_user.id, workout_exercise_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found in workout."
        )


# ── Sets ──────────────────────────────────────────────────────────────────────


@workout_router.post(
    "/{workout_id}/exercises/{workout_exercise_id}/sets",
    response_model=SetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a set for an exercise",
)
def log_set(
    workout_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
    body: LogSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SetResponse:
    result = workout_service.log_set(db, current_user.id, workout_exercise_id, body)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found in workout."
        )
    return result


@workout_router.patch(
    "/{workout_id}/exercises/{workout_exercise_id}/sets/{set_id}",
    response_model=SetResponse,
    summary="Update a logged set",
)
def update_set(
    workout_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
    set_id: uuid.UUID,
    body: UpdateSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SetResponse:
    result = workout_service.update_set(db, current_user.id, set_id, body)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found.")
    return result


@workout_router.delete(
    "/{workout_id}/exercises/{workout_exercise_id}/sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a logged set",
)
def delete_set(
    workout_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
    set_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = workout_service.delete_set(db, current_user.id, set_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found.")


# ── Aggregate router (registered last so all routes above are included) ────────
# include_router copies routes at call time - this must come after all @decorators.
router = APIRouter()
router.include_router(template_router)
router.include_router(workout_router)
