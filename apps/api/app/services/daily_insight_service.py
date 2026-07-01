"""Daily nutrition insight service.

Orchestrates:
  1. Gathering today's (or any given date's) logged nutrition + the user's
     own configured targets (read-only).
  2. Computing deterministic comparisons (percent of target, remaining).
  3. Building a versioned prompt from ONLY that data.
  4. Calling the AI via ai_service.call_ai() for the narrative.
  5. Parsing the structured JSON reply.
  6. Logging the call to ai_usage_logs.
  7. Returning a DailyInsightResponse - this never mutates user data.

Fallback:
  When AI is unavailable, returns deterministic rule-based highlights so the
  comparisons are still useful without a model. The core tracker always
  works without AI.

Safety:
  - Comparisons are computed here, in code - the model never does the math.
  - Targets are only compared when the user has actually set them; we never
    invent a target on the user's behalf (per AI Assistant Rules).
  - General population nutrition reference ranges (e.g. typical fiber
    intake) may be mentioned to the model as generic educational context,
    clearly labelled as NOT the user's personal target.
  - This endpoint never diagnoses, guarantees outcomes, or recommends
    extreme restriction - see AI_ASSISTANT_RULES / Health and Safety Rules.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_log import AIUsageLog
from app.models.goal import Goal
from app.schemas.nutrition import MEAL_TYPE_ORDER, DailyNutritionResponse, MacroTotals
from app.schemas.nutrition_insight import DailyInsightResponse, MacroComparison
from app.schemas.nutrition_target import NutritionTargetResponse
from app.services import ai_service, nutrition_service, nutrition_target_service
from app.services.ai_service import AIUnavailableError, estimate_cost

PROMPT_VERSION = "daily-insight-v1"
_FEATURE = "daily_nutrition_insight"

# Meal slots that count as "a meal" for the remaining-meals suggestion list.
# "other" is a catch-all bucket, not a distinct meal occasion.
_MEAL_SLOTS = [m for m in MEAL_TYPE_ORDER if m != "other"]

# Widely-cited general adult reference ranges - NOT personalised, only used
# as generic educational context when the user has not set their own target.
_GENERAL_FIBER_GUIDANCE = "roughly 25-38 g of fiber a day for most adults"
_GENERAL_FAT_GUIDANCE = "roughly 20-35% of daily calories from fat for most adults"

_METRICS: list[tuple[str, str, str]] = [
    # (metric key, label, unit)
    ("calories", "Calories", "kcal"),
    ("protein", "Protein", "g"),
    ("carbs", "Carbs", "g"),
    ("fat", "Fat", "g"),
    ("fiber", "Fiber", "g"),
]


# ── Comparisons (deterministic) ───────────────────────────────────────────────


def _current_value(totals: MacroTotals, metric: str) -> float:
    return {
        "calories": totals.calories,
        "protein": totals.protein_g,
        "carbs": totals.carbs_g,
        "fat": totals.fat_g,
        "fiber": totals.fiber_g,
    }[metric]


def _target_value(targets: NutritionTargetResponse, metric: str) -> float | None:
    return {
        "calories": targets.calorie_target_kcal,
        "protein": targets.protein_target_g,
        "carbs": targets.carbs_target_g,
        "fat": targets.fat_target_g,
        "fiber": targets.fiber_target_g,
    }[metric]


def _build_comparisons(
    totals: MacroTotals, targets: NutritionTargetResponse
) -> list[MacroComparison]:
    comparisons: list[MacroComparison] = []
    for metric, label, unit in _METRICS:
        current = round(_current_value(totals, metric), 1)
        target = _target_value(targets, metric)
        percent = round((current / target) * 100, 1) if target and target > 0 else None
        remaining = round(target - current, 1) if target is not None else None
        comparisons.append(
            MacroComparison(
                metric=metric,
                label=label,
                unit=unit,
                current=current,
                target=target,
                percent_of_target=percent,
                remaining=remaining,
            )
        )
    return comparisons


def _meals_logged_remaining(daily: DailyNutritionResponse) -> tuple[list[str], list[str]]:
    logged = {section.meal_type for section in daily.meals if section.entries}
    remaining: list[str] = [str(m) for m in _MEAL_SLOTS if m not in logged]
    logged_ordered: list[str] = [str(m) for m in _MEAL_SLOTS if m in logged]
    return logged_ordered, remaining


# ── Nutrition-relevant goal framing (existence/type only, never invented values) ──


def _nutrition_relevant_goal_types(db: Session, user_id: uuid.UUID) -> list[str]:
    stmt = select(Goal.goal_type).where(
        Goal.user_id == user_id,
        Goal.status == "active",
        Goal.goal_type.in_(("weight_loss", "weight_gain", "body_fat", "strength", "endurance")),
    )
    return [row[0] for row in db.execute(stmt).all()]


# ── Prompt ────────────────────────────────────────────────────────────────────


def _build_prompt(
    *,
    target_date: date,
    comparisons: list[MacroComparison],
    meals_logged: list[str],
    meals_remaining: list[str],
    goal_types: list[str],
) -> str:
    lines = [f"Date: {target_date.isoformat()}"]
    for c in comparisons:
        if c.target is not None:
            lines.append(
                f"  {c.label}: {c.current} {c.unit} logged so far, "
                f"target {c.target} {c.unit} "
                f"({c.percent_of_target}% of target, {c.remaining} {c.unit} remaining)"
            )
        else:
            lines.append(f"  {c.label}: {c.current} {c.unit} logged so far, no personal target set")

    lines.append(f"Meals already logged today: {', '.join(meals_logged) or 'none yet'}")
    lines.append(f"Meals not yet logged today: {', '.join(meals_remaining) or 'none - all logged'}")
    if goal_types:
        lines.append(f"User's active fitness goal types: {', '.join(goal_types)}")

    data_block = "\n".join(lines)

    return f"""You are a supportive nutrition assistant reviewing a user's food log for today.

