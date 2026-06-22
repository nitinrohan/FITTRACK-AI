"""Dashboard summary schemas.

A single GET /api/v1/dashboard/summary endpoint returns all the data
the dashboard page needs in one round-trip.  Each section is optional
(null when the user has no data) so the frontend can display appropriate
empty states.
"""

from __future__ import annotations

from pydantic import BaseModel

# ── Weight trend ──────────────────────────────────────────────────────────────


class WeightTrendPoint(BaseModel):
    """One data point on the weight trend line."""

    date: str  # YYYY-MM-DD
    weight_kg: float


class WeightTrendSection(BaseModel):
    """30-day weight history for the trend chart."""

    points: list[WeightTrendPoint]
    latest_kg: float | None = None
    moving_avg_7d_kg: float | None = None
    change_kg: float | None = None  # latest - oldest in window


# ── Workout frequency ─────────────────────────────────────────────────────────


class WorkoutFrequencyPoint(BaseModel):
    """One bar in the workout-frequency chart."""

    date: str  # YYYY-MM-DD
    count: int


class WorkoutFrequencySection(BaseModel):
    """28-day workout frequency (completed workouts per day)."""

    points: list[WorkoutFrequencyPoint]
    total_28d: int
    last_workout_date: str | None = None


# ── Today's nutrition ─────────────────────────────────────────────────────────


class TodayNutritionSection(BaseModel):
    """Macro totals for today."""

    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    water_ml: float


# ── Active goals ──────────────────────────────────────────────────────────────


class GoalSummaryItem(BaseModel):
    """One active goal with its progress percentage."""

    id: str
    title: str
    goal_type: str
    progress_pct: float | None


class GoalsSummarySection(BaseModel):
    """Active goals for the progress-bar widget."""

    goals: list[GoalSummaryItem]
    count: int
    avg_progress_pct: float | None


# ── Latest measurements ───────────────────────────────────────────────────────


class LatestMeasurementSection(BaseModel):
    """Most-recent body measurement snapshot (values in cm)."""

    date: str
    recorded_count: int
    waist_cm: float | None = None
    chest_cm: float | None = None
    hips_cm: float | None = None
    neck_cm: float | None = None
    left_arm_cm: float | None = None
    right_arm_cm: float | None = None
    left_thigh_cm: float | None = None
    right_thigh_cm: float | None = None


# ── Top-level response ────────────────────────────────────────────────────────


class DashboardSummary(BaseModel):
    """Full dashboard summary for the /api/v1/dashboard/summary endpoint."""

    weight_trend: WeightTrendSection | None = None
    workout_frequency: WorkoutFrequencySection | None = None
    today_nutrition: TodayNutritionSection | None = None
    goals: GoalsSummarySection | None = None
    latest_measurement: LatestMeasurementSection | None = None
