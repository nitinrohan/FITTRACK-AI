"""Workout service — business logic for templates, workout sessions, and sets.

Responsibilities:
- Orchestrate template create/update (including exercise list replace).
- Start a workout, optionally pre-populating exercises from a template.
- Detect personal records (PR) when a set is logged.
- Compute total workout volume at completion.
- Build response objects (denormalising exercise names, computing durations).

Design notes:
- All DB mutations go through the repository; no SQLAlchemy queries here.
- PR detection is best-effort: if historical data is missing we mark is_pr=False.
- Volume formula: sum(weight_kg * reps) for sets where both values are present.
  This is "total tonnage" — a common and easily understood metric.
- Estimated 1RM (Epley formula) is available as a helper but not surfaced in
  responses yet; it is here for use in future analytics features.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.workout import Workout, WorkoutExercise, WorkoutSet, WorkoutTemplate
from app.repositories import workout_repository
from app.schemas.workouts import (
    AddExerciseRequest,
    CompleteWorkoutRequest,
    CreateTemplateRequest,
    LogSetRequest,
    SetResponse,
    StartWorkoutRequest,
    TemplateExerciseResponse,
    TemplateListResponse,
    TemplateResponse,
    UpdateSetRequest,
    UpdateTemplateRequest,
    UpdateWorkoutRequest,
    WorkoutExerciseResponse,
    WorkoutListResponse,
    WorkoutResponse,
    WorkoutSummary,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _duration_seconds(started_at: datetime, completed_at: datetime) -> int:
    """Return elapsed seconds between two naive UTC datetimes."""
    delta = completed_at - started_at
    return max(0, int(delta.total_seconds()))


def estimated_one_rep_max(weight_kg: float, reps: int) -> float | None:
    """Epley formula: weight x (1 + reps/30).

    Returns None for invalid inputs (reps=0 or weight=0).
    Clearly an estimate — not presented as exact.
    """
    if reps <= 0 or weight_kg <= 0:
        return None
    return round(weight_kg * (1 + reps / 30), 2)


def compute_volume_kg(sets: list[WorkoutSet]) -> float | None:
    """Total tonnage: sum(weight_kg x reps) for strength sets.

    Returns None if no sets have both weight and reps.
    """
    total = 0.0
    counted = 0
    for s in sets:
        if s.weight_kg is not None and s.reps is not None and s.reps > 0:
            total += s.weight_kg * s.reps
            counted += 1
    return round(total, 3) if counted > 0 else None


def is_strength_pr(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    weight_kg: float,
    reps: int,
) -> bool:
    """True if weight_kg * reps exceeds the user's previous best for this exercise."""
    best = workout_repository.get_best_set_for_exercise(db, user_id, exercise_id)
    if best is None:
        return True  # first ever logged set for this exercise = PR
    best_volume = (best.weight_kg or 0) * (best.reps or 0)
    return (weight_kg * reps) > best_volume


def is_duration_pr(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    duration_seconds: int,
) -> bool:
    best = workout_repository.get_best_duration_for_exercise(db, user_id, exercise_id)
    if best is None:
        return True
    return duration_seconds > (best.duration_seconds or 0)


def is_distance_pr(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
    distance_meters: float,
) -> bool:
    best = workout_repository.get_best_distance_for_exercise(db, user_id, exercise_id)
    if best is None:
        return True
    return distance_meters > (best.distance_meters or 0)


# ── Response builders ─────────────────────────────────────────────────────────


def _build_set_response(ws: WorkoutSet) -> SetResponse:
    return SetResponse(
        id=ws.id,
        set_number=ws.set_number,
        reps=ws.reps,
        weight_kg=ws.weight_kg,
        duration_seconds=ws.duration_seconds,
        distance_meters=ws.distance_meters,
        rpe=ws.rpe,
        is_pr=ws.is_pr,
        completed_at=ws.completed_at,
    )


def _build_exercise_response(we: WorkoutExercise) -> WorkoutExerciseResponse:
    return WorkoutExerciseResponse(
        id=we.id,
        exercise_id=we.exercise_id,
        order_index=we.order_index,
        notes=we.notes,
        exercise_name=we.exercise.name if we.exercise else "Unknown",
        exercise_category=we.exercise.category if we.exercise else None,
        sets=[_build_set_response(s) for s in (we.sets or [])],
    )


