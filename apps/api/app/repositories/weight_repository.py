"""Weight entry repository — all DB access for the weight-tracking domain.

All query functions accept user_id explicitly so the service layer never
needs to perform a cross-user lookup.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.weight_entry import WeightEntry

# ── Write ─────────────────────────────────────────────────────────────────────


def create_entry(
    db: Session,
    *,
    user_id: uuid.UUID,
    weight_kg: float,
    display_unit: str = "kg",
    body_fat_pct: float | None = None,
    muscle_mass_kg: float | None = None,
    measured_at: date,
    notes: str | None = None,
) -> WeightEntry:
    entry = WeightEntry(
        user_id=user_id,
        weight_kg=weight_kg,
        display_unit=display_unit,
        body_fat_pct=body_fat_pct,
        muscle_mass_kg=muscle_mass_kg,
        measured_at=measured_at,
        notes=notes,
    )
    db.add(entry)
    db.flush()
    return entry


def update_entry(db: Session, entry: WeightEntry, **fields: object) -> WeightEntry:
    """Apply a whitelist of fields to an existing entry."""
    allowed = {
        "weight_kg",
        "display_unit",
        "body_fat_pct",
        "muscle_mass_kg",
        "measured_at",
        "notes",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(entry, key, value)
    db.flush()
    return entry


def delete_entry(db: Session, entry: WeightEntry) -> None:
    db.delete(entry)
    db.flush()


# ── Read ──────────────────────────────────────────────────────────────────────


def get_entry_by_id(db: Session, entry_id: uuid.UUID) -> WeightEntry | None:
    return db.get(WeightEntry, entry_id)


def get_entry_for_user(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> WeightEntry | None:
    """Fetch a single entry, returning None if it doesn't belong to user_id."""
    stmt = select(WeightEntry).where(
        WeightEntry.id == entry_id,
        WeightEntry.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_entries_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 30,
) -> tuple[list[WeightEntry], int]:
    """Return (entries, total_count) ordered newest-first."""
    base = select(WeightEntry).where(WeightEntry.user_id == user_id)
    if date_from:
        base = base.where(WeightEntry.measured_at >= date_from)
    if date_to:
        base = base.where(WeightEntry.measured_at <= date_to)

    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    rows_stmt = (
        base.order_by(desc(WeightEntry.measured_at), desc(WeightEntry.created_at))
        .offset(offset)
        .limit(limit)
    )
    entries = list(db.execute(rows_stmt).scalars().all())
    return entries, total


def get_recent_entries(db: Session, user_id: uuid.UUID, *, limit: int = 7) -> list[WeightEntry]:
    """Fetch the N most-recent entries (used for moving average)."""
    stmt = (
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .order_by(desc(WeightEntry.measured_at), desc(WeightEntry.created_at))
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_latest_entry(db: Session, user_id: uuid.UUID) -> WeightEntry | None:
    stmt = (
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .order_by(desc(WeightEntry.measured_at), desc(WeightEntry.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
