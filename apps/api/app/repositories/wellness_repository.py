"""Repository functions for the wellness domain (sleep, steps, wellness check-in).

All functions accept a SQLAlchemy Session and return ORM objects.
No business logic lives here — that belongs in wellness_service.py.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.wellness import DailySteps, SleepLog, WellnessLog

# ── SleepLog ──────────────────────────────────────────────────────────────────


def create_sleep_log(db: Session, **kwargs: object) -> SleepLog:
    entry = SleepLog(**kwargs)
    db.add(entry)
    db.flush()
    return entry


def get_sleep_log_by_id(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> SleepLog | None:
    stmt = select(SleepLog).where(
        SleepLog.id == entry_id,
        SleepLog.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_sleep_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[SleepLog], int]:
    stmt = select(SleepLog).where(SleepLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(SleepLog.date >= date_from)
    if date_to:
        stmt = stmt.where(SleepLog.date <= date_to)

    total = len(db.execute(stmt.with_only_columns(SleepLog.id).order_by(None)).all())

    offset = (page - 1) * page_size
    entries = list(
        db.scalars(
            stmt.order_by(SleepLog.date.desc(), SleepLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return entries, total


def get_latest_sleep_for_date(db: Session, user_id: uuid.UUID, for_date: date) -> SleepLog | None:
    stmt = (
        select(SleepLog)
        .where(SleepLog.user_id == user_id, SleepLog.date == for_date)
        .order_by(SleepLog.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def update_sleep_log_fields(db: Session, entry: SleepLog, **fields: object) -> SleepLog:
    for key, val in fields.items():
        setattr(entry, key, val)
    db.flush()
    return entry


def delete_sleep_log(db: Session, entry: SleepLog) -> None:
    db.delete(entry)
    db.flush()


# ── DailySteps ────────────────────────────────────────────────────────────────


def create_steps_log(db: Session, **kwargs: object) -> DailySteps:
    entry = DailySteps(**kwargs)
    db.add(entry)
    db.flush()
    return entry


def get_steps_log_by_id(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> DailySteps | None:
    stmt = select(DailySteps).where(
        DailySteps.id == entry_id,
        DailySteps.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_steps_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[DailySteps], int]:
    stmt = select(DailySteps).where(DailySteps.user_id == user_id)
    if date_from:
        stmt = stmt.where(DailySteps.date >= date_from)
    if date_to:
        stmt = stmt.where(DailySteps.date <= date_to)

    total = len(db.execute(stmt.with_only_columns(DailySteps.id).order_by(None)).all())

    offset = (page - 1) * page_size
    entries = list(
        db.scalars(
            stmt.order_by(DailySteps.date.desc(), DailySteps.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return entries, total


def get_latest_steps_for_date(db: Session, user_id: uuid.UUID, for_date: date) -> DailySteps | None:
    stmt = (
        select(DailySteps)
        .where(DailySteps.user_id == user_id, DailySteps.date == for_date)
        .order_by(DailySteps.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def update_steps_log_fields(db: Session, entry: DailySteps, **fields: object) -> DailySteps:
    for key, val in fields.items():
        setattr(entry, key, val)
    db.flush()
    return entry


def delete_steps_log(db: Session, entry: DailySteps) -> None:
    db.delete(entry)
    db.flush()


# ── WellnessLog ───────────────────────────────────────────────────────────────


def create_wellness_log(db: Session, **kwargs: object) -> WellnessLog:
    entry = WellnessLog(**kwargs)
    db.add(entry)
    db.flush()
    return entry


def get_wellness_log_by_id(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> WellnessLog | None:
    stmt = select(WellnessLog).where(
        WellnessLog.id == entry_id,
        WellnessLog.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_wellness_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[WellnessLog], int]:
    stmt = select(WellnessLog).where(WellnessLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(WellnessLog.date >= date_from)
    if date_to:
        stmt = stmt.where(WellnessLog.date <= date_to)

    total = len(db.execute(stmt.with_only_columns(WellnessLog.id).order_by(None)).all())

    offset = (page - 1) * page_size
    entries = list(
        db.scalars(
            stmt.order_by(WellnessLog.date.desc(), WellnessLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ).all()
    )
    return entries, total


def get_latest_wellness_for_date(
    db: Session, user_id: uuid.UUID, for_date: date
) -> WellnessLog | None:
    stmt = (
        select(WellnessLog)
        .where(WellnessLog.user_id == user_id, WellnessLog.date == for_date)
        .order_by(WellnessLog.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def update_wellness_log_fields(db: Session, entry: WellnessLog, **fields: object) -> WellnessLog:
    for key, val in fields.items():
        setattr(entry, key, val)
    db.flush()
    return entry


def delete_wellness_log(db: Session, entry: WellnessLog) -> None:
    db.delete(entry)
    db.flush()