Data logged so far today (this is everything you may reference - do not invent any other numbers):
{data_block}

General population reference (NOT this user's personal target - only mention
if relevant, and always label it as a general guideline, never as their goal):
  Fiber: {_GENERAL_FIBER_GUIDANCE}
  Fat: {_GENERAL_FAT_GUIDANCE}

Rules:
- Use ONLY the numbers given above. Never invent foods, quantities, or targets.
- If a personal target is not set for a metric, say so plainly instead of guessing one.
- Be encouraging and practical, never guilt-inducing or alarmist.
- Never recommend extreme calorie restriction, skipping meals, or excessive exercise.
- If meals remain unlogged today, suggest general, balanced ideas (protein + vegetables +
  a healthy fat/carb source) for those remaining meal slots - not exact recipes or medical advice.
- This is not medical or dietitian advice; do not present it as such.

Respond with ONLY a JSON object in this exact shape (no markdown, no extra text):
{{
  "highlights": ["observation 1", "observation 2"],
  "suggestions": ["suggestion for a remaining meal or macro gap", "..."],
  "encouragement": "One warm, practical sentence."
}}

Include 2-4 highlights and 1-3 suggestions."""


# ── Rule-based fallback ───────────────────────────────────────────────────────


def _rule_based_insight(comparisons: list[MacroComparison], meals_remaining: list[str]) -> tuple[list[str], list[str], str]:
    highlights: list[str] = []
    suggestions: list[str] = []

    for c in comparisons:
        if c.target is None:
            continue
        if c.percent_of_target is not None:
            highlights.append(
                f"{c.label}: {c.current} of {c.target} {c.unit} so far ({c.percent_of_target}% of target)."
            )
        if c.remaining is not None and c.remaining > 0 and c.metric in ("protein", "fiber"):
            suggestions.append(f"You have about {c.remaining} {c.unit} of {c.label.lower()} left to reach your target.")

    if not highlights:
        highlights.append("Logged totals are shown above - set a nutrition target in Settings to see comparisons.")

    if meals_remaining:
        suggestions.append(
            f"Still to log today: {', '.join(meals_remaining)}. "
            "A balanced plate with protein, vegetables, and a healthy fat or carb source works well."
        )

    if not suggestions:
        suggestions.append("Keep logging consistently - it's the best way to spot patterns over time.")

    return highlights[:4], suggestions[:3], "Every day logged is useful data - keep going."


# ── Log helper ────────────────────────────────────────────────────────────────


def _write_log(
    db: Session,
    *,
    user_id: uuid.UUID,
    provider: str,
    model_id: str,
    input_tokens: int | None,
    output_tokens: int | None,
    success: bool,
    error_message: str | None,
    response_json: str | None,
) -> AIUsageLog:
    entry = AIUsageLog(
        user_id=user_id,
        feature=_FEATURE,
        provider=provider,
        model_id=model_id,
        prompt_version=PROMPT_VERSION,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_cost(provider, input_tokens, output_tokens),
        success=success,
        error_message=error_message,
        response_json=response_json,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ── Public API ────────────────────────────────────────────────────────────────


def get_daily_insight(
    db: Session, *, user_id: uuid.UUID, target_date: date
) -> DailyInsightResponse:
    """Return a read-only nutrition insight for the given date. Never raises."""
    daily = nutrition_service.get_daily_nutrition(db, user_id, target_date)
    targets = nutrition_target_service.get_targets(db, user_id)
    comparisons = _build_comparisons(daily.day_totals, targets)
    meals_logged, meals_remaining = _meals_logged_remaining(daily)

    from app.config import get_settings

    settings = get_settings()
    if not settings.ai_enabled:
        highlights, suggestions, encouragement = _rule_based_insight(comparisons, meals_remaining)
        return DailyInsightResponse(
            date=target_date,
            day_totals=daily.day_totals,
            targets=targets,
            comparisons=comparisons,
            meals_logged=meals_logged,
            meals_remaining=meals_remaining,
            ai_available=False,
            highlights=highlights,
            suggestions=suggestions,
            encouragement=encouragement,
            message="AI is off - showing rule-based observations from your logged data.",
            generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    provider: str = settings.ai_provider
    model_id: str = settings.ai_model
    goal_types = _nutrition_relevant_goal_types(db, user_id)

    try:
        prompt = _build_prompt(
            target_date=target_date,
            comparisons=comparisons,
            meals_logged=meals_logged,
            meals_remaining=meals_remaining,
            goal_types=goal_types,
        )
        text, provider, model_id, inp_tok, out_tok = ai_service.call_ai(prompt, max_tokens=600)
        parsed = ai_service.parse_json_reply(text)

        highlights = [str(h) for h in parsed.get("highlights", []) if h][:4]
        suggestions = [str(s) for s in parsed.get("suggestions", []) if s][:3]
        encouragement = str(parsed.get("encouragement", "")).strip()

        if not highlights and not encouragement:
            raise ValueError("AI returned empty insight content.")

        log = _write_log(
            db,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            input_tokens=inp_tok,
            output_tokens=out_tok,
            success=True,
            error_message=None,
            response_json=json.dumps(parsed),
        )

        return DailyInsightResponse(
            date=target_date,
            day_totals=daily.day_totals,
            targets=targets,
            comparisons=comparisons,
            meals_logged=meals_logged,
            meals_remaining=meals_remaining,
            ai_available=True,
            highlights=highlights,
            suggestions=suggestions,
            encouragement=encouragement,
            provider=provider,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            log_id=str(log.id),
            generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    except (AIUnavailableError, ValueError, KeyError) as exc:
        try:
            _write_log(
                db,
                user_id=user_id,
                provider=provider,
                model_id=model_id,
                input_tokens=None,
                output_tokens=None,
                success=False,
                error_message=str(exc)[:500],
                response_json=None,
            )
        except Exception:
            db.rollback()

        highlights, suggestions, encouragement = _rule_based_insight(comparisons, meals_remaining)
        return DailyInsightResponse(
            date=target_date,
            day_totals=daily.day_totals,
            targets=targets,
            comparisons=comparisons,
            meals_logged=meals_logged,
            meals_remaining=meals_remaining,
            ai_available=False,
            highlights=highlights,
            suggestions=suggestions,
            encouragement=encouragement,
            message="Couldn't generate an AI insight right now - showing rule-based observations instead.",
            generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
