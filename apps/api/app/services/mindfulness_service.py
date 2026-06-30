"""Business logic for the mindfulness domain - sessions and minute logs.

Pure, unit-tested domain calculation:
  - compute_streak : consecutive local days (ending today/yesterday) that have
                     at least one mindful-minute log. Forgiving of "today not
                     done yet", mirroring the habit streak rule.

Timezone handling matches the stress service: minute logs are stored in UTC and
grouped into the user's local calendar day for daily totals and the streak.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.mindfulness import MindfulnessLog, MindfulnessSession
from app.schemas.mindfulness import (
    CreateSessionRequest,
    LogMindfulnessRequest,
    MindfulnessDailySummary,
    MindfulnessLogListResponse,
    MindfulnessLogResponse,
    MindfulnessSessionListResponse,
    MindfulnessSessionResponse,
)

# ── Pure domain calculation ─────────────────────────────────────────────────────


def compute_streak(active_days: set[date], today: date) -> int:
    """Consecutive days with at least one mindful log, ending today or yesterday.

    Not having logged *today* does not zero the streak (the day is not over);
    it counts up to yesterday in that case.
    """
    if today in active_days:
        cursor = today
    elif (today - timedelta(days=1)) in active_days:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _resolve_zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo("UTC")


def _local_date(dt: datetime, zone: ZoneInfo) -> date:
    """Convert a UTC-naive datetime to a calendar date in ``zone``."""
    return dt.replace(tzinfo=timezone.utc).astimezone(zone).date()


def _day_bounds_utc(on_date: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    start_local = datetime.combine(on_date, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


# ── Sessions ────────────────────────────────────────────────────────────────────


def list_sessions(
    db: Session,
    user_id: uuid.UUID,
    *,
    category: str | None = None,
) -> MindfulnessSessionListResponse:
    """System sessions plus the caller's own custom sessions."""
    stmt = select(MindfulnessSession).where(
        MindfulnessSession.is_active.is_(True),
        or_(
            MindfulnessSession.is_system.is_(True),
            MindfulnessSession.user_id == user_id,
        ),
    )
    if category is not None:
        stmt = stmt.where(MindfulnessSession.category == category)
    rows = db.execute(stmt.order_by(MindfulnessSession.title)).scalars().all()
    return MindfulnessSessionListResponse(
        items=[MindfulnessSessionResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


def create_session(
    db: Session, user_id: uuid.UUID, payload: CreateSessionRequest
) -> MindfulnessSessionResponse:
    session = MindfulnessSession(
        user_id=user_id,
        title=payload.title,
        category=payload.category,
        duration_minutes=payload.duration_minutes,
        description=payload.description,
        external_url=payload.external_url,
        is_system=False,
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return MindfulnessSessionResponse.model_validate(session)


# ── Logs ────────────────────────────────────────────────────────────────────────


def _log_response(entry: MindfulnessLog) -> MindfulnessLogResponse:
    return MindfulnessLogResponse(
        id=entry.id,
        user_id=entry.user_id,
        session_id=entry.session_id,
        session_title=entry.session.title if entry.session is not None else None,
        duration_minutes=entry.duration_minutes,
        recorded_at=entry.recorded_at,
        note=entry.note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def log_minutes(
    db: Session, user_id: uuid.UUID, payload: LogMindfulnessRequest
) -> MindfulnessLogResponse:
    if payload.session_id is not None:
        session = db.execute(
            select(MindfulnessSession).where(
                MindfulnessSession.id == payload.session_id,
                MindfulnessSession.is_active.is_(True),
                or_(
                    MindfulnessSession.is_system.is_(True),
                    MindfulnessSession.user_id == user_id,
                ),
            )
        ).scalar_one_or_none()
        if session is None:
            raise ValidationError("Session not found or not available to you.")

    recorded_at = payload.recorded_at or datetime.now(timezone.utc)
    if recorded_at.tzinfo is not None:
        recorded_at = recorded_at.astimezone(timezone.utc).replace(tzinfo=None)

    entry = MindfulnessLog(
        user_id=user_id,
        session_id=payload.session_id,
        duration_minutes=payload.duration_minutes,
        recorded_at=recorded_at,
        note=payload.note,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _log_response(entry)


def list_logs(
    db: Session,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 50,
) -> MindfulnessLogListResponse:
    base = select(MindfulnessLog).where(MindfulnessLog.user_id == user_id)
    total = len(db.execute(base).scalars().all())
    rows = (
        db.execute(
            base.order_by(MindfulnessLog.recorded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return MindfulnessLogListResponse(
        items=[_log_response(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def daily_summary(
    db: Session, user_id: uuid.UUID, *, on_date: date, tz: str = "UTC"
) -> MindfulnessDailySummary:
    zone = _resolve_zone(tz)
    start_utc, end_utc = _day_bounds_utc(on_date, zone)

    today_rows = db.execute(
        select(MindfulnessLog.duration_minutes).where(
            MindfulnessLog.user_id == user_id,
            MindfulnessLog.recorded_at >= start_utc,
            MindfulnessLog.recorded_at < end_utc,
        )
    ).scalars().all()

    # Streak needs the full set of active local days.
    all_times = db.execute(
        select(MindfulnessLog.recorded_at).where(MindfulnessLog.user_id == user_id)
    ).scalars().all()
    active_days = {_local_date(dt, zone) for dt in all_times}

    return MindfulnessDailySummary(
        date=on_date,
        total_minutes=sum(today_rows),
        sessions_count=len(today_rows),
        current_streak=compute_streak(active_days, on_date),
    )


def delete_log(db: Session, entry_id: uuid.UUID, user_id: uuid.UUID) -> None:
    entry = db.execute(
        select(MindfulnessLog).where(
            MindfulnessLog.id == entry_id, MindfulnessLog.user_id == user_id
        )
    ).scalar_one_or_none()
    if entry is None:
        raise NotFoundError("Mindfulness log not found.")
    db.delete(entry)
    db.commit()
