"""Tests for /api/v1/goals/* endpoints and goal_service calculations.

Covers:
  - POST /           create goal (201, validation, auth guard)
  - GET  /           list goals (pagination, status filter, auth guard)
  - GET  /{id}       get goal (200, 404 for missing, 404 for other user's goal)
  - PUT  /{id}       update (partial, status transitions, 404)
  - DELETE /{id}     delete (204, 404)
  - progress_pct     unit tests for compute_progress_pct
  - status transitions  validated transitions and illegal ones
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services.goal_service import compute_progress_pct

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_active = True
    return user


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _make_goal(
    user_id: uuid.UUID,
    *,
    title: str = "Lose 5 kg",
    goal_type: str = "weight_loss",
    status: str = "active",
    starting_value: float | None = 80.0,
    target_value: float | None = 75.0,
    current_value: float | None = 78.0,
    target_unit: str | None = "kg",
) -> MagicMock:
    g = MagicMock()
    g.id = uuid.uuid4()
    g.user_id = user_id
    g.goal_type = goal_type
    g.title = title
    g.description = None
    g.starting_value = starting_value
    g.target_value = target_value
    g.current_value = current_value
    g.target_unit = target_unit
    g.deadline = None
    g.status = status
    g.completed_at = None
    g.is_public = False
    g.created_at = datetime.now(timezone.utc)
    g.updated_at = datetime.now(timezone.utc)
    return g


# ── Progress calculation ───────────────────────────────────────────────────────

class TestComputeProgressPct:
    def test_returns_none_when_target_missing(self) -> None:
        assert compute_progress_pct(80.0, None, 78.0) is None

    def test_returns_none_when_current_missing(self) -> None:
        assert compute_progress_pct(80.0, 75.0, None) is None

    def test_decrease_goal_halfway(self) -> None:
        # 80 → 75 target, currently at 77.5 = 50%
        assert compute_progress_pct(80.0, 75.0, 77.5) == 50.0

    def test_decrease_goal_complete(self) -> None:
        assert compute_progress_pct(80.0, 75.0, 75.0) == 100.0

    def test_increase_goal_halfway(self) -> None:
        # bench press 60 → 100, currently at 80 = 50%
        assert compute_progress_pct(60.0, 100.0, 80.0) == 50.0

    def test_increase_goal_complete(self) -> None:
        assert compute_progress_pct(60.0, 100.0, 100.0) == 100.0

    def test_clamped_at_zero(self) -> None:
        # current went the wrong way
        assert compute_progress_pct(80.0, 75.0, 85.0) == 0.0

    def test_clamped_at_100(self) -> None:
        assert compute_progress_pct(80.0, 75.0, 70.0) == 100.0

    def test_no_starting_value_uses_zero_baseline(self) -> None:
        # target 100 from implicit 0, currently at 50 = 50%
        assert compute_progress_pct(None, 100.0, 50.0) == 50.0

    def test_target_equals_starting_returns_100_when_matched(self) -> None:
        assert compute_progress_pct(70.0, 70.0, 70.0) == 100.0

    def test_target_equals_starting_returns_0_when_not_matched(self) -> None:
        assert compute_progress_pct(70.0, 70.0, 68.0) == 0.0


# ── POST /api/v1/goals ────────────────────────────────────────────────────────

class TestCreateGoal:
    def test_valid_goal_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        # current_value == starting_value → 0% progress
        goal = _make_goal(user.id, current_value=80.0)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.create_goal", return_value=goal),
        ):
            resp = client.post(
                "/api/v1/goals",
                json={
                    "goal_type": "weight_loss",
                    "title": "Lose 5 kg",
                    "starting_value": 80.0,
                    "target_value": 75.0,
                    "current_value": 80.0,
                    "target_unit": "kg",
                },
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Lose 5 kg"
        assert data["progress_pct"] == 0.0

    def test_qualitative_goal_no_numeric_fields(self, client: TestClient) -> None:
        user = _make_user()
        goal = _make_goal(user.id, title="Run a 5K", goal_type="endurance",
                          starting_value=None, target_value=None,
                          current_value=None, target_unit=None)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.create_goal", return_value=goal),
        ):
            resp = client.post(
                "/api/v1/goals",
                json={"goal_type": "endurance", "title": "Run a 5K"},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert resp.json()["progress_pct"] is None

    def test_numeric_value_without_unit_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/goals",
                json={"goal_type": "weight_loss", "title": "Lose weight",
                      "target_value": 75.0},  # missing target_unit
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_empty_title_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/goals",
                json={"goal_type": "custom", "title": ""},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_invalid_goal_type_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/goals",
                json={"goal_type": "flying", "title": "Fly to the moon"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/goals",
            json={"goal_type": "custom", "title": "Test"},
        )
        assert resp.status_code == 401


# ── GET /api/v1/goals ─────────────────────────────────────────────────────────

class TestListGoals:
    def test_returns_goal_list(self, client: TestClient) -> None:
        user = _make_user()
        goals = [_make_goal(user.id) for _ in range(3)]
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.goal_service.goal_repository.list_goals_for_user",
                return_value=(goals, 3),
            ),
        ):
            resp = client.get("/api/v1/goals", cookies=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["goals"]) == 3
        assert data["has_next"] is False

    def test_pagination_has_next(self, client: TestClient) -> None:
        user = _make_user()
        goals = [_make_goal(user.id)]
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.goal_service.goal_repository.list_goals_for_user",
                return_value=(goals, 5),
            ),
        ):
            resp = client.get("/api/v1/goals?page=1&page_size=1", cookies=_auth(user))
        assert resp.json()["has_next"] is True

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/goals")
        assert resp.status_code == 401


# ── GET /api/v1/goals/{id} ────────────────────────────────────────────────────

class TestGetGoal:
    def test_returns_goal(self, client: TestClient) -> None:
        user = _make_user()
        goal = _make_goal(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.goal_service.goal_repository.get_goal_for_user",
                return_value=goal,
            ),
        ):
            resp = client.get(f"/api/v1/goals/{goal.id}", cookies=_auth(user))
        assert resp.status_code == 200

    def test_other_users_goal_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.goal_service.goal_repository.get_goal_for_user",
                return_value=None,
            ),
        ):
            resp = client.get(f"/api/v1/goals/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/goals/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PUT /api/v1/goals/{id} ────────────────────────────────────────────────────

class TestUpdateGoal:
    def test_updates_title(self, client: TestClient) -> None:
        user = _make_user()
        goal = _make_goal(user.id)
        updated = _make_goal(user.id, title="Updated title")
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=goal),
            patch("app.services.goal_service.goal_repository.update_goal", return_value=updated),
        ):
            resp = client.put(
                f"/api/v1/goals/{goal.id}",
                json={"title": "Updated title"},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"

    def test_valid_status_transition_active_to_completed(self, client: TestClient) -> None:
        user = _make_user()
        goal = _make_goal(user.id, status="active")
        completed_goal = _make_goal(user.id, status="completed")
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=goal),
            patch("app.services.goal_service.goal_repository.update_goal", return_value=completed_goal),
        ):
            resp = client.put(
                f"/api/v1/goals/{goal.id}",
                json={"status": "completed"},
                cookies=_auth(user),
            )
        assert resp.status_code == 200

    def test_invalid_status_transition_completed_to_active_returns_422(
        self, client: TestClient
    ) -> None:
        user = _make_user()
        goal = _make_goal(user.id, status="completed")
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=goal),
        ):
            resp = client.put(
                f"/api/v1/goals/{goal.id}",
                json={"status": "active"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=None),
        ):
            resp = client.put(
                f"/api/v1/goals/{uuid.uuid4()}",
                json={"title": "X"},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.put(f"/api/v1/goals/{uuid.uuid4()}", json={"title": "X"})
        assert resp.status_code == 401


# ── DELETE /api/v1/goals/{id} ─────────────────────────────────────────────────

class TestDeleteGoal:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        goal = _make_goal(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=goal),
            patch("app.services.goal_service.goal_repository.delete_goal"),
        ):
            resp = client.delete(f"/api/v1/goals/{goal.id}", cookies=_auth(user))
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.goal_service.goal_repository.get_goal_for_user", return_value=None),
        ):
            resp = client.delete(f"/api/v1/goals/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/goals/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── Status transition unit tests ──────────────────────────────────────────────

class TestStatusTransitions:
    def test_active_to_paused_allowed(self) -> None:
        from app.services.goal_service import _validate_status_transition
        _validate_status_transition("active", "paused")  # should not raise

    def test_active_to_cancelled_allowed(self) -> None:
        from app.services.goal_service import _validate_status_transition
        _validate_status_transition("active", "cancelled")

    def test_paused_to_active_allowed(self) -> None:
        from app.services.goal_service import _validate_status_transition
        _validate_status_transition("paused", "active")

    def test_completed_to_active_forbidden(self) -> None:
        from app.exceptions import ValidationError
        from app.services.goal_service import _validate_status_transition
        with pytest.raises(ValidationError):
            _validate_status_transition("completed", "active")

    def test_cancelled_to_active_forbidden(self) -> None:
        from app.exceptions import ValidationError
        from app.services.goal_service import _validate_status_transition
        with pytest.raises(ValidationError):
            _validate_status_transition("cancelled", "active")

    def test_same_status_is_noop(self) -> None:
        from app.services.goal_service import _validate_status_transition
        _validate_status_transition("active", "active")  # should not raise
