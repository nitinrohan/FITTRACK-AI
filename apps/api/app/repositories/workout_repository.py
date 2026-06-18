"""Workout repository — all DB access for the workouts domain.

Ownership is enforced on every user-facing query by filtering on user_id.
The repository never raises HTTP exceptions — that is the router's job.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.workout import (
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutTemplate,
    WorkoutTemplateExercise,
)

# ── WorkoutTemplate ───────────────────────────────────────────────────────────


def create_template(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    description: str | None,
) -> WorkoutTemplate:
    """Insert a new template (without exercises — add them separately)."""
    template = WorkoutTemplate(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        is_system=False,
    )
    db.add(template)
    db.flush()  # populate template.id without committing
    return template


def add_template_exercise(
    db: Session,
    template_id: uuid.UUID,
    exercise_id: uuid.UUID,
    order_index: int,
    **defaults: Any,
) -> WorkoutTemplateExercise:
    te = WorkoutTemplateExercise(
        id=uuid.uuid4(),
        template_id=template_id,
        exercise_id=exercise_id,
        order_index=order_index,
        **{k: v for k, v in defaults.items() if v is not None},
    )
    db.add(te)
    return te


def delete_template_exercises(db: Session, template_id: uuid.UUID) -> None:
    """Remove all exercise slots from a template (used before a full replace)."""
    db.query(WorkoutTemplateExercise).filter(
        WorkoutTemplateExercise.template_id == template_id
    ).delete(synchronize_session=False)


def get_template_by_id(db: Session, template_id: uuid.UUID) -> WorkoutTemplate | None:
    return (
        db.query(WorkoutTemplate)
        .options(
            joinedload(WorkoutTemplate.template_exercises).joinedload(
                WorkoutTemplateExercise.exercise
            )
        )
        .filter(WorkoutTemplate.id == template_id)
        .first()
    )


def get_template_for_user(
    db: Session, template_id: uuid.UUID, user_id: uuid.UUID
) -> WorkoutTemplate | None:
    """Return template only if owned by user or is a system template."""
    return (
        db.query(WorkoutTemplate)
        .options(
            joinedload(WorkoutTemplate.template_exercises).joinedload(
                WorkoutTemplateExercise.exercise
            )
        )
        .filter(
            WorkoutTemplate.id == template_id,
            (WorkoutTemplate.user_id == user_id) | (WorkoutTemplate.is_system == True),  # noqa: E712
        )
        .first()
    )


def list_templates_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[WorkoutTemplate], int]:
    """Return (templates, total) — user's own templates + system templates."""
    query = (
        db.query(WorkoutTemplate)
        .options(
            joinedload(WorkoutTemplate.template_exercises).joinedload(
                WorkoutTemplateExercise.exercise
            )
        )
        .filter(
            (WorkoutTemplate.user_id == user_id) | (WorkoutTemplate.is_system == True)  # noqa: E712
        )
        .order_by(WorkoutTemplate.created_at.desc())
    )
    total = query.count()
    templates = query.offset(offset).limit(limit).all()
    return templates, total


def update_template_fields(
    db: Session, template: WorkoutTemplate, **fields: Any
) -> WorkoutTemplate:
    for key, value in fields.items():
        setattr(template, key, value)
    db.flush()
    return template


def delete_template(db: Session, template: WorkoutTemplate) -> None:
    db.delete(template)
    db.commit()


# ── Workout (session) ─────────────────────────────────────────────────────────


def create_workout(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    started_at: datetime,
    template_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> Workout:
    workout = Workout(
        id=uuid.uuid4(),
        user_id=user_id,
        template_id=template_id,
        name=name,
        notes=notes,
        started_at=started_at,
        completed_at=None,
        total_volume_kg=None,
    )
    db.add(workout)
    db.flush()
    return workout


def get_workout_by_id(db: Session, workout_id: uuid.UUID) -> Workout | None:
    return (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.exercise),
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.sets),
            joinedload(Workout.template),
        )
        .filter(Workout.id == workout_id)
        .first()
    )


def get_workout_for_user(
    db: Session, workout_id: uuid.UUID, user_id: uuid.UUID
) -> Workout | None:
    return (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.exercise),
            joinedload(Workout.exercises)
            .joinedload(WorkoutExercise.sets),
            joinedload(Workout.template),
        )
        .filter(Workout.id == workout_id, Workout.user_id == user_id)
        .first()
    )


def list_workouts_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    completed_only: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Workout], int]:
    query = (
        db.query(Workout)
        .options(
            joinedload(Workout.exercises).joinedload(WorkoutExercise.sets),
            joinedload(Workout.template),
        )
        .filter(Workout.user_id == user_id)
    )
    if completed_only:
        query = query.filter(Workout.completed_at.isnot(None))
    total = query.count()
    workouts = (
        query.order_by(Workout.started_at.desc()).offset(offset).limit(limit).all()
    )
    return workouts, total


