"""Tests for the dashboard's habits-today section (Phase 12 integration)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.services.dashboard_service import _build_habits_today

TODAY = date(2026, 6, 24)


def _completion(on_date: date) -> MagicMock:
    c = MagicMock()
    c.date = on_date
    return c


def _habit(name: str, completion_dates: list[date]) -> MagicMock:
    h = MagicMock()
    h.id = uuid.uuid4()
    h.name = name
    h.color = None
    h.target_days_per_week = 7
    h.completions = [_completion(d) for d in completion_dates]
    return h


def test_returns_none_when_no_habits() -> None:
    db = MagicMock()
    with (
        patch(
            "app.services.dashboard_service.habit_repository.list_habits",
            return_value=([], 0),
        ),
        patch("app.services.dashboard_service._today_utc", return_value=TODAY),
    ):
        assert _build_habits_today(db, uuid.uuid4()) is None


def test_builds_section_with_completion_and_streak() -> None:
    db = MagicMock()
    habits = [
        _habit("Water", [TODAY, TODAY - timedelta(days=1)]),  # done today, streak 2
        _habit("Read", [TODAY - timedelta(days=2)]),  # not done today
    ]
    with (
        patch(
            "app.services.dashboard_service.habit_repository.list_habits",
            return_value=(habits, 2),
        ),
        patch("app.services.dashboard_service._today_utc", return_value=TODAY),
    ):
        section = _build_habits_today(db, uuid.uuid4())

    assert section is not None
    assert section.total == 2
    assert section.completed_count == 1
    water = next(h for h in section.habits if h.name == "Water")
    assert water.completed_today is True
    assert water.current_streak == 2
    read = next(h for h in section.habits if h.name == "Read")
    assert read.completed_today is False
