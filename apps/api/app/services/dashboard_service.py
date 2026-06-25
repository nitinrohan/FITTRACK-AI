"""Dashboard service — aggregates data from multiple domains.

One function, one DB session, one response.  Each section degrades
gracefully to None when the user has no data.

Design notes:
- Weight trend: up to 30 most-recent weight entries, newest-first from the
  repository, then reversed for charting (chronological order).
- Workout frequency: completed workouts in the last 28 days, grouped by
  calendar date (UTC date of started_at).
- Today's nutrition: food-log totals for today using the existing
  nutrition_service.get_daily_nutrition helper.
- Goals: active goals only, their progress_pct pre-computed by goal_service.
- Latest measurement: most-recent BodyMeasurement row, key fields only.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories import (
    habit_repository,
    measurement_repository,
    weight_repository,
)
from app.schemas.dashboard import (
    DashboardSummary,
    GoalsSummarySection,
    GoalSummaryItem,
    HabitsTodaySection,
    HabitTodayItem,
    LatestMeasurementSection,
    TodayNutritionSection,
    WeightTrendPoint,
    WeightTrendSection,
    WorkoutFrequencyPoint,
    WorkoutFrequencySection,
)
from app.services import habit_service, nutrition_service

# ── Helpers ───────────────────────────────────────────────────────────────────


def _today_utc() -> date:
    return date.today()


# ── Per-section builders ──────────────────────────────────────────────────────


def _build_weight_trend(db: Session, user_id: uuid.UUID) -> WeightTrendSection | None:
    entries, _ = weight_repository.list_entries_for_user(db, user_id, offset=0, limit=30)
    if not entries:
        return None

    # entries are newest-first; reverse for the chart (oldest → newest)
    points = [
        WeightTrendPoint(
            date=e.measured_at.isoformat(),
            weight_kg=e.weight_kg,
        )
        for e in reversed(entries)
    ]

    latest_kg = entries[0].weight_kg
    oldest_kg = entries[-1].weight_kg
    change_kg = round(latest_kg - oldest_kg, 2) if len(entries) > 1 else None

    # 7-day moving average: mean of up to 7 most-recent entries
    recent = entries[:7]
    moving_avg = round(sum(e.weight_kg for e in recent) / len(recent), 2)

    return WeightTrendSection(
        points=points,
        latest_kg=latest_kg,
        moving_avg_7d_kg=moving_avg,
        change_kg=change_kg,
    )


def _build_workout_frequency(db: Session, user_id: uuid.UUID) -> WorkoutFrequencySection | None:
    today = _today_utc()
    cutoff = today - timedelta(days=27)  # 28-day window inclusive

    # Query completed workouts in the window directly (no pagination needed here)
    from sqlalchemy import select

    from app.models.workout import Workout  # local to avoid circular at module level

    stmt = (
        select(Workout)
        .where(
            Workout.user_id == user_id,
            Workout.completed_at.isnot(None),
            Workout.started_at >= cutoff.isoformat(),
        )
        .order_by(Workout.started_at.asc())
    )
    workouts = list(db.execute(stmt).scalars())

    # Group by calendar date (use date of started_at)
    counts: dict[date, int] = defaultdict(int)
    last_workout_date: date | None = None
    for w in workouts:
        d = w.started_at.date() if hasattr(w.started_at, "date") else w.started_at
        counts[d] += 1
        if last_workout_date is None or d > last_workout_date:
            last_workout_date = d

    # Build a point for every day in the window (zero-fill gaps)
    points: list[WorkoutFrequencyPoint] = []
    for i in range(28):
        day = cutoff + timedelta(days=i)
        points.append(WorkoutFrequencyPoint(date=day.isoformat(), count=counts.get(day, 0)))

    total = sum(counts.values())

    # Return None if user has never completed a workout
    if total == 0 and last_workout_date is None:
        return None

    return WorkoutFrequencySection(
        points=points,
        total_28d=total,
        last_workout_date=last_workout_date.isoformat() if last_workout_date else None,
    )


def _build_today_nutrition(db: Session, user_id: uuid.UUID) -> TodayNutritionSection | None:
    today = _today_utc()
    summary = nutrition_service.get_daily_nutrition(db, user_id, today)

    # Return None only when there's truly nothing logged
    food_log_count = sum(len(ms.entries) for ms in summary.meals)
    water_log_count = len(summary.water_logs)
    if food_log_count == 0 and water_log_count == 0:
        return None

    totals = summary.day_totals
    return TodayNutritionSection(
        calories_kcal=totals.calories,
        protein_g=totals.protein_g,
        carbs_g=totals.carbs_g,
        fat_g=totals.fat_g,
        water_ml=float(summary.water_total_ml),
    )


def _build_goals(db: Session, user_id: uuid.UUID) -> GoalsSummarySection | None:
    from app.services import goal_service

    goals_data = goal_service.list_goals(
        db,
        user_id=user_id,
        status="active",
        page=1,
        page_size=10,
    )
    goals_list = goals_data.goals
    if not goals_list:
        return None

    items = [
        GoalSummaryItem(
            id=str(g.id),
            title=g.title,
            goal_type=g.goal_type,
            progress_pct=g.progress_pct,
        )
        for g in goals_list
    ]

    valid_pcts = [g.progress_pct for g in goals_list if g.progress_pct is not None]
    avg_pct = round(sum(valid_pcts) / len(valid_pcts), 1) if valid_pcts else None

    return GoalsSummarySection(
        goals=items,
        count=len(items),
        avg_progress_pct=avg_pct,
    )


def _build_latest_measurement(db: Session, user_id: uuid.UUID) -> LatestMeasurementSection | None:
    entry = measurement_repository.get_latest_measurement(db, user_id)
    if entry is None:
        return None

    from app.services.measurement_service import _count_recorded

    return LatestMeasurementSection(
        date=entry.measured_at.isoformat(),
        recorded_count=_count_recorded(entry),
        waist_cm=entry.waist_cm,
        chest_cm=entry.chest_cm,
        hips_cm=entry.hips_cm,
        neck_cm=entry.neck_cm,
        left_arm_cm=entry.left_arm_cm,
        right_arm_cm=entry.right_arm_cm,
        left_thigh_cm=entry.left_thigh_cm,
        right_thigh_cm=entry.right_thigh_cm,
    )


def _build_habits_today(db: Session, user_id: uuid.UUID) -> HabitsTodaySection | None:
    habits, _total = habit_repository.list_habits(db, user_id, include_archived=False)
    if not habits:
        return None

    today = _today_utc()
    items: list[HabitTodayItem] = []
    completed_count = 0
    for habit in habits:
        completed_dates = {c.date for c in habit.completions}
        done = today in completed_dates
        if done:
            completed_count += 1
        items.append(
            HabitTodayItem(
                id=str(habit.id),
                name=habit.name,
                color=habit.color,
                target_days_per_week=habit.target_days_per_week,
                completed_today=done,
                current_streak=habit_service.compute_current_streak(completed_dates, today),
            )
        )

    return HabitsTodaySection(
        habits=items,
        total=len(items),
        completed_count=completed_count,
    )


# ── Public API ─────────────────────────────────────────────────────────────────


def get_dashboard_summary(db: Session, *, user_id: uuid.UUID) -> DashboardSummary:
    """Aggregate all dashboard data in a single call."""
    return DashboardSummary(
        weight_trend=_build_weight_trend(db, user_id),
        workout_frequency=_build_workout_frequency(db, user_id),
        today_nutrition=_build_today_nutrition(db, user_id),
        goals=_build_goals(db, user_id),
        latest_measurement=_build_latest_measurement(db, user_id),
        habits_today=_build_habits_today(db, user_id),
    )