def _build_workout_response(workout: Workout) -> WorkoutResponse:
    duration = None
    if workout.completed_at is not None:
        duration = _duration_seconds(workout.started_at, workout.completed_at)
    return WorkoutResponse(
        id=workout.id,
        name=workout.name,
        notes=workout.notes,
        template_id=workout.template_id,
        template_name=workout.template.name if workout.template else None,
        started_at=workout.started_at,
        completed_at=workout.completed_at,
        total_volume_kg=workout.total_volume_kg,
        duration_seconds=duration,
        exercises=[_build_exercise_response(we) for we in (workout.exercises or [])],
        created_at=workout.created_at,
    )


def _build_workout_summary(workout: Workout) -> WorkoutSummary:
    duration = None
    if workout.completed_at is not None:
        duration = _duration_seconds(workout.started_at, workout.completed_at)

    exercise_count = len(workout.exercises or [])
    set_count = sum(len(we.sets or []) for we in (workout.exercises or []))

    return WorkoutSummary(
        id=workout.id,
        name=workout.name,
        template_id=workout.template_id,
        template_name=workout.template.name if workout.template else None,
        started_at=workout.started_at,
        completed_at=workout.completed_at,
        total_volume_kg=workout.total_volume_kg,
        duration_seconds=duration,
        exercise_count=exercise_count,
        set_count=set_count,
    )


def _build_template_exercise_response(
    te: Any,
) -> TemplateExerciseResponse:
    return TemplateExerciseResponse(
        id=te.id,
        exercise_id=te.exercise_id,
        order_index=te.order_index,
        default_sets=te.default_sets,
        default_reps=te.default_reps,
        default_weight_kg=te.default_weight_kg,
        default_duration_seconds=te.default_duration_seconds,
        default_distance_meters=te.default_distance_meters,
        notes=te.notes,
        exercise_name=te.exercise.name if te.exercise else "Unknown",
        exercise_category=te.exercise.category if te.exercise else None,
    )


