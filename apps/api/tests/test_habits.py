"""Tests for the habit domain — /api/v1/habits.

Covers:
  Pure domain calculations:
    - compute_current_streak (forgiving "today not done yet" behaviour)
    - compute_longest_streak
    - completions_in_week
    - weekly_adherence_pct (cap, div-by-zero guard)

  Response assembly:
    - _habit_response derives the stats from a habit's completions

  Schema validation:
    - name blank / trimmed, target_days_per_week range

  Endpoint tests (service patched):
    - CRUD habits + completions, status codes, auth, not-found

  Service behaviour:
    - mark_complete is idempotent
    - update archiving stamps archived_at

  Ownership isolation:
    - another user's habit is not reachable (404)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.habit import (
    CompletionResponse,
    HabitCompletionsResponse,
    HabitListResponse,
    HabitResponse,
)
from app.services.habit_service import (
    _habit_response,
    completions_in_week,
    compute_current_streak,
    compute_longest_streak,
    mark_complete,
    update_habit,
    weekly_adherence_pct,
)

# ── Helpers ─────────────────────────────────────────────────────────────────────

TODAY = date.today()


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _completion_obj(habit_id: uuid.UUID, on_date: date) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.habit_id = habit_id
    c.date = on_date
    c.created_at = _now()
    return c


def _make_habit(
    *,
    user_id: uuid.UUID,
    name: str = "Drink water",
    target: int = 7,
    is_archived: bool = False,
    completion_dates: list[date] | None = None,
) -> MagicMock:
    h = MagicMock()
    h.id = uuid.uuid4()
    h.user_id = user_id
    h.name = name
    h.description = None
    h.color = None
    h.target_days_per_week = target
    h.is_archived = is_archived
    h.archived_at = None
    h.created_at = _now()
    h.updated_at = _now()
    h.completions = [_completion_obj(h.id, d) for d in (completion_dates or [])]
    return h


def _habit_resp(user_id: uuid.UUID) -> HabitResponse:
    return HabitResponse(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Drink water",
        description=None,
        color=None,
        target_days_per_week=7,
        is_archived=False,
        archived_at=None,
        created_at=_now(),
        updated_at=_now(),
        completed_today=False,
        current_streak=0,
        longest_streak=0,
        completions_this_week=0,
        weekly_adherence_pct=0,
    )


# ── Pure domain calculations ────────────────────────────────────────────────────


class TestCurrentStreak:
    def test_empty_is_zero(self) -> None:
        assert compute_current_streak(set(), TODAY) == 0

    def test_today_only(self) -> None:
        assert compute_current_streak({TODAY}, TODAY) == 1

    def test_consecutive_including_today(self) -> None:
        days = {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
        assert compute_current_streak(days, TODAY) == 3

    def test_today_not_done_but_yesterday_counts(self) -> None:
        # Today is still in progress; streak counts up to yesterday.
        days = {TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
        assert compute_current_streak(days, TODAY) == 2

    def test_broken_when_neither_today_nor_yesterday(self) -> None:
        days = {TODAY - timedelta(days=3), TODAY - timedelta(days=4)}
        assert compute_current_streak(days, TODAY) == 0

    def test_gap_stops_the_count(self) -> None:
        days = {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=3)}
        assert compute_current_streak(days, TODAY) == 2


class TestLongestStreak:
    def test_empty_is_zero(self) -> None:
        assert compute_longest_streak(set()) == 0

    def test_single(self) -> None:
        assert compute_longest_streak({TODAY}) == 1

    def test_longest_run_wins(self) -> None:
        base = date(2026, 6, 1)
        # run of 2 (Jun 1-2), gap, run of 4 (Jun 5-8)
        days = {base, base + timedelta(days=1)} | {
            base + timedelta(days=n) for n in (4, 5, 6, 7)
        }
        assert compute_longest_streak(days) == 4

    def test_all_consecutive(self) -> None:
        base = date(2026, 6, 1)
        days = {base + timedelta(days=n) for n in range(5)}
        assert compute_longest_streak(days) == 5


class TestCompletionsInWeek:
    def test_counts_only_current_week_up_to_today(self) -> None:
        today = date(2026, 6, 24)
        week_start = today - timedelta(days=today.weekday())  # Monday
        days = {
            week_start,
            week_start + timedelta(days=1),
            today,
            week_start - timedelta(days=1),  # previous week → excluded
            today + timedelta(days=1),  # future → excluded
        }
        assert completions_in_week(days, today) == 3

    def test_empty(self) -> None:
        assert completions_in_week(set(), TODAY) == 0


class TestWeeklyAdherence:
    def test_partial(self) -> None:
        assert weekly_adherence_pct(3, 7) == 43

    def test_full(self) -> None:
        assert weekly_adherence_pct(7, 7) == 100

    def test_over_target_capped(self) -> None:
        assert weekly_adherence_pct(10, 5) == 100

    def test_zero_target_guarded(self) -> None:
        assert weekly_adherence_pct(3, 0) == 0

    def test_none_done(self) -> None:
        assert weekly_adherence_pct(0, 5) == 0


# ── Response assembly ────────────────────────────────────────────────────────────


class TestHabitResponseAssembly:
    def test_derives_stats_from_completions(self) -> None:
        user_id = uuid.uuid4()
        habit = _make_habit(
            user_id=user_id,
            target=5,
            completion_dates=[TODAY, TODAY - timedelta(days=1)],
        )
        resp = _habit_response(habit, TODAY)
        assert resp.completed_today is True
        assert resp.current_streak == 2
        assert resp.longest_streak == 2
        assert resp.weekly_adherence_pct == weekly_adherence_pct(
            resp.completions_this_week, 5
        )

    def test_no_completions(self) -> None:
        habit = _make_habit(user_id=uuid.uuid4(), completion_dates=[])
        resp = _habit_response(habit, TODAY)
        assert resp.completed_today is False
        assert resp.current_streak == 0
        assert resp.longest_streak == 0


# ── Schema validation ────────────────────────────────────────────────────────────


class TestHabitSchemaValidation:
    def test_blank_name_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.habit import CreateHabitRequest

        with pytest.raises(PydanticValidationError):
            CreateHabitRequest(name="   ")

    def test_name_is_trimmed(self) -> None:
        from app.schemas.habit import CreateHabitRequest

        req = CreateHabitRequest(name="  Read  ")
        assert req.name == "Read"

    def test_target_out_of_range_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.habit import CreateHabitRequest

        with pytest.raises(PydanticValidationError):
            CreateHabitRequest(name="Read", target_days_per_week=8)

    def test_target_zero_fails(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.habit import CreateHabitRequest

        with pytest.raises(PydanticValidationError):
            CreateHabitRequest(name="Read", target_days_per_week=0)


# ── Endpoint tests ───────────────────────────────────────────────────────────────


class TestHabitEndpoints:
    def test_create_habit(self, client: TestClient) -> None:
        user = _make_user()
        resp = _habit_resp(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.create_habit", return_value=resp),
        ):
            r = client.post(
                "/api/v1/habits",
                json={"name": "Drink water", "target_days_per_week": 7},
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["name"] == "Drink water"

    def test_create_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/habits", json={"name": "Read"})
        assert r.status_code == 401

    def test_create_blank_name_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/habits", json={"name": "   "}, cookies=_auth(user)
            )
        assert r.status_code == 422

    def test_list_habits(self, client: TestClient) -> None:
        user = _make_user()
        page = HabitListResponse(
            items=[_habit_resp(user.id)], total=1, page=1, page_size=50
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.list_habits", return_value=page),
        ):
            r = client.get("/api/v1/habits", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_list_requires_auth(self, client: TestClient) -> None:
        r = client.get("/api/v1/habits")
        assert r.status_code == 401

    def test_get_habit(self, client: TestClient) -> None:
        user = _make_user()
        resp = _habit_resp(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.get_habit", return_value=resp),
        ):
            r = client.get(f"/api/v1/habits/{resp.id}", cookies=_auth(user))
        assert r.status_code == 200

    def test_get_habit_not_found(self, client: TestClient) -> None:
        from app.exceptions import NotFoundError

        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.habit_service.get_habit",
                side_effect=NotFoundError("Habit not found."),
            ),
        ):
            r = client.get(f"/api/v1/habits/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404

    def test_update_habit(self, client: TestClient) -> None:
        user = _make_user()
        resp = _habit_resp(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.update_habit", return_value=resp),
        ):
            r = client.patch(
                f"/api/v1/habits/{resp.id}",
                json={"name": "Drink more water"},
                cookies=_auth(user),
            )
        assert r.status_code == 200

    def test_delete_habit(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.delete_habit", return_value=True),
        ):
            r = client.delete(f"/api/v1/habits/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 204

    def test_delete_habit_not_found(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.delete_habit", return_value=False),
        ):
            r = client.delete(f"/api/v1/habits/{uuid.uuid4()}", cookies=_auth(user))
        assert r.status_code == 404


class TestCompletionEndpoints:
    def test_mark_complete(self, client: TestClient) -> None:
        user = _make_user()
        habit_id = uuid.uuid4()
        resp = CompletionResponse(
            id=uuid.uuid4(), habit_id=habit_id, date=TODAY, created_at=_now()
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.mark_complete", return_value=resp),
        ):
            r = client.post(
                f"/api/v1/habits/{habit_id}/completions",
                json={"date": str(TODAY)},
                cookies=_auth(user),
            )
        assert r.status_code == 201
        assert r.json()["date"] == str(TODAY)

    def test_mark_requires_auth(self, client: TestClient) -> None:
        r = client.post(f"/api/v1/habits/{uuid.uuid4()}/completions", json={})
        assert r.status_code == 401

    def test_list_completions(self, client: TestClient) -> None:
        user = _make_user()
        habit_id = uuid.uuid4()
        resp = HabitCompletionsResponse(habit_id=habit_id, items=[])
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.list_completions", return_value=resp),
        ):
            r = client.get(
                f"/api/v1/habits/{habit_id}/completions", cookies=_auth(user)
            )
        assert r.status_code == 200

    def test_unmark_complete(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.unmark_complete", return_value=True),
        ):
            r = client.delete(
                f"/api/v1/habits/{uuid.uuid4()}/completions/{TODAY}",
                cookies=_auth(user),
            )
        assert r.status_code == 204

    def test_unmark_not_found(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.habit_service.unmark_complete", return_value=False),
        ):
            r = client.delete(
                f"/api/v1/habits/{uuid.uuid4()}/completions/{TODAY}",
                cookies=_auth(user),
            )
        assert r.status_code == 404


# ── Service behaviour ────────────────────────────────────────────────────────────


class TestMarkCompleteService:
    def test_idempotent_returns_existing(self) -> None:
        user_id = uuid.uuid4()
        habit = _make_habit(user_id=user_id)
        existing = _completion_obj(habit.id, TODAY)
        db = MagicMock()
        with (
            patch(
                "app.repositories.habit_repository.get_habit_by_id",
                return_value=habit,
            ),
            patch(
                "app.repositories.habit_repository.get_completion",
                return_value=existing,
            ),
            patch(
                "app.repositories.habit_repository.create_completion"
            ) as create_mock,
        ):
            result = mark_complete(db, habit.id, user_id, TODAY)
        create_mock.assert_not_called()
        assert result.id == existing.id

    def test_creates_when_absent(self) -> None:
        user_id = uuid.uuid4()
        habit = _make_habit(user_id=user_id)
        created = _completion_obj(habit.id, TODAY)
        db = MagicMock()
        with (
            patch(
                "app.repositories.habit_repository.get_habit_by_id",
                return_value=habit,
            ),
            patch(
                "app.repositories.habit_repository.get_completion",
                side_effect=[None, created],
            ),
            patch(
                "app.repositories.habit_repository.create_completion"
            ) as create_mock,
        ):
            result = mark_complete(db, habit.id, user_id, TODAY)
        create_mock.assert_called_once()
        assert result.id == created.id


class TestUpdateArchiving:
    def test_archiving_sets_archived_at(self) -> None:
        user_id = uuid.uuid4()
        habit = _make_habit(user_id=user_id, is_archived=False)
        db = MagicMock()

        captured: dict[str, object] = {}

        def _capture(_db: object, _habit: object, **fields: object) -> object:
            captured.update(fields)
            return habit

        from app.schemas.habit import UpdateHabitRequest

        with (
            patch(
                "app.repositories.habit_repository.get_habit_by_id",
                return_value=habit,
            ),
            patch(
                "app.repositories.habit_repository.update_habit_fields",
                side_effect=_capture,
            ),
        ):
            update_habit(
                db,
                habit.id,
                user_id,
                UpdateHabitRequest(is_archived=True),
                today=TODAY,
            )
        assert captured.get("is_archived") is True
        assert captured.get("archived_at") is not None


# ── Ownership isolation ──────────────────────────────────────────────────────────


class TestOwnershipIsolation:
    def test_other_users_habit_not_found(self, client: TestClient) -> None:
        """User B requesting User A's habit gets 404 (repo scopes by user_id)."""
        user_b = _make_user()
        with (
            patch(
                "app.dependencies.user_repository.get_user_by_id", return_value=user_b
            ),
            patch(
                "app.repositories.habit_repository.get_habit_by_id", return_value=None
            ),
        ):
            r = client.get(f"/api/v1/habits/{uuid.uuid4()}", cookies=_auth(user_b))
        assert r.status_code == 404
