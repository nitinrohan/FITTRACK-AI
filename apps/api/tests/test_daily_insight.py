"""Tests for the daily nutrition insight service (GET /api/v1/nutrition/insight).

Focus areas:
  - Comparisons are computed deterministically in code, not by the model.
  - No personal target set -> comparison shows target=None, never invented.
  - AI off / AI failure -> rule-based fallback, still useful, never raises.
  - Successful AI call -> parsed highlights/suggestions/encouragement.
  - Read-only: never calls db.commit for data mutation (insight itself
    doesn't create/update/delete any tracked record).
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.nutrition import DailyNutritionResponse, MacroTotals
from app.schemas.nutrition_target import NutritionTargetResponse
from app.services import daily_insight_service as svc
from app.services.ai_service import AIUnavailableError

TODAY = date.today()


def _user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _daily(calories: float = 635, protein: float = 59, carbs: float = 63, fat: float = 16.5, fiber: float = 7.5) -> DailyNutritionResponse:
    return DailyNutritionResponse(
        date=TODAY,
        meals=[],
        day_totals=MacroTotals(
            calories=calories, protein_g=protein, carbs_g=carbs, fat_g=fat, fiber_g=fiber
        ),
        water_logs=[],
        water_total_ml=0,
    )


def _targets(**overrides: float | None) -> NutritionTargetResponse:
    base = {
        "calorie_target_kcal": None,
        "protein_target_g": None,
        "carbs_target_g": None,
        "fat_target_g": None,
        "fiber_target_g": None,
    }
    base.update(overrides)
    return NutritionTargetResponse(is_set=any(v is not None for v in base.values()), updated_at=None, **base)


def _settings(enabled: bool = True) -> MagicMock:
    s = MagicMock()
    s.ai_enabled = enabled
    s.ai_provider = "ollama"
    s.ai_model = "llama3.1"
    return s


class TestComparisons:
    def test_no_target_set_yields_none_not_invented(self) -> None:
        comparisons = svc._build_comparisons(_daily().day_totals, _targets())
        protein = next(c for c in comparisons if c.metric == "protein")
        assert protein.target is None
        assert protein.percent_of_target is None
        assert protein.remaining is None
        assert protein.current == 59.0

    def test_percent_and_remaining_computed_against_real_target(self) -> None:
        comparisons = svc._build_comparisons(
            _daily(protein=59).day_totals, _targets(protein_target_g=150)
        )
        protein = next(c for c in comparisons if c.metric == "protein")
        assert protein.percent_of_target == round(59 / 150 * 100, 1)
        assert protein.remaining == round(150 - 59, 1)

    def test_over_target_gives_negative_remaining(self) -> None:
        comparisons = svc._build_comparisons(
            _daily(calories=2500).day_totals, _targets(calorie_target_kcal=2000)
        )
        cal = next(c for c in comparisons if c.metric == "calories")
        assert cal.remaining == -500.0


class TestAIUnavailable:
    def test_ai_disabled_uses_rule_based_fallback(self) -> None:
        db = MagicMock()
        with (
            patch.object(svc, "nutrition_service") as nut_mock,
            patch.object(svc, "nutrition_target_service") as target_mock,
        ):
            nut_mock.get_daily_nutrition.return_value = _daily()
            target_mock.get_targets.return_value = _targets(protein_target_g=150)
            with patch("app.config.get_settings", return_value=_settings(enabled=False)):
                result = svc.get_daily_insight(db, user_id=uuid.uuid4(), target_date=TODAY)
        assert result.ai_available is False
        assert result.highlights
        assert result.comparisons

    def test_ai_failure_degrades_to_rule_based(self) -> None:
        db = MagicMock()
        with (
            patch.object(svc, "nutrition_service") as nut_mock,
            patch.object(svc, "nutrition_target_service") as target_mock,
            patch.object(svc.ai_service, "call_ai", side_effect=AIUnavailableError("down")),
            patch("app.models.goal.Goal"),
        ):
            nut_mock.get_daily_nutrition.return_value = _daily()
            target_mock.get_targets.return_value = _targets()
            with patch("app.config.get_settings", return_value=_settings(enabled=True)):
                db.execute.return_value.all.return_value = []
                result = svc.get_daily_insight(db, user_id=uuid.uuid4(), target_date=TODAY)
        assert result.ai_available is False
        assert result.message is not None


class TestAISuccess:
    def test_parses_highlights_and_suggestions(self) -> None:
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        parsed = {
            "highlights": ["Protein is at 39% of your target so far."],
            "suggestions": ["Add a fiber-rich lunch."],
            "encouragement": "Good start today!",
        }
        with (
            patch.object(svc, "nutrition_service") as nut_mock,
            patch.object(svc, "nutrition_target_service") as target_mock,
            patch.object(
                svc.ai_service,
                "call_ai",
                return_value=("{}", "ollama", "llama3.1", 100, 50),
            ),
            patch.object(svc.ai_service, "parse_json_reply", return_value=parsed),
        ):
            nut_mock.get_daily_nutrition.return_value = _daily()
            target_mock.get_targets.return_value = _targets(protein_target_g=150)
            with patch("app.config.get_settings", return_value=_settings(enabled=True)):
                result = svc.get_daily_insight(db, user_id=uuid.uuid4(), target_date=TODAY)
        assert result.ai_available is True
        assert result.highlights == parsed["highlights"]
        assert result.encouragement == "Good start today!"
        assert result.log_id is not None


class TestEndpoint:
    def test_requires_auth(self, client: TestClient) -> None:
        r = client.get(f"/api/v1/nutrition/insight?date={TODAY}")
        assert r.status_code == 401

    def test_returns_preview(self, client: TestClient) -> None:
        from app.schemas.nutrition_insight import DailyInsightResponse

        user = _user()
        fake = DailyInsightResponse(
            date=TODAY,
            day_totals=_daily().day_totals,
            targets=_targets(),
            comparisons=[],
            meals_logged=[],
            meals_remaining=["breakfast", "lunch", "dinner", "snack"],
            ai_available=False,
            message="AI is off.",
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.daily_insight_service.get_daily_insight",
                return_value=fake,
            ),
        ):
            r = client.get(f"/api/v1/nutrition/insight?date={TODAY}", cookies=_auth(user))
        assert r.status_code == 200
        assert r.json()["ai_available"] is False
