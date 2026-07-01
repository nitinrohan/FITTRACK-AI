"""Business logic for stress readings (0-100).

Pure, unit-tested domain calculations:
  - classify_band : map a 0-100 level to low / moderate / high.
  - summarise     : highest / lowest / average / band for a set of readings,
                    safe when the set is empty (returns None, not 0).

Timezone handling: the daily summary groups readings by the user's local
calendar day. The caller passes an IANA timezone; readings are stored in UTC
and converted to that zone to decide which day they fall in.

Stress here is self-reported and is explicitly not a medical assessment; the
API and UI present it supportively, never diagnostically.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.stress import StressLog
from app.schemas.stress import (
    LogStressRequest,
    StressBand,
    StressDailySummary,
    StressListResponse,
    StressLogResponse,
)

# Band thresholds (inclusive upper bounds). 0-33 low, 34-66 moderate, 67-100 high.
_LOW_MAX = 33
_MODERATE_MAX = 66


def classify_band(level: int) -> StressBand:
    """Map a 0-100 stress level to a coarse band."""
    if level <= _LOW_MAX:
        return "low"
    if level <= _MODERATE_MAX:
        return "moderate"
    return "high"


def summarise(levels: list[int], *, on_date: date) -> StressDailySummary:
    """Aggregate a day's readings. Empty -> all-None aggregates (not 0)."""
    if not levels:
        return StressDailySummary(
            date=on_date, count=0, highest=None, lowest=None, average=None, band=None
        )
    average = round(sum(levels) / len(levels))
    return StressDailySummary(
        date=on_date,
        count=len(levels),
        highest=max(levels),
        lowest=min(levels),
        average=average,
        band=classify_band(average),
    )


def _resolve_zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo("UTC")


def _day_bounds_utc(on_date: date, tz: str) -> tuple[datetime, datetime]:
    """Return [start, end) UTC-naive datetimes for the local day ``on_date``."""
    zone = _resolve_zone(tz)
    start_local = datetime.combine(on_date, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _response(entry: StressLog) -> StressLogResponse:
    return StressLogResponse(
        id=entry.id,
        user_id=entry.user_id,
        level=entry.level,
        band=classify_band(entry.level),
        recorded_at=entry.recorded_at,
        source=entry.source,
        note=entry.note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


# ── Operations ──────────────────────────────────────────────────────────────────


def log_reading(
    db: Session, user_id: uuid.UUID, payload: LogStressRequest
) -> StressLogResponse:
    recorded_at = payload.recorded_at or datetime.now(timezone.utc)
    if recorded_at.tzinfo is not None:
        recorded_at = recorded_at.astimezone(timezone.utc).replace(tzinfo=None)
    entry = StressLog(
        user_id=user_id,
        level=payload.level,
        recorded_at=recorded_at,
        source="manual",
        note=payload.note,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _response(entry)


def list_readings(
    db: Session,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> StressListResponse:
    base = select(StressLog).where(StressLog.user_id == user_id)
    total = len(db.execute(base).scalars().all())
    rows = (
        db.execute(
            base.order_by(StressLog.recorded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return StressListResponse(
        items=[_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def daily_summary(
    db: Session, user_id: uuid.UUID, *, on_date: date, tz: str = "UTC"
) -> StressDailySummary:
    start_utc, end_utc = _day_bounds_utc(on_date, tz)
    rows = (
        db.execute(
            select(StressLog.level).where(
                StressLog.user_id == user_id,
                StressLog.recorded_at >= start_utc,
                StressLog.recorded_at < end_utc,
            )
        )
        .scalars()
        .all()
    )
    return summarise(list(rows), on_date=on_date)


def delete_reading(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
    entry = db.execute(
        select(StressLog).where(
            StressLog.id == entry_id, StressLog.user_id == user_id
        )
    ).scalar_one_or_none()
    if entry is None:
        raise NotFoundError("Stress reading not found.")
    db.delete(entry)
    db.commit()
