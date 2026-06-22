"""Weekly summary service.

Orchestrates:
  1. Gathering last-7-days data for the user (read-only).
  2. Building a structured prompt (versioned).
  3. Calling the AI via ai_service.call_ai().
  4. Parsing the structured JSON reply.
  5. Logging the call to ai_usage_logs.
  6. Returning a WeeklySummaryResponse (never mutates user data).

Fallback:
  When AI is unavailable, returns a response with ai_available=False and
  rule-based highlights derived from the data snapshot.
  The core tracker always works without AI.

Safety:
  - We pass only aggregated counts and averages to the AI, never raw food
    names, personal notes, or journal text.  This limits data exposure.
  - The AI is instructed to only reference the numbers it was given.
  - The user must explicitly accept the summary before any action is taken.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.ai_log import AIUsageLog
from app.repositories import measurement_repository, weight_repository
from app.schemas.ai import WeeklyDataSnapshot, WeeklySummaryResponse
from app.services import ai_service
from app.services.ai_service import AIUnavailableError, estimate_cost

# ── Prompt version ────────────────────────────────────────────────────────────

PROMPT_VERSION = "weekly_v1"

# ── Context gathering ─────────────────────────────────────────────────────────


def _gather_snapshot(
    db: Session, user_id: uuid.UUID
) -> tuple[WeeklyDataSnapshot, dict[str, object]]:
    """Collect last-7-days aggregated stats.

    Returns (snapshot, extended_context_dict).
    extended_context_dict has extra fields (averages) used in the prompt
    but not all surfaced in the response schema.
    """
    today = date.today()
    week_start = today - timedelta(days=6)

    # Weight
    weight_entries, _ = weight_repository.list_entries_for_user(
        db, user_id, date_from=week_start, date_to=today, offset=0, limit=100
    )
    weight_count = len(weight_entries)
    avg_weight_kg: float | None = None
    if weight_count > 0:
        avg_weight_kg = round(sum(e.weight_kg for e in weight_entries) / weight_count, 1)

    # Workouts (completed only, started in the window)
    from sqlalchemy import select

    from app.models.workout import Workout

    stmt = select(Workout).where(
        Workout.user_id == user_id,
        Workout.completed_at.isnot(None),
        Workout.started_at >= week_start.isoformat(),
    )
    workouts = list(db.execute(stmt).scalars())
    workout_count = len(workouts)

    # Total workout volume (sum of weight_kg * reps across all sets)
    total_volume_kg: float = 0.0
    for w in workouts:
        for ex in w.exercises:
            for s in ex.sets:
                if s.weight_kg is not None and s.reps is not None:
                    total_volume_kg += s.weight_kg * s.reps

    # Nutrition — count distinct days with food log entries in the window
    from sqlalchemy import func

    from app.models.nutrition import FoodLog, WaterLog

    food_day_stmt = select(func.count(func.distinct(FoodLog.logged_date))).where(
        FoodLog.user_id == user_id,
        FoodLog.logged_date >= week_start,
        FoodLog.logged_date <= today,
    )
    food_log_days: int = db.execute(food_day_stmt).scalar_one() or 0

    water_day_stmt = select(func.count(func.distinct(WaterLog.logged_date))).where(
        WaterLog.user_id == user_id,
        WaterLog.logged_date >= week_start,
        WaterLog.logged_date <= today,
    )
    water_log_days: int = db.execute(water_day_stmt).scalar_one() or 0

    # Active goals
    from app.models.goal import Goal

    goal_stmt = select(func.count()).select_from(
        select(Goal)
        .where(
            Goal.user_id == user_id,
            Goal.status == "active",
        )
        .subquery()
    )
    active_goals: int = db.execute(goal_stmt).scalar_one() or 0

    # Latest measurement
    latest_meas = measurement_repository.get_latest_measurement(db, user_id)
    waist_cm = latest_meas.waist_cm if latest_meas else None

    snapshot = WeeklyDataSnapshot(
        week_start=week_start,
        week_end=today,
        weight_entries=weight_count,
        workouts_completed=workout_count,
        food_log_days=food_log_days,
        water_log_days=water_log_days,
        active_goals=active_goals,
    )
    extended: dict[str, object] = {
        "avg_weight_kg": avg_weight_kg,
        "total_workout_volume_kg": round(total_volume_kg, 1),
        "waist_cm": waist_cm,
    }
    return snapshot, extended


# ── Prompt builder ────────────────────────────────────────────────────────────


def _build_prompt(snapshot: WeeklyDataSnapshot, extra: dict[str, object]) -> str:
    """Build the structured prompt for the weekly summary.

    We instruct the model to respond with a JSON object only.
    No markdown, no preamble.
    """
    lines = [
        f"Week: {snapshot.week_start} to {snapshot.week_end}",
        f"Weight entries logged: {snapshot.weight_entries}",
    ]
    if extra.get("avg_weight_kg") is not None:
        lines.append(f"Average weight this week: {extra['avg_weight_kg']} kg")
    lines.append(f"Workouts completed: {snapshot.workouts_completed}")
    if extra.get("total_workout_volume_kg", 0):
        lines.append(f"Total training volume: {extra['total_workout_volume_kg']} kg")
    lines.append(f"Days with food logged: {snapshot.food_log_days} of 7")
    lines.append(f"Days with water logged: {snapshot.water_log_days} of 7")
    lines.append(f"Active fitness goals: {snapshot.active_goals}")
    if extra.get("waist_cm") is not None:
        lines.append(f"Most recent waist measurement: {extra['waist_cm']} cm")

    data_block = "\n".join(f"  {line}" for line in lines)

    return f"""You are a supportive fitness coach assistant reviewing a user's weekly fitness data.