def _build_template_response(template: WorkoutTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        is_system=template.is_system,
        exercises=[
            _build_template_exercise_response(te)
            for te in (template.template_exercises or [])
        ],
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ── Template operations ───────────────────────────────────────────────────────


def create_template(
    db: Session,
    user_id: uuid.UUID,
    payload: CreateTemplateRequest,
) -> TemplateResponse:
    template = workout_repository.create_template(
        db, user_id, payload.name, payload.description
    )
    for ex_in in payload.exercises:
        workout_repository.add_template_exercise(
            db,
            template_id=template.id,
            exercise_id=ex_in.exercise_id,
            order_index=ex_in.order_index,
            default_sets=ex_in.default_sets,
            default_reps=ex_in.default_reps,
            default_weight_kg=ex_in.default_weight_kg,
            default_duration_seconds=ex_in.default_duration_seconds,
            default_distance_meters=ex_in.default_distance_meters,
            notes=ex_in.notes,
        )
    db.commit()
    db.refresh(template)
    return _build_template_response(template)


def list_templates(
    db: Session,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> TemplateListResponse:
    offset = (page - 1) * page_size
    templates, total = workout_repository.list_templates_for_user(
        db, user_id, offset=offset, limit=page_size
    )
    return TemplateListResponse(
        templates=[_build_template_response(t) for t in templates],
        total=total,
    )


def get_template(
    db: Session,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
) -> TemplateResponse | None:
    template = workout_repository.get_template_for_user(db, template_id, user_id)
    if template is None:
        return None
    return _build_template_response(template)


def update_template(
    db: Session,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: UpdateTemplateRequest,
) -> TemplateResponse | None:
    template = workout_repository.get_template_for_user(db, template_id, user_id)
    if template is None or template.is_system:
        return None

    fields: dict[str, Any] = {}
    if payload.name is not None:
        fields["name"] = payload.name
    if payload.description is not None:
        fields["description"] = payload.description
    if fields:
        workout_repository.update_template_fields(db, template, **fields)

    if payload.exercises is not None:
        workout_repository.delete_template_exercises(db, template_id)
        for ex_in in payload.exercises:
            workout_repository.add_template_exercise(
                db,
                template_id=template_id,
                exercise_id=ex_in.exercise_id,
                order_index=ex_in.order_index,
                default_sets=ex_in.default_sets,
                default_reps=ex_in.default_reps,
                default_weight_kg=ex_in.default_weight_kg,
                default_duration_seconds=ex_in.default_duration_seconds,
                default_distance_meters=ex_in.default_distance_meters,
                notes=ex_in.notes,
            )

    db.commit()
    # Re-fetch with eager-loaded relationships so response has current data.
    refreshed = workout_repository.get_template_for_user(db, template_id, user_id)
    return _build_template_response(refreshed)  # type: ignore[arg-type]


def delete_template(
    db: Session, user_id: uuid.UUID, template_id: uuid.UUID
) -> bool:
    template = workout_repository.get_template_for_user(db, template_id, user_id)
    if template is None or template.is_system:
        return False
    workout_repository.delete_template(db, template)
    return True


# ── Workout session operations ────────────────────────────────────────────────


def start_workout(
    db: Session,
    user_id: uuid.UUID,
    payload: StartWorkoutRequest,
) -> WorkoutResponse:
    started_at = payload.started_at or _utc_now()
    name = payload.name or "Workout"

    # If a template is supplied, inherit its name and pre-populate exercises
    template: WorkoutTemplate | None = None
    if payload.template_id is not None:
        template = workout_repository.get_template_for_user(
            db, payload.template_id, user_id
        )
        if template is not None and not payload.name:
            name = template.name

    workout = workout_repository.create_workout(
        db,
        user_id=user_id,
        name=name,
        started_at=started_at,
        template_id=template.id if template else None,
        notes=payload.notes,
    )

    if template is not None:
        for te in template.template_exercises:
            workout_repository.add_workout_exercise(
                db,
                workout_id=workout.id,
                exercise_id=te.exercise_id,
                order_index=te.order_index,
                notes=None,
            )

    db.commit()
    # Re-fetch with all relationships eager-loaded
    workout = workout_repository.get_workout_for_user(db, workout.id, user_id)  # type: ignore[assignment]
    return _build_workout_response(workout)


def list_workouts(
    db: Session,
    user_id: uuid.UUID,
    *,
    completed_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> WorkoutListResponse:
    offset = (page - 1) * page_size
    workouts, total = workout_repository.list_workouts_for_user(
        db, user_id, completed_only=completed_only, offset=offset, limit=page_size
    )
    return WorkoutListResponse(
        workouts=[_build_workout_summary(w) for w in workouts],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_workout(
    db: Session, user_id: uuid.UUID, workout_id: uuid.UUID
) -> WorkoutResponse | None:
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    if workout is None:
        return None
    return _build_workout_response(workout)


def complete_workout(
    db: Session,
    user_id: uuid.UUID,
    workout_id: uuid.UUID,
    payload: CompleteWorkoutRequest,
) -> WorkoutResponse | None:
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    if workout is None:
        return None
    if workout.completed_at is not None:
        # Already completed — return as-is (idempotent)
        return _build_workout_response(workout)

    completed_at = payload.completed_at or _utc_now()

    # Gather all sets to compute volume
    all_sets: list[WorkoutSet] = []
    for we in workout.exercises:
        all_sets.extend(we.sets or [])

    volume = compute_volume_kg(all_sets)

    workout_repository.complete_workout(
        db, workout, completed_at=completed_at, total_volume_kg=volume, notes=payload.notes
    )
    db.commit()
    refreshed = workout_repository.get_workout_for_user(db, workout_id, user_id)
    return _build_workout_response(refreshed)  # type: ignore[arg-type]


def update_workout(
    db: Session,
    user_id: uuid.UUID,
    workout_id: uuid.UUID,
    payload: UpdateWorkoutRequest,
) -> WorkoutResponse | None:
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    if workout is None:
        return None
    fields: dict[str, Any] = {}
    if payload.name is not None:
        fields["name"] = payload.name
    if payload.notes is not None:
        fields["notes"] = payload.notes
    if fields:
        workout_repository.update_workout_fields(db, workout, **fields)
        db.commit()
        workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
        assert workout is not None  # just committed, must still exist
    return _build_workout_response(workout)


def delete_workout(
    db: Session, user_id: uuid.UUID, workout_id: uuid.UUID
) -> bool:
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    if workout is None:
        return False
    workout_repository.delete_workout(db, workout)
    return True


# ── Exercise within a workout ─────────────────────────────────────────────────


def add_exercise_to_workout(
    db: Session,
    user_id: uuid.UUID,
    workout_id: uuid.UUID,
    payload: AddExerciseRequest,
) -> WorkoutResponse | None:
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    if workout is None:
        return None
    workout_repository.add_workout_exercise(
        db,
        workout_id=workout_id,
        exercise_id=payload.exercise_id,
        order_index=payload.order_index,
        notes=payload.notes,
    )
    db.commit()
    workout = workout_repository.get_workout_for_user(db, workout_id, user_id)
    assert workout is not None  # just committed, must still exist
    return _build_workout_response(workout)


def remove_exercise_from_workout(
    db: Session,
    user_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
) -> bool:
    we = workout_repository.get_workout_exercise(db, workout_exercise_id, user_id)
    if we is None:
        return False
    workout_repository.delete_workout_exercise(db, we)
    db.commit()
    return True


# ── Set logging ───────────────────────────────────────────────────────────────


def log_set(
    db: Session,
    user_id: uuid.UUID,
    workout_exercise_id: uuid.UUID,
    payload: LogSetRequest,
) -> SetResponse | None:
    """Log a set and detect PRs.  Returns None if the workout_exercise doesn't
    belong to the user."""
    we = workout_repository.get_workout_exercise(db, workout_exercise_id, user_id)
    if we is None:
        return None

    exercise_id = we.exercise_id
    pr = False

    # Strength PR check
    if payload.weight_kg is not None and payload.reps is not None:
        pr = is_strength_pr(
            db, user_id, exercise_id, payload.weight_kg, payload.reps
        )
    # Duration PR check (only if not already a strength PR)
    elif payload.duration_seconds is not None:
        pr = is_duration_pr(db, user_id, exercise_id, payload.duration_seconds)
    # Distance PR check
    elif payload.distance_meters is not None:
        pr = is_distance_pr(db, user_id, exercise_id, payload.distance_meters)

    ws = workout_repository.log_set(
        db,
        workout_exercise_id=workout_exercise_id,
        set_number=payload.set_number,
        reps=payload.reps,
        weight_kg=payload.weight_kg,
        duration_seconds=payload.duration_seconds,
        distance_meters=payload.distance_meters,
        rpe=payload.rpe,
        completed_at=payload.completed_at or _utc_now(),
        is_pr=pr,
    )
    db.commit()
    refreshed_ws = workout_repository.get_set(db, ws.id, user_id)
    return _build_set_response(refreshed_ws)  # type: ignore[arg-type]


def update_set(
    db: Session,
    user_id: uuid.UUID,
    set_id: uuid.UUID,
    payload: UpdateSetRequest,
) -> SetResponse | None:
    ws = workout_repository.get_set(db, set_id, user_id)
    if ws is None:
        return None

    fields: dict[str, Any] = {}
    for attr in ("reps", "weight_kg", "duration_seconds", "distance_meters", "rpe", "completed_at"):
        val = getattr(payload, attr, None)
        if val is not None:
            fields[attr] = val
    if fields:
        workout_repository.update_set_fields(db, ws, **fields)
        db.commit()
        ws = workout_repository.get_set(db, set_id, user_id)
        assert ws is not None  # just committed, must still exist
    return _build_set_response(ws)


def delete_set(
    db: Session, user_id: uuid.UUID, set_id: uuid.UUID
) -> bool:
    ws = workout_repository.get_set(db, set_id, user_id)
    if ws is None:
        return False
    workout_repository.delete_set(db, ws)
    db.commit()
    return True
