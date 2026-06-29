"""Tests for the AI macro-estimation service and endpoint.

Focus areas:
  - Fallback when AI is disabled / fails (never raises; ai_available False).
  - Successful parse → deterministic portion math (computed in code, not AI).
  - Defensive coercion of malformed / negative / missing model output.
  - Endpoint: auth required, validation, preview shape.

The AI provider call is always mocked - no network and no real model.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services import macro_estimation_service as svc
from app.services.ai_service import AIUnavailableError


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _settings(enabled: bool = True) -> MagicMock:
    s = MagicMock()
    s.ai_enabled = enabled
    s.ai_provider = "ollama"
    s.ai_model = "llama3.1"
    return s


# ── Fallback behaviour ──────────────────────────────────────────────────────────


class TestFallback:
    def test_ai_disabled_returns_unavailable(self) -> None:
        db = MagicMock()
        with patch.object(svc, "get_settings", return_value=_settings(enabled=False)):
            result = svc.estimate_macros(db, user_id=uuid.uuid4(), description="eggs")
        assert result.ai_available is False
        assert result.message is not None
        assert result.calories_per_100g is None

    def test_provider_failure_degrades_gracefully(self) -> None:
        db = MagicMock()
        with (
            patch.object(svc, "get_settings", return_value=_settings()),
            patch.object(
                svc.ai_service, "call_ai", side_effect=AIUnavailableError("down")
            ),
            patch.object(svc, "_write_log"),
        ):
            result = svc.estimate_macros(db, user_id=uuid.uuid4(), description="eggs")
        assert result.ai_available is False
        assert result.is_estimate is True

    def test_all_zero_macros_treated_as_failure(self) -> None:
        db = MagicMock()
        payload = {
            "name": "Water",
            "serving_size_g": 250,
            "calories_per_100g": 0,
            "protein_per_100g": 0,
            "carbs_per_100g": 0,
            "fat_per_100g": 0,
        }
        with (
            patch.object(svc, "get_settings", return_value=_settings()),
            patch.object(
                svc.ai_service,
                "call_ai",
                return_value=("{}", "ollama", "llama3.1", 10, 5),
            ),
            patch.object(svc.ai_service, "parse_json_reply", return_value=payload),
            patch.object(svc, "_write_log"),
        ):
            result = svc.estimate_macros(db, user_id=uuid.uuid4(), description="water")
        assert result.ai_available is False


# ── Successful estimate ─────────────────────────────────────────────────────────


class TestSuccessfulEstimate:
    def _run(self, payload: dict[str, object]) -> object:
        db = MagicMock()
        log = MagicMock()
        log.id = uuid.uuid4()
        with (
            patch.object(svc, "get_settings", return_value=_settings()),
            patch.object(
                svc.ai_service,
                "call_ai",
                return_value=("{}", "ollama", "llama3.1", 20, 8),
            ),
            patch.object(svc.ai_service, "parse_json_reply", return_value=payload),
            patch.object(svc, "_write_log", return_value=log),
        ):
            return svc.estimate_macros(db, user_id=uuid.uuid4(), description="x")

    def test_portion_math_is_deterministic(self) -> None:
        # 200 g serving at 150 kcal / 100 g => 300 kcal for the portion.
        result = self._run(
            {
                "name": "Oatmeal",
                "serving_size_g": 200,
                "serving_unit": "bowl",
                "calories_per_100g": 150,
                "protein_per_100g": 5,
                "carbs_per_100g": 27,
                "fat_per_100g": 3,
                "confidence": "medium",
            }
        )
        assert result.ai_available is True
        assert result.calories_per_100g == 150
        assert result.portion is not None
        assert result.portion.grams == 200
        assert result.portion.calories_kcal == 300.0
        assert result.portion.protein_g == 10.0
        assert result.confidence == "medium"
        assert result.log_id is not None

    def test_missing_serving_defaults_to_100g(self) -> None:
        result = self._run(
            {"name": "Cheese", "calories_per_100g": 400, "protein_per_100g": 25}
        )
        assert result.serving_size_g == 100.0
        assert result.portion.calories_kcal == 400.0

    def test_negative_and_bad_values_coerced(self) -> None:
        result = self._run(
            {
                "name": "Mystery",
                "serving_size_g": -5,
                "calories_per_100g": -10,
                "protein_per_100g": "abc",
                "carbs_per_100g": 12,
                "fat_per_100g": None,
                "confidence": "wild",
            }
        )
        assert result.calories_per_100g == 0.0  # negative clamped
        assert result.protein_per_100g == 0.0  # non-numeric -> 0
        assert result.serving_size_g == 100.0  # invalid serving -> default
        assert result.confidence == "low"  # invalid confidence -> low


# ── Endpoint ─────────────────────────────────────────────────────────────────────


class TestEndpoint:
    def test_requires_auth(self, client: TestClient) -> None:
        r = client.post("/api/v1/nutrition/estimate-macros", json={"description": "egg"})
        assert r.status_code == 401

    def test_blank_description_422(self, client: TestClient) -> None:
        user = _user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            r = client.post(
                "/api/v1/nutrition/estimate-macros",
                json={"description": ""},
                cookies=_auth(user),
            )
        assert r.status_code == 422

    def test_returns_preview(self, client: TestClient) -> None:
        from app.schemas.ai import MacroEstimateResponse

        user = _user()
        preview = MacroEstimateResponse(
            ai_available=False, message="off"
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.macro_estimation_service.estimate_macros",
                return_value=preview,
            ),
        ):
            r = client.post(
                "/api/v1/nutrition/estimate-macros",
                json={"description": "two eggs"},
                cookies=_auth(user),
            )
        assert r.status_code == 200
        assert r.json()["is_estimate"] is True
