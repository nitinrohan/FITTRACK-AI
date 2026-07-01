"""Progress service - builds time-series for charts over a selectable range.

Three metrics for the MVP:
  - weight   : one point per weight entry (kg), oldest -> newest
  - workouts : completed workouts per calendar day (zero-filled)
  - calories : total kcal logged per day that has food entries

All maths (totals, averages, change) lives here so the chart components stay
presentational, and so the figures can be unit-tested. Every query is scoped
by user_id. Calorie totals use a single FoodLog<->Food join, not one query
per day.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition import Food, FoodLog
from app.models.workout import Workout
from app.repositories import weight_repository
from app.schemas.progress import MetricSeries, ProgressPoint, ProgressResponse

# Clamp range to a sane window to bound query cost.
MIN_DAYS = 7
MAX_DAYS = 365
DEFAULT_DAYS = 30


def _today() -> date:
    return date.today()


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "total": 0.0,
            "minimum": None,
            "maximum": None,
            "average": None,
            "first": None,
            "latest": None,
            "change": None,
        }
    first = values[0]
    latest = values[-1]
    return {
        "total": round(sum(values), 2),
        "minimum": round(min(values), 2),
        "maximum": round(max(values), 2),
        "average": round(sum(values) / len(values), 2),
        "first": round(first, 2),
        "latest": round(latest, 2),
        "change": round(latest - first, 2),
    }


def _series(
    *, metric: str, label: str, unit: str, points: list[ProgressPoint]
) -> MetricSeries:
    stats = _stats([p.value for p in points])
    return MetricSeries(
        metric=metric,
        label=label,
        unit=unit,
        points=points,
        count=len(points),
        total=stats["total"] or 0.0,
        minimum=stats["minimum"],
        maximum=stats["maximum"],
        average=stats["average"],
        first=stats["first"],
        latest=stats["latest"],
        change=stats["change"],
    )


# ── Per-metric builders ──────────────────────────────────────────────────────


def _weight_series(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> MetricSeries | None:
    entries, _ = weight_repository.list_entries_for_user(
        db, user_id, date_from=start, date_to=end, offset=0, limit=MAX_DAYS
    )
    if not entries:
        return None
    # Repository returns newest-first; chart wants oldest -> newest.
    points = [
        ProgressPoint(date=e.measured_at.isoformat(), value=round(e.weight_kg, 2))
        for e in reversed(entries)
    ]
    return _series(metric="weight", label="Body weight", unit="kg", points=points)


def _workout_series(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> MetricSeries | None:
    stmt = (
        select(Workout)
        .where(
            Workout.user_id == user_id,
            Workout.completed_at.isnot(None),
            Workout.started_at >= start.isoformat(),
        )
        .order_by(Workout.started_at.asc())
    )
    workouts = list(db.execute(stmt).scalars())

    counts: dict[date, int] = defaultdict(int)
    for w in workouts:
        d = w.started_at.date() if hasattr(w.started_at, "date") else w.started_at
        if start <= d <= end:
            counts[d] += 1

    if not counts:
        return None

    days = (end - start).days + 1
    points = [
        ProgressPoint(
            date=(start + timedelta(days=i)).isoformat(),
            value=float(counts.get(start + timedelta(days=i), 0)),
        )
        for i in range(days)
    ]
    return _series(
        metric="workouts", label="Workouts", unit="per day", points=points
    )


def _calorie_series(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> MetricSeries | None:
    stmt = (
        select(FoodLog.logged_date, Food.calories_per_100g, FoodLog.quantity_g)
        .join(Food, Food.id == FoodLog.food_id)
        .where(
            FoodLog.user_id == user_id,
            FoodLog.logged_date >= start,
            FoodLog.logged_date <= end,
        )
    )
    rows = db.execute(stmt).all()
    if not rows:
        return None

    totals: dict[date, float] = defaultdict(float)
    for logged_date, cal_per_100g, qty_g in rows:
        totals[logged_date] += cal_per_100g * qty_g / 100.0

    # One point per logged day, chronological.
    points = [
        ProgressPoint(date=d.isoformat(), value=round(totals[d], 0))
        for d in sorted(totals)
    ]
    return _series(
        metric="calories", label="Calories", unit="kcal/day", points=points
    )


# ── Public API ────────────────────────────────────────────────────────────────


def get_progress(db: Session, *, user_id: uuid.UUID, days: int) -> ProgressResponse:
    days = max(MIN_DAYS, min(MAX_DAYS, days))
    end = _today()
    start = end - timedelta(days=days - 1)
    return ProgressResponse(
        range_days=days,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        weight=_weight_series(db, user_id, start, end),
        workouts=_workout_series(db, user_id, start, end),
        calories=_calorie_series(db, user_id, start, end),
    )
