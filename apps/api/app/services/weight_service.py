"""Weight service - business logic for the weight-tracking domain.

Unit conversions:
  1 lb = 0.453592 kg  (exact value used throughout)

BMI formula:
  BMI = weight_kg / (height_m ** 2)
  Labelled as an estimate.  Requires height from UserProfile.
  Returns None when height is unavailable.

Moving average:
  7-day moving average is the mean of the N most-recent entries
  (up to 7).  Returns None when there are no entries.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.weight_entry import WeightEntry
from app.repositories import weight_repository
from app.schemas.weight import (
    LogWeightRequest,
    UpdateWeightEntryRequest,
    WeightEntryResponse,
    WeightListResponse,
    WeightListStats,
)

_LBS_TO_KG = 0.453592


# ── Calculations ──────────────────────────────────────────────────────────────


def compute_bmi(weight_kg: float, height_cm: float | None) -> float | None:
    """Return BMI rounded to 1 decimal, or None if height is unavailable.

    Formula: weight_kg / (height_m)²
    Result is labelled as an estimate in API responses.
    """
    if not height_cm or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m**2), 1)


def compute_moving_average(entries: list[WeightEntry]) -> float | None:
    """Return the mean weight_kg of the provided entries, or None if empty."""
    if not entries:
        return None
    total = sum(e.weight_kg for e in entries)
    return round(total / len(entries), 2)


def compute_stats(entries: list[WeightEntry], recent_7: list[WeightEntry]) -> WeightListStats:
    """Compute summary stats from a full entry list and the 7 most-recent."""
    if not entries:
        return WeightListStats(
            count=0,
            latest_kg=None,
            earliest_kg=None,
            change_kg=None,
            min_kg=None,
            max_kg=None,
            moving_avg_7d_kg=None,
        )

    # entries are ordered newest-first
    weights = [e.weight_kg for e in entries]
    latest_kg = weights[0]
    earliest_kg = weights[-1]
    return WeightListStats(
        count=len(entries),
        latest_kg=round(latest_kg, 2),
        earliest_kg=round(earliest_kg, 2),
        change_kg=round(latest_kg - earliest_kg, 2),
        min_kg=round(min(weights), 2),
        max_kg=round(max(weights), 2),
        moving_avg_7d_kg=compute_moving_average(recent_7),
    )


# ── Response builder ──────────────────────────────────────────────────────────


def _to_response(entry: WeightEntry, height_cm: float | None = None) -> WeightEntryResponse:
    resp = WeightEntryResponse.model_validate(entry)
    resp.weight_lbs = round(entry.weight_kg / _LBS_TO_KG, 1)
    resp.bmi = compute_bmi(entry.weight_kg, height_cm)
    return resp


# ── CRUD ──────────────────────────────────────────────────────────────────────


def log_weight(
    db: Session,
    user_id: uuid.UUID,
    body: LogWeightRequest,
    height_cm: float | None = None,
) -> WeightEntryResponse:
    weight_kg = body.weight * _LBS_TO_KG if body.display_unit == "lbs" else body.weight
    entry = weight_repository.create_entry(
        db,
        user_id=user_id,
        weight_kg=round(weight_kg, 4),
        display_unit=body.display_unit,
        body_fat_pct=body.body_fat_pct,
        muscle_mass_kg=body.muscle_mass_kg,
        measured_at=body.measured_at,
        notes=body.notes,
    )
    db.commit()
    db.refresh(entry)
    return _to_response(entry, height_cm)


def get_entry(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    height_cm: float | None = None,
) -> WeightEntryResponse:
    entry = weight_repository.get_entry_for_user(db, entry_id, user_id)
    if entry is None:
        raise NotFoundError("Weight entry not found")
    return _to_response(entry, height_cm)


def update_entry(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateWeightEntryRequest,
    height_cm: float | None = None,
) -> WeightEntryResponse:
    entry = weight_repository.get_entry_for_user(db, entry_id, user_id)
    if entry is None:
        raise NotFoundError("Weight entry not found")

    fields: dict[str, object] = {}
    raw = body.model_dump(exclude_none=True)

    # Convert weight if provided
    if "weight" in raw:
        unit = raw.get("display_unit", entry.display_unit)
        w = float(raw["weight"])
        fields["weight_kg"] = round(w * _LBS_TO_KG if unit == "lbs" else w, 4)
        del raw["weight"]

    fields.update(raw)
    entry = weight_repository.update_entry(db, entry, **fields)
    db.commit()
    db.refresh(entry)
    return _to_response(entry, height_cm)


def delete_entry(
    db: Session,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    entry = weight_repository.get_entry_for_user(db, entry_id, user_id)
    if entry is None:
        raise NotFoundError("Weight entry not found")
    weight_repository.delete_entry(db, entry)
    db.commit()


def list_entries(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 30,
    height_cm: float | None = None,
) -> WeightListResponse:
    offset = (page - 1) * page_size
    entries, total = weight_repository.list_entries_for_user(
        db,
        user_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=page_size,
    )
    recent_7 = weight_repository.get_recent_entries(db, user_id, limit=7)

    return WeightListResponse(
        entries=[_to_response(e, height_cm) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + len(entries)) < total,
        stats=compute_stats(entries, recent_7),
    )
