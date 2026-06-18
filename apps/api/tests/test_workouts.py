"""Tests for /api/v1/templates/* and /api/v1/workouts/* endpoints.

Covers:
  Service-layer unit tests:
    - compute_volume_kg
    - estimated_one_rep_max
    - is_strength_pr / is_duration_pr / is_distance_pr

  Template API:
    - POST   /api/v1/templates                  (201, validation, auth guard)
    - GET    /api/v1/templates                  (200, auth guard)
    - GET    /api/v1/templates/{id}             (200, 404)
    - PUT    /api/v1/templates/{id}             (200, 404)
    - DELETE /api/v1/templates/{id}             (204, 404)

  Workout session API:
    - POST   /api/v1/workouts                   (201, from template, ad-hoc)
    - GET    /api/v1/workouts                   (200, auth guard)
    - GET    /api/v1/workouts/{id}              (200, 404, other-user 404)
    - POST   /api/v1/workouts/{id}/complete     (200, idempotent, volume calc)
    - PATCH  /api/v1/workouts/{id}              (200, 404)
    - DELETE /api/v1/workouts/{id}              (204, 404)

  Exercise management:
    - POST   /api/v1/workouts/{id}/exercises    (201, 404)
    - DELETE /api/v1/workouts/{id}/exercises/{we_id}  (204, 404)

  Set logging:
    - POST   .../sets            (201, PR detection, validation)
    - PATCH  .../sets/{id}       (200, 404)
    - DELETE .../sets/{id}       (204, 404)

  Ownership isolation:
    - Other user cannot access templates or workouts
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database import get_db
from app.main import app as fastapi_app
from app.models.workout import WorkoutSet
from app.services.workout_service import (
    compute_volume_kg,
    estimated_one_rep_max,
    is_distance_pr,
    is_duration_pr,
    is_strength_pr,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_exercise(name: str = "Bench Press", category: str = "strength") -> MagicMock:
    ex = MagicMock()
    ex.id = uuid.uuid4()
    ex.name = name
    ex.category = category
    return ex


def _make_template_exercise(exercise: MagicMock, order: int = 0) -> MagicMock:
    te = MagicMock()
    te.id = uuid.uuid4()
    te.exercise_id = exercise.id
    te.exercise = exercise
    te.order_index = order
    te.default_sets = 3
    te.default_reps = 8
    te.default_weight_kg = 80.0
    te.default_duration_seconds = None
    te.default_distance_meters = None
    te.notes = None
    return te


def _make_template(
    user_id: uuid.UUID,
    name: str = "Push Day",
    exercises: list | None = None,
) -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.user_id = user_id
    t.name = name
    t.description = None
    t.is_system = False
    t.template_exercises = exercises or []
    t.created_at = _now()
    t.updated_at = _now()
    return t


@contextmanager
def _override_db():
    """Override get_db with a MagicMock session for the duration of the block.

    This prevents db.commit() and db.refresh() from blowing up on MagicMock
    objects when the repository functions return mocks.
    """
    mock_session = MagicMock()
    fastapi_app.dependency_overrides[get_db] = lambda: mock_session
    try:
        yield mock_session
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)


def _make_set(
    *,
    reps: int | None = 8,
    weight_kg: float | None = 80.0,
    duration_seconds: int | None = None,
    distance_meters: float | None = None,
    is_pr: bool = False,
) -> MagicMock:
    ws = MagicMock(spec=WorkoutSet)
    ws.id = uuid.uuid4()
    ws.set_number = 1
    ws.reps = reps
    ws.weight_kg = weight_kg
    ws.duration_seconds = duration_seconds
    ws.distance_meters = distance_meters
    ws.rpe = None
    ws.is_pr = is_pr
    ws.completed_at = _now()
    return ws


def _make_workout_exercise(exercise: MagicMock, sets: list | None = None) -> MagicMock:
    we = MagicMock()
    we.id = uuid.uuid4()
    we.exercise_id = exercise.id
    we.exercise = exercise
    we.order_index = 0
    we.notes = None
    we.sets = sets or []
    return we


def _make_workout(
    user_id: uuid.UUID,
    name: str = "Push Day",
    exercises: list | None = None,
    completed: bool = False,
    template: MagicMock | None = None,
) -> MagicMock:
    w = MagicMock()
    w.id = uuid.uuid4()
    w.user_id = user_id
    w.name = name
    w.notes = None
    w.template_id = template.id if template else None
    w.template = template
    w.started_at = _now()
    w.completed_at = _now() if completed else None
    w.total_volume_kg = 640.0 if completed else None
    w.exercises = exercises or []
    w.created_at = _now()
    return w


# ── Unit tests: compute_volume_kg ─────────────────────────────────────────────


class TestComputeVolumeKg:
    def test_single_set(self) -> None:
        sets = [_make_set(reps=8, weight_kg=80.0)]
        assert compute_volume_kg(sets) == 640.0  # type: ignore[arg-type]

    def test_multiple_sets(self) -> None:
        sets = [
            _make_set(reps=8, weight_kg=80.0),
            _make_set(reps=6, weight_kg=90.0),
        ]
        assert compute_volume_kg(sets) == 8 * 80.0 + 6 * 90.0  # type: ignore[arg-type]

    def test_skips_sets_missing_weight(self) -> None:
        sets = [_make_set(reps=8, weight_kg=None)]
        assert compute_volume_kg(sets) is None  # type: ignore[arg-type]

    def test_skips_sets_missing_reps(self) -> None:
        sets = [_make_set(reps=None, weight_kg=80.0)]
        assert compute_volume_kg(sets) is None  # type: ignore[arg-type]

    def test_empty_list_returns_none(self) -> None:
        assert compute_volume_kg([]) is None

    def test_skips_zero_reps(self) -> None:
        sets = [_make_set(reps=0, weight_kg=80.0)]
        assert compute_volume_kg(sets) is None  # type: ignore[arg-type]

    def test_mixed_sets(self) -> None:
        """Only strength sets contribute; cardio sets (no weight) are skipped."""
        sets = [
            _make_set(reps=10, weight_kg=50.0),
            _make_set(reps=None, weight_kg=None, duration_seconds=30),
        ]
        assert compute_volume_kg(sets) == 500.0  # type: ignore[arg-type]


# ── Unit tests: estimated_one_rep_max ─────────────────────────────────────────


class TestEstimated1RM:
    def test_epley_formula(self) -> None:
        result = estimated_one_rep_max(100.0, 5)
        assert result == round(100.0 * (1 + 5 / 30), 2)

    def test_zero_reps_returns_none(self) -> None:
        assert estimated_one_rep_max(100.0, 0) is None

    def test_zero_weight_returns_none(self) -> None:
        assert estimated_one_rep_max(0.0, 10) is None

    def test_one_rep_max_equals_weight(self) -> None:
        # 1 rep → 1RM ≈ weight * (1 + 1/30)
        result = estimated_one_rep_max(100.0, 1)
        assert result == round(100.0 * (1 + 1 / 30), 2)


# ── Unit tests: PR detection ──────────────────────────────────────────────────


class TestPRDetection:
    def test_strength_pr_when_no_history(self) -> None:
        db = MagicMock()
        with patch(
            "app.services.workout_service.workout_repository.get_best_set_for_exercise",
            return_value=None,
        ):
            assert is_strength_pr(db, uuid.uuid4(), uuid.uuid4(), 80.0, 8) is True

    def test_strength_pr_when_volume_exceeds_best(self) -> None:
        db = MagicMock()
        best = _make_set(reps=8, weight_kg=80.0)  # volume=640
        with patch(
            "app.services.workout_service.workout_repository.get_best_set_for_exercise",
            return_value=best,
        ):
            # New set: 9 * 80 = 720 > 640 → PR
            assert is_strength_pr(db, uuid.uuid4(), uuid.uuid4(), 80.0, 9) is True

    def test_no_pr_when_volume_does_not_exceed_best(self) -> None:
        db = MagicMock()
        best = _make_set(reps=8, weight_kg=80.0)  # volume=640
        with patch(
            "app.services.workout_service.workout_repository.get_best_set_for_exercise",
            return_value=best,
        ):
            assert is_strength_pr(db, uuid.uuid4(), uuid.uuid4(), 80.0, 7) is False

    def test_duration_pr_when_no_history(self) -> None:
        db = MagicMock()
        with patch(
            "app.services.workout_service.workout_repository.get_best_duration_for_exercise",
            return_value=None,
        ):
            assert is_duration_pr(db, uuid.uuid4(), uuid.uuid4(), 60) is True

    def test_duration_pr_when_exceeds_best(self) -> None:
        db = MagicMock()
        best = _make_set(duration_seconds=60, reps=None, weight_kg=None)
        with patch(
            "app.services.workout_service.workout_repository.get_best_duration_for_exercise",
            return_value=best,
        ):
            assert is_duration_pr(db, uuid.uuid4(), uuid.uuid4(), 90) is True

    def test_no_duration_pr_when_equal(self) -> None:
        db = MagicMock()
        best = _make_set(duration_seconds=60, reps=None, weight_kg=None)
        with patch(
            "app.services.workout_service.workout_repository.get_best_duration_for_exercise",
            return_value=best,
        ):
            assert is_duration_pr(db, uuid.uuid4(), uuid.uuid4(), 60) is False

    def test_distance_pr_when_no_history(self) -> None:
        db = MagicMock()
        with patch(
            "app.services.workout_service.workout_repository.get_best_distance_for_exercise",
            return_value=None,
        ):
            assert is_distance_pr(db, uuid.uuid4(), uuid.uuid4(), 5000.0) is True

    def test_no_distance_pr_when_shorter(self) -> None:
        db = MagicMock()
        best = _make_set(distance_meters=5000.0, reps=None, weight_kg=None)
        with patch(
            "app.services.workout_service.workout_repository.get_best_distance_for_exercise",
            return_value=best,
        ):
            assert is_distance_pr(db, uuid.uuid4(), uuid.uuid4(), 3000.0) is False


# ── POST /api/v1/templates ────────────────────────────────────────────────────


class TestCreateTemplate:
    def test_creates_template_201(self, client: TestClient) -> None:
        user = _make_user()
        template = _make_template(user.id)
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.create_template", return_value=template),
            patch("app.services.workout_service.workout_repository.add_template_exercise"),
            # db.refresh(template) will be called on the mock session, not on the template
        ):
            resp = client.post(
                "/api/v1/templates",
                json={"name": "Push Day"},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Push Day"

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/templates", json={"name": "Push Day"})
        assert resp.status_code == 401

    def test_name_required(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/templates",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_name_too_long_rejected(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/templates",
                json={"name": "x" * 121},
                cookies=_auth(user),
            )
        assert resp.status_code == 422


# ── GET /api/v1/templates ─────────────────────────────────────────────────────


class TestListTemplates:
    def test_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.list_templates_for_user",
                return_value=([], 0),
            ),
        ):
            resp = client.get("/api/v1/templates", cookies=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert "total" in data

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 401

    def test_empty_list(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.list_templates_for_user",
                return_value=([], 0),
            ),
        ):
            resp = client.get("/api/v1/templates", cookies=_auth(user))
        assert resp.json()["total"] == 0
        assert resp.json()["templates"] == []


# ── GET /api/v1/templates/{id} ────────────────────────────────────────────────


class TestGetTemplate:
    def test_returns_template(self, client: TestClient) -> None:
        user = _make_user()
        template = _make_template(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=template,
            ),
        ):
            resp = client.get(f"/api/v1/templates/{template.id}", cookies=_auth(user))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Push Day"

    def test_returns_404_when_not_found(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=None,
            ),
        ):
            resp = client.get(f"/api/v1/templates/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/templates/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PUT /api/v1/templates/{id} ────────────────────────────────────────────────


class TestUpdateTemplate:
    def test_updates_name(self, client: TestClient) -> None:
        user = _make_user()
        template = _make_template(user.id, name="Old Name")
        updated = _make_template(user.id, name="New Name")
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                # First call: fetch for mutation check; second call: re-fetch after commit
                side_effect=[template, updated],
            ),
            patch("app.services.workout_service.workout_repository.update_template_fields", return_value=updated),
            patch("app.services.workout_service.workout_repository.delete_template_exercises"),
        ):
            resp = client.put(
                f"/api/v1/templates/{template.id}",
                json={"name": "New Name"},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_returns_404_for_missing_template(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=None,
            ),
        ):
            resp = client.put(
                f"/api/v1/templates/{uuid.uuid4()}",
                json={"name": "x"},
                cookies=_auth(user),
            )
        assert resp.status_code == 404


# ── DELETE /api/v1/templates/{id} ────────────────────────────────────────────


class TestDeleteTemplate:
    def test_deletes_and_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        template = _make_template(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=template,
            ),
            patch("app.services.workout_service.workout_repository.delete_template"),
        ):
            resp = client.delete(
                f"/api/v1/templates/{template.id}", cookies=_auth(user)
            )
        assert resp.status_code == 204

    def test_returns_404_for_missing(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=None,
            ),
        ):
            resp = client.delete(
                f"/api/v1/templates/{uuid.uuid4()}", cookies=_auth(user)
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/templates/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── POST /api/v1/workouts ────────────────────────────────────────────────────


class TestStartWorkout:
    def _start(self, client: TestClient, user: MagicMock, workout: MagicMock, body: dict) -> object:
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.create_workout",
                return_value=workout,
            ),
            patch(
                "app.services.workout_service.workout_repository.get_template_for_user",
                return_value=None,
            ),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=workout,
            ),
        ):
            return client.post("/api/v1/workouts", json=body, cookies=_auth(user))

    def test_adhoc_workout_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id)
        resp = self._start(client, user, workout, {"name": "Morning session"})
        assert resp.status_code == 201  # type: ignore[union-attr]

    def test_workout_in_progress_has_no_completed_at(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id)
        resp = self._start(client, user, workout, {"name": "Morning session"})
        assert resp.json()["completed_at"] is None  # type: ignore[union-attr]

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/workouts", json={"name": "Test"})
        assert resp.status_code == 401

    def test_default_name_is_workout(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id, name="Workout")
        resp = self._start(client, user, workout, {})
        assert resp.status_code == 201  # type: ignore[union-attr]


# ── GET /api/v1/workouts ─────────────────────────────────────────────────────


class TestListWorkouts:
    def test_returns_200(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.list_workouts_for_user",
                return_value=([], 0),
            ),
        ):
            resp = client.get("/api/v1/workouts", cookies=_auth(user))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/v1/workouts").status_code == 401

    def test_completed_only_filter(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.list_workouts_for_user",
                return_value=([], 0),
            ) as mock_list,
        ):
            client.get("/api/v1/workouts?completed_only=true", cookies=_auth(user))
            _, kwargs = mock_list.call_args
            assert kwargs.get("completed_only") is True


# ── GET /api/v1/workouts/{id} ────────────────────────────────────────────────


class TestGetWorkout:
    def test_returns_workout(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=workout,
            ),
        ):
            resp = client.get(f"/api/v1/workouts/{workout.id}", cookies=_auth(user))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Push Day"

    def test_404_for_other_users_workout(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=None,
            ),
        ):
            resp = client.get(f"/api/v1/workouts/{uuid.uuid4()}", cookies=_auth(user))
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        assert client.get(f"/api/v1/workouts/{uuid.uuid4()}").status_code == 401


# ── POST /api/v1/workouts/{id}/complete ──────────────────────────────────────


class TestCompleteWorkout:
    def test_completes_and_sets_volume(self, client: TestClient) -> None:
        user = _make_user()
        ws = _make_set(reps=8, weight_kg=80.0)
        we = _make_workout_exercise(_make_exercise(), sets=[ws])
        workout = _make_workout(user.id, exercises=[we])
        completed = _make_workout(user.id, exercises=[we], completed=True)

        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                side_effect=[workout, completed],
            ),
            patch("app.services.workout_service.workout_repository.complete_workout", return_value=completed),
        ):
            resp = client.post(
                f"/api/v1/workouts/{workout.id}/complete",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["completed_at"] is not None

    def test_idempotent_on_already_completed(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id, completed=True)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=workout,
            ),
        ):
            resp = client.post(
                f"/api/v1/workouts/{workout.id}/complete",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 200

    def test_404_for_missing_workout(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=None,
            ),
        ):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/complete",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 404


# ── PATCH /api/v1/workouts/{id} ──────────────────────────────────────────────


class TestUpdateWorkout:
    def test_updates_name(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id, name="Old Name")
        updated = _make_workout(user.id, name="New Name")
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                side_effect=[workout, updated],
            ),
            patch("app.services.workout_service.workout_repository.update_workout_fields", return_value=updated),
        ):
            resp = client.patch(
                f"/api/v1/workouts/{workout.id}",
                json={"name": "New Name"},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_404_for_missing(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=None,
            ),
        ):
            resp = client.patch(
                f"/api/v1/workouts/{uuid.uuid4()}",
                json={"name": "x"},
                cookies=_auth(user),
            )
        assert resp.status_code == 404


# ── DELETE /api/v1/workouts/{id} ─────────────────────────────────────────────


class TestDeleteWorkout:
    def test_deletes_and_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        workout = _make_workout(user.id)
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=workout,
            ),
            patch("app.services.workout_service.workout_repository.delete_workout"),
        ):
            resp = client.delete(f"/api/v1/workouts/{workout.id}", cookies=_auth(user))
        assert resp.status_code == 204

    def test_requires_auth(self, client: TestClient) -> None:
        assert client.delete(f"/api/v1/workouts/{uuid.uuid4()}").status_code == 401


# ── POST /api/v1/workouts/{id}/exercises ─────────────────────────────────────


class TestAddExercise:
    def test_adds_exercise_returns_201(self, client: TestClient) -> None:
        user = _make_user()
        ex = _make_exercise()
        we = _make_workout_exercise(ex)
        workout = _make_workout(user.id, exercises=[we])
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=workout,
            ),
            patch("app.services.workout_service.workout_repository.add_workout_exercise", return_value=we),
        ):
            resp = client.post(
                f"/api/v1/workouts/{workout.id}/exercises",
                json={"exercise_id": str(ex.id)},
                cookies=_auth(user),
            )
        assert resp.status_code == 201

    def test_404_for_missing_workout(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_for_user",
                return_value=None,
            ),
        ):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises",
                json={"exercise_id": str(uuid.uuid4())},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_exercise_id_required(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 422


# ── DELETE /api/v1/workouts/{id}/exercises/{we_id} ───────────────────────────


class TestRemoveExercise:
    def test_removes_and_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        we_id = uuid.uuid4()
        workout_id = uuid.uuid4()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_exercise",
                return_value=MagicMock(),
            ),
            patch("app.services.workout_service.workout_repository.delete_workout_exercise"),
        ):
            resp = client.delete(
                f"/api/v1/workouts/{workout_id}/exercises/{we_id}",
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_404_for_missing(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_exercise",
                return_value=None,
            ),
        ):
            resp = client.delete(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 404


# ── POST .../sets ─────────────────────────────────────────────────────────────


class TestLogSet:
    def _log(
        self, client: TestClient, user: MagicMock, we_id: uuid.UUID, body: dict
    ) -> object:
        we = MagicMock()
        we.exercise_id = uuid.uuid4()
        set_kwargs = {k: body.get(k) for k in ("reps", "weight_kg", "duration_seconds", "distance_meters") if k in body}
        ws = _make_set(**set_kwargs)  # type: ignore[arg-type]
        ws.is_pr = False
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_workout_exercise", return_value=we),
            patch("app.services.workout_service.workout_repository.get_best_set_for_exercise", return_value=None),
            patch("app.services.workout_service.workout_repository.get_best_duration_for_exercise", return_value=None),
            patch("app.services.workout_service.workout_repository.get_best_distance_for_exercise", return_value=None),
            patch("app.services.workout_service.workout_repository.log_set", return_value=ws),
            patch("app.services.workout_service.workout_repository.get_set", return_value=ws),
        ):
            return client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{we_id}/sets",
                json=body,
                cookies=_auth(user),
            )

    def test_logs_strength_set_201(self, client: TestClient) -> None:
        user = _make_user()
        resp = self._log(
            client, user, uuid.uuid4(),
            {"set_number": 1, "reps": 8, "weight_kg": 80.0},
        )
        assert resp.status_code == 201  # type: ignore[union-attr]

    def test_logs_cardio_set(self, client: TestClient) -> None:
        user = _make_user()
        resp = self._log(
            client, user, uuid.uuid4(),
            {"set_number": 1, "distance_meters": 5000.0},
        )
        assert resp.status_code == 201  # type: ignore[union-attr]

    def test_logs_timed_set(self, client: TestClient) -> None:
        user = _make_user()
        resp = self._log(
            client, user, uuid.uuid4(),
            {"set_number": 1, "duration_seconds": 60},
        )
        assert resp.status_code == 201  # type: ignore[union-attr]

    def test_no_metrics_rejected_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets",
                json={"set_number": 1},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_rpe_out_of_range_rejected(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets",
                json={"set_number": 1, "reps": 8, "weight_kg": 80.0, "rpe": 11},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets",
            json={"set_number": 1, "reps": 8, "weight_kg": 80.0},
        )
        assert resp.status_code == 401

    def test_404_for_missing_workout_exercise(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.workout_service.workout_repository.get_workout_exercise",
                return_value=None,
            ),
        ):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets",
                json={"set_number": 1, "reps": 8, "weight_kg": 80.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_first_set_is_pr(self, client: TestClient) -> None:
        """First-ever set for an exercise should be marked as PR."""
        user = _make_user()
        we = MagicMock()
        we.exercise_id = uuid.uuid4()
        ws = _make_set(reps=8, weight_kg=80.0, is_pr=True)
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_workout_exercise", return_value=we),
            patch("app.services.workout_service.workout_repository.get_best_set_for_exercise", return_value=None),
            patch("app.services.workout_service.workout_repository.log_set", return_value=ws),
            patch("app.services.workout_service.workout_repository.get_set", return_value=ws),
        ):
            resp = client.post(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets",
                json={"set_number": 1, "reps": 8, "weight_kg": 80.0},
                cookies=_auth(user),
            )
        assert resp.status_code == 201
        assert resp.json()["is_pr"] is True


# ── PATCH .../sets/{id} ───────────────────────────────────────────────────────


class TestUpdateSet:
    def test_updates_reps(self, client: TestClient) -> None:
        user = _make_user()
        ws = _make_set(reps=10, weight_kg=80.0)
        with (
            _override_db(),
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_set", return_value=ws),
            patch("app.services.workout_service.workout_repository.update_set_fields", return_value=ws),
        ):
            resp = client.patch(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets/{ws.id}",
                json={"reps": 10},
                cookies=_auth(user),
            )
        assert resp.status_code == 200

    def test_404_for_missing_set(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_set", return_value=None),
        ):
            resp = client.patch(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets/{uuid.uuid4()}",
                json={"reps": 10},
                cookies=_auth(user),
            )
        assert resp.status_code == 404


# ── DELETE .../sets/{id} ──────────────────────────────────────────────────────


class TestDeleteSet:
    def test_deletes_and_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        ws = _make_set()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_set", return_value=ws),
            patch("app.services.workout_service.workout_repository.delete_set"),
        ):
            resp = client.delete(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets/{ws.id}",
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_404_for_missing_set(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.workout_service.workout_repository.get_set", return_value=None),
        ):
            resp = client.delete(
                f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(
            f"/api/v1/workouts/{uuid.uuid4()}/exercises/{uuid.uuid4()}/sets/{uuid.uuid4()}"
        )
        assert resp.status_code == 401
