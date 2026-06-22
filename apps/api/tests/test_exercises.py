"""Tests for /api/v1/exercises/* endpoints and exercise_service.

Covers:
  - POST /           create custom exercise (201, validation, auth guard)
  - GET  /           list exercises (system + own, search, filter, auth guard)
  - GET  /{id}       get exercise (200, 404 for missing, 404 for other user's custom)
  - PATCH /{id}      update (owner only, 403 for system, 403 for other user's)
  - DELETE /{id}     soft delete (204, 403 for system, 403 for other user's)
  - Seed helper      seed_exercises inserts system exercises only once
  - Schemas          muscle_groups parsing and name stripping
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.exercise import Exercise

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_active = True
    return user


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _make_exercise(
    user_id: uuid.UUID | None = None,
    *,
    is_system: bool = False,
    name: str = "Test Exercise",
    category: str = "strength",
    equipment: str = "barbell",
    muscle_groups: str = "chest,triceps",
) -> MagicMock:
    e = MagicMock(spec=Exercise)
    e.id = uuid.uuid4()
    e.name = name
    e.description = "A test exercise"
    e.instructions = "Do the thing"
    e.category = category
    e.muscle_groups = muscle_groups
    e.equipment = equipment
    e.is_system = is_system
    e.is_active = True
    e.user_id = user_id
    e.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    e.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return e


def _exercise_response(e: MagicMock):  # type: ignore[return]
    from app.schemas.exercises import ExerciseResponse

    raw = e.muscle_groups or ""
    groups = [m.strip() for m in raw.split(",") if m.strip()]
    return ExerciseResponse(
        id=e.id,
        name=e.name,
        description=e.description,
        instructions=e.instructions,
        category=e.category,
        muscle_groups=groups,
        equipment=e.equipment,
        is_system=e.is_system,
        user_id=e.user_id,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


# ── POST /api/v1/exercises ─────────────────────────────────────────────────────


class TestCreateExercise:
    def test_returns_201_with_valid_data(self, client: TestClient) -> None:
        user = _make_user()
        exercise = _make_exercise(user_id=user.id)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.create_exercise",
                return_value=_exercise_response(exercise),
            ),
        ):
            resp = client.post(
                "/api/v1/exercises",
                json={
                    "name": "Cable Fly",
                    "category": "strength",
                    "equipment": "cable",
                    "muscle_groups": ["chest"],
                },
                cookies=_auth(user),
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == exercise.name

    def test_empty_name_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/exercises",
                json={"name": "", "category": "strength", "equipment": "none"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_invalid_category_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/exercises",
                json={"name": "Thing", "category": "not_a_category", "equipment": "none"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_invalid_equipment_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/exercises",
                json={"name": "Thing", "category": "strength", "equipment": "flamethrower"},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/exercises",
            json={"name": "Cable Fly", "category": "strength", "equipment": "cable"},
        )
        assert resp.status_code == 401


# ── GET /api/v1/exercises ──────────────────────────────────────────────────────


class TestListExercises:
    def test_returns_list(self, client: TestClient) -> None:
        user = _make_user()
        exercise = _make_exercise(is_system=True)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.list_exercises",
                return_value=([_exercise_response(exercise)], 1),
            ),
        ):
            resp = client.get("/api/v1/exercises", cookies=_auth(user))

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_empty_list(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.list_exercises",
                return_value=([], 0),
            ),
        ):
            resp = client.get("/api/v1/exercises", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/exercises")
        assert resp.status_code == 401

    def test_search_param_passed_through(self, client: TestClient) -> None:
        user = _make_user()
        captured: dict = {}

        def fake_list(db, uid, *, search=None, **kwargs):  # type: ignore
            captured["search"] = search
            return [], 0

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.exercise_service.list_exercises", side_effect=fake_list),
        ):
            client.get("/api/v1/exercises?search=bench", cookies=_auth(user))

        assert captured["search"] == "bench"


# ── GET /api/v1/exercises/{id} ─────────────────────────────────────────────────


class TestGetExercise:
    def test_returns_exercise(self, client: TestClient) -> None:
        user = _make_user()
        exercise = _make_exercise(is_system=True)

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.get_exercise",
                return_value=_exercise_response(exercise),
            ),
        ):
            resp = client.get(f"/api/v1/exercises/{exercise.id}", cookies=_auth(user))

        assert resp.status_code == 200
        assert resp.json()["id"] == str(exercise.id)

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.get_exercise",
                side_effect=NotFoundError("Exercise not found"),
            ),
        ):
            resp = client.get(f"/api/v1/exercises/{uuid.uuid4()}", cookies=_auth(user))

        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(f"/api/v1/exercises/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── PATCH /api/v1/exercises/{id} ───────────────────────────────────────────────


class TestUpdateExercise:
    def test_updates_name(self, client: TestClient) -> None:
        user = _make_user()
        exercise = _make_exercise(user_id=user.id, name="Updated Name")

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.update_exercise",
                return_value=_exercise_response(exercise),
            ),
        ):
            resp = client.patch(
                f"/api/v1/exercises/{exercise.id}",
                json={"name": "Updated Name"},
                cookies=_auth(user),
            )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_system_exercise_returns_403(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import ForbiddenError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.update_exercise",
                side_effect=ForbiddenError("System exercises cannot be modified"),
            ),
        ):
            resp = client.patch(
                f"/api/v1/exercises/{uuid.uuid4()}",
                json={"name": "Hacked"},
                cookies=_auth(user),
            )

        assert resp.status_code == 403

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.patch(f"/api/v1/exercises/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 401


# ── DELETE /api/v1/exercises/{id} ─────────────────────────────────────────────


class TestDeleteExercise:
    def test_returns_204(self, client: TestClient) -> None:
        user = _make_user()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch("app.services.exercise_service.delete_exercise", return_value=None),
        ):
            resp = client.delete(
                f"/api/v1/exercises/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_system_exercise_returns_403(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import ForbiddenError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.delete_exercise",
                side_effect=ForbiddenError("System exercises cannot be deleted"),
            ),
        ):
            resp = client.delete(
                f"/api/v1/exercises/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 403

    def test_not_found_returns_404(self, client: TestClient) -> None:
        user = _make_user()
        from app.exceptions import NotFoundError

        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.exercise_service.delete_exercise",
                side_effect=NotFoundError("Exercise not found"),
            ),
        ):
            resp = client.delete(
                f"/api/v1/exercises/{uuid.uuid4()}",
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(f"/api/v1/exercises/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── Service unit tests ─────────────────────────────────────────────────────────


class TestExerciseService:
    def test_get_exercise_raises_not_found_for_other_users_custom(self) -> None:
        """A user cannot fetch another user's custom exercise."""
        from app.exceptions import NotFoundError
        from app.services import exercise_service

        owner_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        exercise = _make_exercise(user_id=owner_id, is_system=False)

        with (
            patch("app.repositories.exercise_repository.get_by_id", return_value=exercise),
            pytest.raises(NotFoundError),
        ):
            exercise_service.get_exercise(MagicMock(), exercise.id, requester_id)

    def test_update_exercise_raises_forbidden_for_system(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import exercise_service

        exercise = _make_exercise(is_system=True)
        with (
            patch("app.repositories.exercise_repository.get_by_id", return_value=exercise),
            pytest.raises(ForbiddenError),
        ):
            exercise_service.update_exercise(MagicMock(), exercise.id, uuid.uuid4(), name="New")

    def test_delete_exercise_raises_forbidden_for_other_user(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import exercise_service

        owner_id = uuid.uuid4()
        exercise = _make_exercise(user_id=owner_id, is_system=False)
        with (
            patch("app.repositories.exercise_repository.get_by_id", return_value=exercise),
            pytest.raises(ForbiddenError),
        ):
            exercise_service.delete_exercise(MagicMock(), exercise.id, uuid.uuid4())

    def test_delete_exercise_raises_forbidden_for_system(self) -> None:
        from app.exceptions import ForbiddenError
        from app.services import exercise_service

        exercise = _make_exercise(is_system=True)
        with (
            patch("app.repositories.exercise_repository.get_by_id", return_value=exercise),
            pytest.raises(ForbiddenError),
        ):
            exercise_service.delete_exercise(MagicMock(), exercise.id, uuid.uuid4())


# ── Seed helper tests ──────────────────────────────────────────────────────────


class TestSeedExercises:
    def test_skips_when_already_seeded(self) -> None:
        from app.seeds.exercises import seed_exercises

        db = MagicMock()
        with patch(
            "app.repositories.exercise_repository.system_exists",
            return_value=True,
        ):
            count = seed_exercises(db)
        assert count == 0
        db.commit.assert_not_called()

    def test_inserts_when_empty(self) -> None:
        from app.seeds.exercises import SYSTEM_EXERCISES, seed_exercises

        db = MagicMock()
        created: list = []

        def fake_create(db, *, name, **kwargs):  # type: ignore
            e = MagicMock()
            e.name = name
            created.append(e)
            return e

        with (
            patch(
                "app.repositories.exercise_repository.system_exists",
                return_value=False,
            ),
            patch(
                "app.repositories.exercise_repository.create",
                side_effect=fake_create,
            ),
        ):
            count = seed_exercises(db)

        assert count == len(SYSTEM_EXERCISES)
        db.commit.assert_called_once()


# ── Schema unit tests ──────────────────────────────────────────────────────────


class TestExerciseSchemas:
    def test_muscle_groups_string_parsed_to_list(self) -> None:
        from app.schemas.exercises import CreateExerciseRequest

        req = CreateExerciseRequest(
            name="Bench",
            category="strength",
            equipment="barbell",
            muscle_groups="chest,triceps, shoulders",  # type: ignore[arg-type]
        )
        assert req.muscle_groups == ["chest", "triceps", "shoulders"]

    def test_muscle_groups_list_accepted(self) -> None:
        from app.schemas.exercises import CreateExerciseRequest

        req = CreateExerciseRequest(
            name="Bench",
            category="strength",
            equipment="barbell",
            muscle_groups=["chest", "triceps"],
        )
        assert req.muscle_groups == ["chest", "triceps"]

    def test_name_stripped(self) -> None:
        from app.schemas.exercises import CreateExerciseRequest

        req = CreateExerciseRequest(
            name="  Bench Press  ",
            category="strength",
            equipment="barbell",
        )
        assert req.name == "Bench Press"

    def test_empty_muscle_groups_list_accepted(self) -> None:
        from app.schemas.exercises import CreateExerciseRequest

        req = CreateExerciseRequest(
            name="Plank",
            category="strength",
            equipment="bodyweight",
        )
        assert req.muscle_groups == []