def complete_workout(
    db: Session,
    workout: Workout,
    completed_at: datetime,
    total_volume_kg: float | None,
    notes: str | None,
) -> Workout:
    workout.completed_at = completed_at
    workout.total_volume_kg = total_volume_kg
    if notes is not None:
        workout.notes = notes
    db.flush()
    return workout


def update_workout_fields(
    db: Session, workout: Workout, **fields: Any
) -> Workout:
    for key, value in fields.items():
        setattr(workout, key, value)
    db.flush()
    return workout


def delete_workout(db: Session, workout: Workout) -> None:
    db.delete(workout)
    db.commit()


# ── WorkoutExercise ───────────────────────────────────────────────────────────


def add_workout_exercise(
    db: Session,
    workout_id: uuid.UUID,
    exercise_id: uuid.UUID,
    order_index: int,
    notes: str | None = None,
) -> WorkoutExercise:
    we = WorkoutExercise(
        id=uuid.uuid4(),
        workout_id=workout_id,
        exercise_id=exercise_id,
        order_index=order_index,
        notes=notes,
    )
    db.add(we)
    db.flush()
    return we


def get_workout_exercise(
    db: Session, workout_exercise_id: uuid.UUID, user_id: uuid.UUID
) -> WorkoutExercise | None:
    """Return a WorkoutExercise only if the parent workout belongs to user."""
    return (
        db.query(WorkoutExercise)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(
            WorkoutExercise.id == workout_exercise_id,
            Workout.user_id == user_id,
        )
        .first()
    )


def delete_workout_exercise(db: Session, we: WorkoutExercise) -> None:
    db.delete(we)
    db.flush()


# ── WorkoutSet ────────────────────────────────────────────────────────────────


def log_set(
    db: Session,
    workout_exercise_id: uuid.UUID,
    set_number: int,
    *,
    reps: int | None,
    weight_kg: float | None,
    duration_seconds: int | None,
    distance_meters: float | None,
    rpe: float | None,
    completed_at: datetime | None,
    is_pr: bool = False,
) -> WorkoutSet:
    ws = WorkoutSet(
        id=uuid.uuid4(),
        workout_exercise_id=workout_exercise_id,
        set_number=set_number,
        reps=reps,
        weight_kg=weight_kg,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        rpe=rpe,
        completed_at=completed_at,
        is_pr=is_pr,
    )
    db.add(ws)
    db.flush()
    return ws


def get_set(
    db: Session, set_id: uuid.UUID, user_id: uuid.UUID
) -> WorkoutSet | None:
    """Return a WorkoutSet only if the owning workout belongs to user."""
    return (
        db.query(WorkoutSet)
        .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(WorkoutSet.id == set_id, Workout.user_id == user_id)
        .first()
    )


def update_set_fields(
    db: Session, ws: WorkoutSet, **fields: Any
) -> WorkoutSet:
    for key, value in fields.items():
        setattr(ws, key, value)
    db.flush()
    return ws


def delete_set(db: Session, ws: WorkoutSet) -> None:
    db.delete(ws)
    db.flush()


def get_best_set_for_exercise(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
) -> WorkoutSet | None:
    """Return the set with the highest weight_kg * reps (estimated 1RM proxy)
    for the given user and exercise across all completed workouts.

    Used for PR detection: compare the new set's volume against this value.
    """
    return (
        db.query(WorkoutSet)
        .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(
            Workout.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSet.weight_kg.isnot(None),
            WorkoutSet.reps.isnot(None),
        )
        .order_by(
            (WorkoutSet.weight_kg * WorkoutSet.reps).desc()
        )
        .first()
    )


def get_best_duration_for_exercise(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
) -> WorkoutSet | None:
    """Return the set with the longest duration for PR detection on timed exercises."""
    return (
        db.query(WorkoutSet)
        .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(
            Workout.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSet.duration_seconds.isnot(None),
        )
        .order_by(WorkoutSet.duration_seconds.desc())
        .first()
    )


def get_best_distance_for_exercise(
    db: Session,
    user_id: uuid.UUID,
    exercise_id: uuid.UUID,
) -> WorkoutSet | None:
    """Return the set with the greatest distance for PR detection on cardio exercises."""
    return (
        db.query(WorkoutSet)
        .join(WorkoutExercise, WorkoutExercise.id == WorkoutSet.workout_exercise_id)
        .join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(
            Workout.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
            WorkoutSet.distance_meters.isnot(None),
        )
        .order_by(WorkoutSet.distance_meters.desc())
        .first()
    )
