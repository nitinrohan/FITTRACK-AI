"""Business logic for the wellness domain — sleep, steps, wellness check-in.

Key responsibilities:
- Compute duration_minutes from bedtime/wake_time when not supplied directly.
- Enforce ownership: users can only read/modify their own entries.
- Build response objects for each domain.
- Assemble the daily wellness snapshot (sleep + steps + wellness + water total).

All functions follow the commit-then-re-fetch pattern used throughout the
codebase so the service layer remains testable with MagicMock sessions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.wellness import DailySteps, SleepLog, WellnessLog
from app.repositories import nutrition_repository, wellness_repository
from app.schemas.wellness import (
    DailyWellnessSnapshot,
    LogSleepRequest,
    LogStepsRequest,
    LogWellnessRequest,
    SleepListResponse,
    SleepLogResponse,
    StepsListResponse,
    StepsLogResponse,
    UpdateSleepRequest,
    UpdateStepsRequest,
    UpdateWellnessRequest,
    WellnessListResponse,
    WellnessLogResponse,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_duration(bedtime: datetime, wake_time: datetime) -> int:
    """Return sleep duration in whole minutes (always positive)."""
    delta = wake_time - bedtime
    return max(0, int(delta.total_seconds() / 60))


def _sleep_response(entry: SleepLog) -> SleepLogResponse:
    return SleepLogResponse.model_validate(entry)


def _steps_response(entry: DailySteps) -> StepsLogResponse:
    return StepsLogResponse.model_validate(entry)


def _wellness_response(entry: WellnessLog) -> WellnessLogResponse:
    return WellnessLogResponse.model_validate(entry)


# ── Sleep ─────────────────────────────────────────────────────────────────────


def log_sleep(
    db: Session, user_id: uuid.UUID, payload: LogSleepRequest
) -> SleepLogResponse:
    duration = payload.duration_minutes
    if duration is None and payload.bedtime and payload.wake_time:
        duration = _compute_duration(payload.bedtime, payload.wake_time)

    entry = wellness_repository.create_sleep_log(
        db,
        user_id=user_id,
        date=payload.date,
        bedtime=payload.bedtime,
        wake_time=payload.wake_time,
        duration_minutes=duration,
        quality=payload.quality,
        notes=payload.notes,
    )
    db.commit()
    fetched = wellness_repository.get_sleep_log_by_id(db, entry.id, user_id)
    assert fetched is not None
    return _sleep_response(fetched)


def list_sleep_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> SleepListResponse:
    entries, total = wellness_repository.list_sleep_logs(
        db, user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )
    return SleepListResponse(
        items=[_sleep_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_sleep_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> SleepLogResponse:
    entry = wellness_repository.get_sleep_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Sleep log entry not found.")
    return _sleep_response(entry)


def update_sleep_log(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateSleepRequest,
) -> SleepLogResponse:
    entry = wellness_repository.get_sleep_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Sleep log entry not found.")

    updates = payload.model_dump(exclude_unset=True)

    # Recompute duration if times change.
    bedtime = updates.get("bedtime", entry.bedtime)
    wake_time = updates.get("wake_time", entry.wake_time)
    if bedtime and wake_time and "duration_minutes" not in updates:
        updates["duration_minutes"] = _compute_duration(bedtime, wake_time)

    wellness_repository.update_sleep_log_fields(db, entry, **updates)
    db.commit()
    fetched = wellness_repository.get_sleep_log_by_id(db, entry_id, user_id)
    assert fetched is not None
    return _sleep_response(fetched)


def delete_sleep_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    entry = wellness_repository.get_sleep_log_by_id(db, entry_id, user_id)
    if not entry:
        return False
    wellness_repository.delete_sleep_log(db, entry)
    db.commit()
    return True


# ── Steps ─────────────────────────────────────────────────────────────────────


def log_steps(
    db: Session, user_id: uuid.UUID, payload: LogStepsRequest
) -> StepsLogResponse:
    entry = wellness_repository.create_steps_log(
        db,
        user_id=user_id,
        date=payload.date,
        steps=payload.steps,
        active_minutes=payload.active_minutes,
        distance_m=payload.distance_m,
        calories_burned=payload.calories_burned,
        notes=payload.notes,
    )
    db.commit()
    fetched = wellness_repository.get_steps_log_by_id(db, entry.id, user_id)
    assert fetched is not None
    return _steps_response(fetched)


def list_steps_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> StepsListResponse:
    entries, total = wellness_repository.list_steps_logs(
        db, user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )
    return StepsListResponse(
        items=[_steps_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_steps_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> StepsLogResponse:
    entry = wellness_repository.get_steps_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Steps log entry not found.")
    return _steps_response(entry)


def update_steps_log(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateStepsRequest,
) -> StepsLogResponse:
    entry = wellness_repository.get_steps_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Steps log entry not found.")
    wellness_repository.update_steps_log_fields(
        db, entry, **payload.model_dump(exclude_unset=True)
    )
    db.commit()
    fetched = wellness_repository.get_steps_log_by_id(db, entry_id, user_id)
    assert fetched is not None
    return _steps_response(fetched)


def delete_steps_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    entry = wellness_repository.get_steps_log_by_id(db, entry_id, user_id)
    if not entry:
        return False
    wellness_repository.delete_steps_log(db, entry)
    db.commit()
    return True


# ── Wellness check-in ─────────────────────────────────────────────────────────


def log_wellness(
    db: Session, user_id: uuid.UUID, payload: LogWellnessRequest
) -> WellnessLogResponse:
    entry = wellness_repository.create_wellness_log(
        db,
        user_id=user_id,
        date=payload.date,
        mood=payload.mood,
        energy=payload.energy,
        stress=payload.stress,
        notes=payload.notes,
    )
    db.commit()
    fetched = wellness_repository.get_wellness_log_by_id(db, entry.id, user_id)
    assert fetched is not None
    return _wellness_response(fetched)


def list_wellness_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> WellnessListResponse:
    entries, total = wellness_repository.list_wellness_logs(
        db, user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )
    return WellnessListResponse(
        items=[_wellness_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_wellness_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> WellnessLogResponse:
    entry = wellness_repository.get_wellness_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Wellness log entry not found.")
    return _wellness_response(entry)


def update_wellness_log(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateWellnessRequest,
) -> WellnessLogResponse:
    entry = wellness_repository.get_wellness_log_by_id(db, entry_id, user_id)
    if not entry:
        raise NotFoundError("Wellness log entry not found.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationError("No fields provided to update.")

    wellness_repository.update_wellness_log_fields(db, entry, **updates)
    db.commit()
    fetched = wellness_repository.get_wellness_log_by_id(db, entry_id, user_id)
    assert fetched is not None
    return _wellness_response(fetched)


def delete_wellness_log(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    entry = wellness_repository.get_wellness_log_by_id(db, entry_id, user_id)
    if not entry:
        return False
    wellness_repository.delete_wellness_log(db, entry)
    db.commit()
    return True


# ── Daily snapshot ────────────────────────────────────────────────────────────


def get_daily_snapshot(
    db: Session, user_id: uuid.UUID, for_date: date
) -> DailyWellnessSnapshot:
    """Assemble a combined daily snapshot for the given date.

    Pulls:
      - latest sleep log for the date (SleepLog)
      - latest steps log for the date (DailySteps)
      - latest wellness check-in for the date (WellnessLog)
      - sum of all water logs for the date (WaterLog from nutrition domain)
    """
    sleep_entry = wellness_repository.get_latest_sleep_for_date(db, user_id, for_date)
    steps_entry = wellness_repository.get_latest_steps_for_date(db, user_id, for_date)
    wellness_entry = wellness_repository.get_latest_wellness_for_date(db, user_id, for_date)

    water_logs = nutrition_repository.list_water_logs_for_date(db, user_id, for_date)
    water_total_ml = sum(w.amount_ml for w in water_logs)

    return DailyWellnessSnapshot(
        date=for_date,
        sleep=_sleep_response(sleep_entry) if sleep_entry else None,
        steps=_steps_response(steps_entry) if steps_entry else None,
        wellness=_wellness_response(wellness_entry) if wellness_entry else None,
        water_total_ml=water_total_ml,
    )
