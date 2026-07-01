"""Schemas for the progress endpoint - /api/v1/progress.

Returns time-series for the user's key metrics over a selectable range, plus
summary statistics that power the chart's accessible text alternative (a
data table / spoken summary), as required for WCAG-friendly charts.
"""

from __future__ import annotations

from pydantic import BaseModel


class ProgressPoint(BaseModel):
    date: str  # YYYY-MM-DD
    value: float


class MetricSeries(BaseModel):
    """One metric's series plus summary stats.

    Not every stat is meaningful for every metric - the frontend chooses which
    to show (e.g. `total` for workouts, `change` for weight). Computing them
    here keeps the maths in tested backend code, not in the chart component.
    """

    metric: str  # "weight" | "workouts" | "calories"
    label: str
    unit: str
    points: list[ProgressPoint]

    count: int  # number of data points
    total: float
    minimum: float | None
    maximum: float | None
    average: float | None
    first: float | None
    latest: float | None
    change: float | None  # latest - first


class ProgressResponse(BaseModel):
    """Progress series for the requested range. Sections are null when the
    user has no data for that metric in the window."""

    range_days: int
    start_date: str
    end_date: str
    weight: MetricSeries | None = None
    workouts: MetricSeries | None = None
    calories: MetricSeries | None = None
