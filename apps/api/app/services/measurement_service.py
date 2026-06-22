"""Business logic for the body measurements domain.

Key responsibilities:
- Enforce that at least one measurement field is provided on create.
- Enforce ownership: users can only read/modify their own entries.
- Build response objects including the `recorded_count` convenience field.
- Provide the paginated list + latest-entry snapshot.

All functions follow the commit-then-re-fetch pattern used throughout
this codebase so the service layer remains testable with MagicMock sessions.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.measurement import BodyMeasurement
from app.repositories import measurement_repository
from app.schemas.measurement import (
    MEASUREMENT_FIELDS,
    CreateMeasurementRequest,
    MeasurementListResponse,
    MeasurementResponse,
    UpdateMeasurementRequest,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _count_recorded(entry: BodyMeasurement) -> int:
    """Count how many measurement fields are non-None."""
    return sum(1 for field in MEASUREMENT_FIELDS if getattr(entry, field) is not None)


def _build_response(entry: BodyMeasurement) -> MeasurementResponse:
    return MeasurementResponse(
        id=entry.id,
        user_id=entry.user_id,
        measured_at=entry.measured_at,
        notes=entry.notes,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        recorded_count=_count_recorded(entry),
        waist_cm=entry.waist_cm,
        chest_cm=entry.chest_cm,
        hips_cm=entry.hips_cm,
        shoulders_cm=entry.shoulders_cm,
        abdomen_cm=entry.abdomen_cm,
        left_arm_cm=entry.left_arm_cm,
        right_arm_cm=entry.right_arm_cm,
        left_forearm_cm=entry.left_forearm_cm,
        right_forearm_cm=entry.right_forearm_cm,
        left_thigh_cm=entry.left_thigh_cm,
        right_thigh_cm=entry.right_thigh_cm,
        left_calf_cm=entry.left_calf_cm,
        right_calf_cm=entry.right_calf_cm,
        neck_cm=entry.neck_cm,
    )


def _has_any_measurement(payload: CreateMeasurementRequest | UpdateMeasurementRequest) -> bool:
    return any(getattr(payload, f) is not None for f in MEASUREMENT_FIELDS)


# ── CRUD ──────────────────────────────────────────────────────────────────────


def log_measurement(
    db: Session, user_id: uuid.UUID, payload: CreateMeasurementRequest
) -> MeasurementResponse:
    """Create a new body measurement entry.

    Raises ValidationError if no measurement field is provided.
    """
    if not _has_any_measurement(payload):
        raise ValidationError("At least one measurement field must be provided.")

    entry = measurement_repository.create_measurement(
        db,
        user_id=user_id,
        measured_at=payload.measured_at,
        waist_cm=payload.waist_cm,
        chest_cm=payload.chest_cm,
        hips_cm=payload.hips_cm,
        shoulders_cm=payload.shoulders_cm,
        abdomen_cm=payload.abdomen_cm,
        left_arm_cm=payload.left_arm_cm,
        right_arm_cm=payload.right_arm_cm,
        left_forearm_cm=payload.left_forearm_cm,
        right_forearm_cm=payload.right_forearm_cm,
        left_thigh_cm=payload.left_thigh_cm,
        right_thigh_cm=payload.right_thigh_cm,
        left_calf_cm=payload.left_calf_cm,
        right_calf_cm=payload.right_calf_cm,
        neck_cm=payload.neck_cm,
        notes=payload.notes,
    )
    db.commit()
    refreshed = measurement_repository.get_measurement_by_id(db, entry.id, user_id)
    assert refreshed is not None
    return _build_response(refreshed)


def get_measurement(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> MeasurementResponse:
    entry = measurement_repository.get_measurement_by_id(db, entry_id, user_id)
    if entry is None:
        raise NotFoundError("Measurement entry not found.")
    return _build_response(entry)


def list_measurements(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
) -> MeasurementListResponse:
    entries, total = measurement_repository.list_measurements(
        db,
        user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    latest_entry = measurement_repository.get_latest_measurement(db, user_id)
    return MeasurementListResponse(
        entries=[_build_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        latest=_build_response(latest_entry) if latest_entry else None,
    )


def update_measurement(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateMeasurementRequest,
) -> MeasurementResponse:
    entry = measurement_repository.get_measurement_by_id(db, entry_id, user_id)
    if entry is None:
        raise NotFoundError("Measurement entry not found.")

    fields = payload.model_dump(exclude_unset=True)
    if fields:
        measurement_repository.update_measurement_fields(db, entry, **fields)
    db.commit()
    refreshed = measurement_repository.get_measurement_by_id(db, entry_id, user_id)
    assert refreshed is not None
    return _build_response(refreshed)


def delete_measurement(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    entry = measurement_repository.get_measurement_by_id(db, entry_id, user_id)
    if entry is None:
        return False
    measurement_repository.delete_measurement(db, entry)
    db.commit()
    return True
