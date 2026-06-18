"""Tests for AI service layer and /api/v1/ai/* endpoints.

Unit tests:
  - estimate_cost()
  - parse_json_reply() — clean JSON, fenced JSON, invalid JSON
  - _build_prompt() — contains key data points
  - _rule_based_summary() — highlights / suggestions logic

Endpoint tests:
  POST /api/v1/ai/weekly-summary
    - Returns 200 with ai_available=False when AI is disabled (default)
    - Rule-based response contains expected fields
    - Requires auth (401 without token)
    - Patches weekly_summary_service so no real DB or AI calls needed

  POST /api/v1/ai/weekly-summary/accept
    - 204 on successful record
    - 404 when log_id not found
    - Requires auth
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.schemas.ai import WeeklyDataSnapshot, WeeklySummaryResponse
from app.services.ai_service import AIUnavailableError, estimate_cost, parse_json_reply
from app.services.weekly_summary_service import _build_prompt, _rule_based_summary

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    return u


def _auth(user: MagicMock) -> dict[str, str]:
    return {"fittrack_access": create_access_token(str(user.id))}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _snapshot(**kwargs: object) -> WeeklyDataSnapshot:
    defaults: dict[str, object] = {
        "week_start": date(2026, 6, 9),
        "week_end": date(2026, 6, 15),
        "weight_entries": 3,
        "workouts_completed": 2,
        "food_log_days": 5,
        "water_log_days": 4,
        "active_goals": 1,
    }
    defaults.update(kwargs)
    return WeeklyDataSnapshot(**defaults)  # type: ignore[arg-type]


def _summary_response(**kwargs: object) -> WeeklySummaryResponse:
    defaults: dict[str, object] = {
        "highlights": ["You completed 2 workouts this week."],
        "suggestions": ["Keep it up!"],
        "encouragement": "Great work!",
        "data_snapshot": _snapshot(),
        "ai_available": False,
    }
    defaults.update(kwargs)
    return WeeklySummaryResponse(**defaults)  # type: ignore[arg-type]


# ── estimate_cost ─────────────────────────────────────────────────────────────


class TestEstimateCost:
    def test_anthropic_basic(self) -> None:
        cost = estimate_cost("anthropic", 1_000_000, 1_000_000)
        assert cost is not None
        assert abs(cost - 4.80) < 0.001  # 0.80 + 4.00

    def test_openai_basic(self) -> None:
        cost = estimate_cost("openai", 1_000_000, 1_000_000)
        assert cost is not None
        assert abs(cost - 0.75) < 0.001  # 0.15 + 0.60

    def test_none_when_tokens_missing(self) -> None:
        assert estimate_cost("anthropic", None, None) is None
        assert estimate_cost("anthropic", 1000, None) is None

    def test_unknown_provider_returns_none(self) -> None:
        assert estimate_cost("unknown_provider", 1000, 500) is None

    def test_zero_tokens(self) -> None:
        cost = estimate_cost("anthropic", 0, 0)
        assert cost == 0.0


# ── parse_json_reply ──────────────────────────────────────────────────────────


class TestParseJsonReply:
    def test_clean_json(self) -> None:
        text = '{"highlights": ["a"], "suggestions": ["b"], "encouragement": "c"}'
        result = parse_json_reply(text)
        assert result["highlights"] == ["a"]
        assert result["encouragement"] == "c"

    def test_fenced_json(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_reply(text)
        assert result["key"] == "value"

    def test_plain_fenced_json(self) -> None:
        text = '```\n{"x": 1}\n```'
        result = parse_json_reply(text)
        assert result["x"] == 1

    def test_whitespace_around_json(self) -> None:
        text = '  \n  {"a": "b"}  \n  '
        result = parse_json_reply(text)
        assert result["a"] == "b"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_json_reply("not json at all")

    def test_json_array_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_json_reply("[1, 2, 3]")

    def test_empty_object(self) -> None:
        result = parse_json_reply("{}")
        assert result == {}


# ── _build_prompt ─────────────────────────────────────────────────────────────


class TestBuildPrompt:
    def test_contains_week_dates(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {})
        assert "2026-06-09" in prompt
        assert "2026-06-15" in prompt

    def test_contains_workout_count(self) -> None:
        snap = _snapshot(workouts_completed=3)
        prompt = _build_prompt(snap, {})
        assert "3" in prompt

    def test_contains_food_log_days(self) -> None:
        snap = _snapshot(food_log_days=6)
        prompt = _build_prompt(snap, {})
        assert "6 of 7" in prompt

    def test_includes_avg_weight_when_present(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {"avg_weight_kg": 75.5})
        assert "75.5" in prompt

    def test_omits_avg_weight_when_none(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {"avg_weight_kg": None})
        assert "Average weight" not in prompt

    def test_includes_waist_when_present(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {"waist_cm": 82.0})
        assert "82.0" in prompt

    def test_includes_json_schema_instruction(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {})
        assert "highlights" in prompt
        assert "suggestions" in prompt
        assert "encouragement" in prompt

    def test_safety_rules_present(self) -> None:
        snap = _snapshot()
        prompt = _build_prompt(snap, {})
        assert "encouraging" in prompt.lower() or "shame" in prompt.lower()


# ── _rule_based_summary ───────────────────────────────────────────────────────


class TestRuleBasedSummary:
    def test_active_week_highlights_workouts(self) -> None:
        snap = _snapshot(workouts_completed=3)
        result = _rule_based_summary(snap)
        assert any("3" in h or "workout" in h.lower() for h in result.highlights)

    def test_zero_workouts_adds_suggestion(self) -> None:
        snap = _snapshot(workouts_completed=0)
        result = _rule_based_summary(snap)
        assert any("workout" in s.lower() or "moving" in s.lower() for s in result.suggestions)

    def test_good_food_tracking_noted(self) -> None:
        snap = _snapshot(food_log_days=6)
        result = _rule_based_summary(snap)
        text = " ".join(result.highlights)
        assert "6" in text or "nutrition" in text.lower() or "food" in text.lower()

    def test_zero_weight_entries_suggests_logging(self) -> None:
        snap = _snapshot(weight_entries=0)
        result = _rule_based_summary(snap)
        all_text = " ".join(result.suggestions + result.highlights)
        assert "weight" in all_text.lower()

    def test_ai_available_is_false(self) -> None:
        snap = _snapshot()
        result = _rule_based_summary(snap)
        assert result.ai_available is False

    def test_always_has_encouragement(self) -> None:
        snap = _snapshot(workouts_completed=0, weight_entries=0, food_log_days=0)
        result = _rule_based_summary(snap)
        assert result.encouragement != ""

    def test_returns_weekly_summary_response(self) -> None:
        snap = _snapshot()
        result = _rule_based_summary(snap)
        assert isinstance(result, WeeklySummaryResponse)
        assert isinstance(result.highlights, list)
        assert isinstance(result.suggestions, list)


# ── POST /api/v1/ai/weekly-summary ───────────────────────────────────────────


class TestWeeklySummaryEndpoint:
    def test_returns_200_with_rule_based_fallback(
        self, client: TestClient
    ) -> None:
        user = _make_user()
        expected = _summary_response()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.get_weekly_summary",
                return_value=expected,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary",
                json={},
                cookies=_auth(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_available"] is False
        assert "highlights" in data
        assert "suggestions" in data
        assert "encouragement" in data
        assert "data_snapshot" in data

    def test_response_contains_data_snapshot(self, client: TestClient) -> None:
        user = _make_user()
        expected = _summary_response()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.get_weekly_summary",
                return_value=expected,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary",
                json={},
                cookies=_auth(user),
            )
        snapshot = resp.json()["data_snapshot"]
        assert "week_start" in snapshot
        assert "week_end" in snapshot
        assert "workouts_completed" in snapshot

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/api/v1/ai/weekly-summary", json={})
        assert resp.status_code == 401

    def test_ai_summary_with_provider_data(self, client: TestClient) -> None:
        user = _make_user()
        expected = _summary_response(
            ai_available=True,
            provider="anthropic",
            model_id="claude-3-5-haiku-20241022",
            prompt_version="weekly_v1",
            log_id=str(uuid.uuid4()),
        )
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.get_weekly_summary",
                return_value=expected,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary",
                json={},
                cookies=_auth(user),
            )
        data = resp.json()
        assert data["ai_available"] is True
        assert data["provider"] == "anthropic"
        assert data["prompt_version"] == "weekly_v1"
        assert data["log_id"] is not None

    def test_empty_request_body_is_valid(self, client: TestClient) -> None:
        """WeeklySummaryRequest has no required fields."""
        user = _make_user()
        expected = _summary_response()
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.get_weekly_summary",
                return_value=expected,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary",
                cookies=_auth(user),
            )
        assert resp.status_code == 200


# ── POST /api/v1/ai/weekly-summary/accept ────────────────────────────────────


class TestAcceptSummaryEndpoint:
    def test_returns_204_on_success(self, client: TestClient) -> None:
        user = _make_user()
        log_id = str(uuid.uuid4())
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.record_user_decision",
                return_value=True,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary/accept",
                json={"log_id": log_id, "accepted": True},
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_returns_204_on_dismiss(self, client: TestClient) -> None:
        user = _make_user()
        log_id = str(uuid.uuid4())
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.record_user_decision",
                return_value=True,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary/accept",
                json={"log_id": log_id, "accepted": False},
                cookies=_auth(user),
            )
        assert resp.status_code == 204

    def test_returns_404_when_log_not_found(self, client: TestClient) -> None:
        user = _make_user()
        log_id = str(uuid.uuid4())
        with (
            patch("app.dependencies.user_repository.get_user_by_id", return_value=user),
            patch(
                "app.services.weekly_summary_service.record_user_decision",
                return_value=False,
            ),
        ):
            resp = client.post(
                "/api/v1/ai/weekly-summary/accept",
                json={"log_id": log_id, "accepted": True},
                cookies=_auth(user),
            )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/ai/weekly-summary/accept",
            json={"log_id": str(uuid.uuid4()), "accepted": True},
        )
        assert resp.status_code == 401

    def test_missing_log_id_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/ai/weekly-summary/accept",
                json={"accepted": True},
                cookies=_auth(user),
            )
        assert resp.status_code == 422

    def test_missing_accepted_returns_422(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.dependencies.user_repository.get_user_by_id", return_value=user):
            resp = client.post(
                "/api/v1/ai/weekly-summary/accept",
                json={"log_id": str(uuid.uuid4())},
                cookies=_auth(user),
            )
        assert resp.status_code == 422


# ── AIUnavailableError integration ────────────────────────────────────────────


class TestAIUnavailableError:
    def test_is_exception(self) -> None:
        err = AIUnavailableError("test")
        assert isinstance(err, Exception)
        assert str(err) == "test"

    def test_can_be_caught_as_exception(self) -> None:
        try:
            raise AIUnavailableError("no ai")
        except Exception as exc:
            assert str(exc) == "no ai"
