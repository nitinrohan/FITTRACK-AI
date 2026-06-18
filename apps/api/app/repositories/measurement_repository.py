"""Repository functions for the body measurements domain.

All functions accept a SQLAlchemy Session and return ORM objects (or None).
No business logic lives here — that belongs in measurement_service.py.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.measurement import BodyMeasurement


def create_measurement(
    db: Session,
    *,
    user_id: uuid.UUID,
    measured_at: date,
    waist_cm: float | None = None,
    chest_cm: float | None = None,
    hips_cm: float | None = None,
    shoulders_cm: float | None = None,
    abdomen_cm: float | None = None,
    left_arm_cm: float | None = None,
    right_arm_cm: float | None = None,
    left_forearm_cm: float | None = None,
    right_forearm_cm: float | None = None,
    left_thigh_cm: float | None = None,
    right_thigh_cm: float | None = None,
    left_calf_cm: float | None = None,
    right_calf_cm: float | None = None,
    neck_cm: float | None = None,
    notes: str | None = None,
) -> BodyMeasurement:
    entry = BodyMeasurement(
        user_id=user_id,
        measured_at=measured_at,
        waist_cm=waist_cm,
        chest_cm=chest_cm,
        hips_cm=hips_cm,
        shoulders_cm=shoulders_cm,
        abdomen_cm=abdomen_cm,
        left_arm_cm=left_arm_cm,
        right_arm_cm=right_arm_cm,
        left_forearm_cm=left_forearm_cm,
        right_forearm_cm=right_forearm_cm,
        left_thigh_cm=left_thigh_cm,
        right_thigh_cm=right_thigh_cm,
        left_calf_cm=left_calf_cm,
        right_calf_cm=right_calf_cm,
        neck_cm=neck_cm,
        notes=notes,
    )
    db.add(entry)
    db.flush()
    return entry


def get_measurement_by_id(
    db: Session, entry_id: uuid.UUID, user_id: uuid.UUID
) -> BodyMeasurement | None:
    stmt = select(BodyMeasurement).where(
        BodyMeasurement.id == entry_id,
        BodyMeasurement.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_measurements(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[BodyMeasurement], int]:
    """Return paginated measurement entries for a user, newest first."""
    stmt = select(BodyMeasurement).where(BodyMeasurement.user_id == user_id)

    if date_from:
        stmt = stmt.where(BodyMeasurement.measured_at >= date_from)
    if date_to:
        stmt = stmt.where(BodyMeasurement.measured_at <= date_to)

    total_stmt = stmt.with_only_columns(BodyMeasurement.id).order_by(None)
    total = len(db.execute(total_stmt).all())

    offset = (page - 1) * page_size
    stmt = stmt.order_by(
        BodyMeasurement.measured_at.desc(),
        BodyMeasurement.created_at.desc(),
    ).offset(offset).limit(page_size)

    entries = list(db.scalars(stmt).all())
    return entries, total


def get_latest_measurement(
    db: Session, user_id: uuid.UUID
) -> BodyMeasurement | None:
    """Return the most-recent entry for a user, or None."""
    stmt = (
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(
            BodyMeasurement.measured_at.desc(),
            BodyMeasurement.created_at.desc(),
        )
        .limit(1)
    )
    return db.scalars(stmt).first()


def update_measurement_fields(
    db: Session, entry: BodyMeasurement, **fields: object
) -> BodyMeasurement:
    for key, val in fields.items():
        setattr(entry, key, val)
    db.flush()
    return entry


def delete_measurement(db: Session, entry: BodyMeasurement) -> None:
    db.delete(entry)
    db.flush()