Data for the past 7 days:
{data_block}

Based ONLY on the numbers above, write a brief weekly summary.
Rules:
- Do not invent facts or numbers not listed above.
- Be encouraging, not guilt-inducing.
- Never suggest skipping meals, extreme restriction, or overtraining.
- If data is sparse (e.g. 0 workouts), acknowledge it without shaming.
- Keep language simple, warm, and practical.

Respond with ONLY a JSON object in this exact shape (no markdown, no extra text):
{{
  "highlights": ["observation 1", "observation 2"],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "encouragement": "One warm motivating sentence."
}}

Include 2-4 highlights and 1-3 suggestions."""


# ── Rule-based fallback ───────────────────────────────────────────────────────


def _rule_based_summary(snapshot: WeeklyDataSnapshot) -> WeeklySummaryResponse:
    """Generate a minimal summary without AI when the provider is unavailable."""
    highlights: list[str] = []
    suggestions: list[str] = []

    if snapshot.workouts_completed > 0:
        highlights.append(
            f"You completed {snapshot.workouts_completed} workout"
            f"{'s' if snapshot.workouts_completed != 1 else ''} this week."
        )
    else:
        highlights.append("No workouts were logged this week.")
        suggestions.append("Try scheduling one short workout to get moving.")

    if snapshot.weight_entries > 0:
        highlights.append(
            f"You logged your weight {snapshot.weight_entries} "
            f"time{'s' if snapshot.weight_entries != 1 else ''} this week."
        )
    else:
        suggestions.append("Logging your weight regularly helps spot trends early.")

    if snapshot.food_log_days >= 5:
        highlights.append(
            f"You tracked nutrition on {snapshot.food_log_days} of 7 days — great consistency."
        )
    elif snapshot.food_log_days > 0:
        highlights.append(
            f"You tracked food on {snapshot.food_log_days} day"
            f"{'s' if snapshot.food_log_days != 1 else ''} this week."
        )
        suggestions.append("Aim to log at least 5 days this week to build the habit.")

    if snapshot.water_log_days == 0:
        suggestions.append("Try logging your water intake — even rough estimates help.")

    if not suggestions:
        suggestions.append("Keep up the consistency — small steps add up over time.")

    return WeeklySummaryResponse(
        highlights=highlights,
        suggestions=suggestions,
        encouragement="Every week is a fresh start — keep going!",
        data_snapshot=snapshot,
        ai_available=False,
    )


# ── Log helper ────────────────────────────────────────────────────────────────


def _write_log(
    db: Session,
    *,
    user_id: uuid.UUID,
    provider: str,
    model_id: str,
    prompt_version: str,
    input_tokens: int | None,
    output_tokens: int | None,
    success: bool,
    error_message: str | None,
    response_json: str | None,
) -> AIUsageLog:
    entry = AIUsageLog(
        user_id=user_id,
        feature="weekly_summary",
        provider=provider,
        model_id=model_id,
        prompt_version=prompt_version,
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


def get_weekly_summary(db: Session, *, user_id: uuid.UUID) -> WeeklySummaryResponse:
    """Generate a weekly summary for the user.

    Tries the configured AI provider first; falls back to rule-based output
    if AI is unavailable or the call fails.  Never raises — always returns
    a usable response.
    """
    snapshot, extended = _gather_snapshot(db, user_id)

    try:
        prompt = _build_prompt(snapshot, extended)
        text, provider, model_id, inp_tok, out_tok = ai_service.call_ai(prompt, max_tokens=512)

        parsed = ai_service.parse_json_reply(text)

        highlights: list[str] = [str(h) for h in parsed.get("highlights", []) if h][:4]
        suggestions: list[str] = [str(s) for s in parsed.get("suggestions", []) if s][:3]
        encouragement: str = str(parsed.get("encouragement", "")).strip()

        if not highlights and not encouragement:
            raise ValueError("AI returned empty summary content.")

        log = _write_log(
            db,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            input_tokens=inp_tok,
            output_tokens=out_tok,
            success=True,
            error_message=None,
            response_json=json.dumps(parsed),
        )

        return WeeklySummaryResponse(
            highlights=highlights,
            suggestions=suggestions,
            encouragement=encouragement,
            data_snapshot=snapshot,
            ai_available=True,
            provider=provider,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            log_id=str(log.id),
        )

    except (AIUnavailableError, ValueError, KeyError) as exc:
        # Log the failure if AI was actually attempted
        settings_provider = _get_configured_provider()
        if settings_provider != "none":
            _write_log(
                db,
                user_id=user_id,
                provider=settings_provider,
                model_id=_get_configured_model(),
                prompt_version=PROMPT_VERSION,
                input_tokens=None,
                output_tokens=None,
                success=False,
                error_message=str(exc),
                response_json=None,
            )

        return _rule_based_summary(snapshot)


def record_user_decision(db: Session, *, log_id: str, accepted: bool) -> bool:
    """Record whether the user accepted or dismissed a summary.

    Returns True if the log entry was found and updated, False otherwise.
    """
    try:
        entry_uuid = uuid.UUID(log_id)
    except ValueError:
        return False

    log = db.get(AIUsageLog, entry_uuid)
    if log is None:
        return False

    log.accepted = accepted
    db.commit()
    return True


def _get_configured_provider() -> str:
    from app.config import get_settings

    return get_settings().ai_provider


def _get_configured_model() -> str:
    from app.config import get_settings

    return get_settings().ai_model
