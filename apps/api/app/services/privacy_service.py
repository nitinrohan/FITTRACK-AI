"""Privacy service - personal data export and account deletion.

This service powers Phase 14 (privacy, export, account deletion). Two
capabilities live here:

1. build_export(): assemble a complete, machine-readable snapshot of every
   record a single user owns, across all domains. Used by the data-export
   endpoint so users can take their data with them.

2. delete_account(): permanently remove a user and all data they own after
   verifying their password.

Design notes:
- Serialization is generic: each ORM row is converted via SQLAlchemy column
  introspection, so new columns are picked up automatically without touching
  this file. UUID/date/datetime values are converted to ISO strings.
- The export never includes the password hash or any other account secret.
- Deletion is an immediate hard delete. We rely on the ORM relationship
  cascades (configured on User) to remove children in FK-dependency order,
  which satisfies the RESTRICT foreign keys between food_logs/foods and
  workout_exercises/exercises. ai_usage_logs has no ORM relationship on User,
  so it is purged explicitly first (its DB-level ON DELETE CASCADE would also
  handle it, but the explicit delete keeps behaviour identical under SQLite
  test databases that do not enforce foreign keys).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.exceptions import UnauthorizedError
from app.models.ai_log import AIUsageLog
from app.models.exercise import Exercise
from app.models.goal import Goal
from app.models.habit import Habit, HabitCompletion
from app.models.measurement import BodyMeasurement
from app.models.nutrition import Food, FoodLog, WaterLog
from app.models.user import User
from app.models.weight_entry import WeightEntry
from app.models.wellness import DailySteps, SleepLog, WellnessLog
from app.models.workout import (
    Workout,
    WorkoutExercise,
    WorkoutSet,
    WorkoutTemplate,
    WorkoutTemplateExercise,
)

# Bump when the export shape changes in a backward-incompatible way.
EXPORT_FORMAT_VERSION = "1.0"

# Columns that must never leave the backend, even in a user's own export.
_REDACTED_COLUMNS = frozenset({"hashed_password"})


def _serialize(obj: Any) -> dict[str, Any]:
    """Convert a single ORM row to a JSON-safe dict via column introspection."""
    result: dict[str, Any] = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        key = attr.key
        if key in _REDACTED_COLUMNS:
            continue
        value = getattr(obj, key)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime | date):
            value = value.isoformat()
        result[key] = value
    return result


def _serialize_many(rows: Any) -> list[dict[str, Any]]:
    return [_serialize(row) for row in rows]


def build_export(db: Session, *, user: User) -> dict[str, Any]:
    """Return a complete snapshot of every record owned by ``user``.

    The returned structure is plain JSON-serializable Python and groups records
    by domain. Workouts, templates and habits nest their child rows so the
    relationships are preserved in the export.
    """
    uid = user.id

    # Custom (user-owned) exercises and foods only. System library rows
    # (user_id IS NULL) are shared content, not personal data.
    custom_exercises = db.query(Exercise).filter(Exercise.user_id == uid).all()

    templates = db.query(WorkoutTemplate).filter(WorkoutTemplate.user_id == uid).all()
    template_rows = []
    for tpl in templates:
        tpl_exercises = (
            db.query(WorkoutTemplateExercise)
            .filter(WorkoutTemplateExercise.template_id == tpl.id)
            .all()
        )
        template_rows.append(
            {**_serialize(tpl), "exercises": _serialize_many(tpl_exercises)}
        )

    workouts = db.query(Workout).filter(Workout.user_id == uid).all()
    workout_rows = []
    for wkt in workouts:
        w_exercises = (
            db.query(WorkoutExercise)
            .filter(WorkoutExercise.workout_id == wkt.id)
            .all()
        )
        exercise_rows = []
        for we in w_exercises:
            sets = (
                db.query(WorkoutSet)
                .filter(WorkoutSet.workout_exercise_id == we.id)
                .all()
            )
            exercise_rows.append({**_serialize(we), "sets": _serialize_many(sets)})
        workout_rows.append({**_serialize(wkt), "exercises": exercise_rows})

    habits = db.query(Habit).filter(Habit.user_id == uid).all()
    habit_rows = []
    for habit in habits:
        completions = (
            db.query(HabitCompletion)
            .filter(HabitCompletion.habit_id == habit.id)
            .all()
        )
        habit_rows.append(
            {**_serialize(habit), "completions": _serialize_many(completions)}
        )

    return {
        "export_metadata": {
            "format_version": EXPORT_FORMAT_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "user_id": str(uid),
            "email": user.email,
        },
        "account": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        },
        "profile": _serialize(user.profile) if user.profile else None,
        "preferences": _serialize(user.preferences) if user.preferences else None,
        "goals": _serialize_many(db.query(Goal).filter(Goal.user_id == uid).all()),
        "weight_entries": _serialize_many(
            db.query(WeightEntry).filter(WeightEntry.user_id == uid).all()
        ),
        "body_measurements": _serialize_many(
            db.query(BodyMeasurement).filter(BodyMeasurement.user_id == uid).all()
        ),
        "custom_exercises": _serialize_many(custom_exercises),
        "workout_templates": template_rows,
        "workouts": workout_rows,
        "custom_foods": _serialize_many(
            db.query(Food).filter(Food.user_id == uid).all()
        ),
        "food_logs": _serialize_many(
            db.query(FoodLog).filter(FoodLog.user_id == uid).all()
        ),
        "water_logs": _serialize_many(
            db.query(WaterLog).filter(WaterLog.user_id == uid).all()
        ),
        "sleep_logs": _serialize_many(
            db.query(SleepLog).filter(SleepLog.user_id == uid).all()
        ),
        "daily_steps": _serialize_many(
            db.query(DailySteps).filter(DailySteps.user_id == uid).all()
        ),
        "wellness_logs": _serialize_many(
            db.query(WellnessLog).filter(WellnessLog.user_id == uid).all()
        ),
        "habits": habit_rows,
        "ai_usage_logs": _serialize_many(
            db.query(AIUsageLog).filter(AIUsageLog.user_id == uid).all()
        ),
    }


def build_summary(db: Session, *, user: User) -> dict[str, int]:
    """Return a per-category count of the records the user owns.

    Used by the privacy page so the user sees exactly what an export or a
    deletion would cover before they act.
    """
    uid = user.id
    return {
        "goals": db.query(Goal).filter(Goal.user_id == uid).count(),
        "weight_entries": db.query(WeightEntry).filter(WeightEntry.user_id == uid).count(),
        "body_measurements": db.query(BodyMeasurement)
        .filter(BodyMeasurement.user_id == uid)
        .count(),
        "custom_exercises": db.query(Exercise).filter(Exercise.user_id == uid).count(),
        "workout_templates": db.query(WorkoutTemplate)
        .filter(WorkoutTemplate.user_id == uid)
        .count(),
        "workouts": db.query(Workout).filter(Workout.user_id == uid).count(),
        "custom_foods": db.query(Food).filter(Food.user_id == uid).count(),
        "food_logs": db.query(FoodLog).filter(FoodLog.user_id == uid).count(),
        "water_logs": db.query(WaterLog).filter(WaterLog.user_id == uid).count(),
        "sleep_logs": db.query(SleepLog).filter(SleepLog.user_id == uid).count(),
        "daily_steps": db.query(DailySteps).filter(DailySteps.user_id == uid).count(),
        "wellness_logs": db.query(WellnessLog).filter(WellnessLog.user_id == uid).count(),
        "habits": db.query(Habit).filter(Habit.user_id == uid).count(),
    }


def delete_account(db: Session, *, user: User, password: str) -> None:
    """Permanently delete the user and everything they own.

    The caller must supply the account password; it is verified here so a
    stolen session cookie alone cannot destroy an account. Raises
    UnauthorizedError on a password mismatch.

    This is irreversible. ORM relationship cascades remove owned child rows in
    FK-dependency order; ai_usage_logs is purged explicitly first.
    """
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Password is incorrect.")

    db.query(AIUsageLog).filter(AIUsageLog.user_id == user.id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
