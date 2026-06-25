"""AI macro-estimation service.

Turns a free-text food/drink description (e.g. "two boiled eggs and a slice
of wholegrain toast") into a structured macro ESTIMATE.

Safety / architecture rules honoured here:
- The result is always an estimate, never presented as exact, and is never
  saved automatically — the endpoint returns a preview the user approves.
- The language model only parses text into per-100g figures; the portion
  totals are computed by deterministic Python, not the model.
- When AI is unavailable or the call fails, we degrade gracefully: the user
  is told to enter macros manually. This function never raises.
- Every call is logged (provider, model, prompt version, tokens, cost,
  success) so usage and the user's later accept/reject can be tracked.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ai_log import AIUsageLog
from app.schemas.ai import MacroEstimateResponse, MacroPortion
from app.services import ai_service
from app.services.ai_service import AIUnavailableError, estimate_cost

PROMPT_VERSION = "macro-est-v1"

_FEATURE = "macro_estimate"
_CONFIDENCE = {"low", "medium", "high"}


# ── Prompt ──────────────────────────────────────────────────────────────────────


def _build_prompt(description: str) -> str:
    return (
        "You are a nutrition assistant. Estimate the nutrition for the food or "
        "drink described below. Respond with ONLY a JSON object, no prose.\n\n"
        "Return these keys:\n"
        '  "name": short food name (string)\n'
        '  "serving_size_g": typical grams for the described portion (number)\n'
        '  "serving_unit": e.g. "serving", "cup", "egg" (string)\n'
        '  "calories_per_100g": number\n'
        '  "protein_per_100g": grams (number)\n'
        '  "carbs_per_100g": grams (number)\n'
        '  "fat_per_100g": grams (number)\n'
        '  "confidence": "low" | "medium" | "high"\n\n'
        "All nutrition values must be PER 100 GRAMS. Give your best estimate "
        "even if unsure (use low confidence). Do not refuse.\n\n"
        f"Food description: {description}"
    )


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _num(value: object, *, default: float = 0.0) -> float:
    try:
        n = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(0.0, round(n, 2))


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


def _unavailable(message: str) -> MacroEstimateResponse:
    return MacroEstimateResponse(ai_available=False, message=message)


# ── Public API ───────────────────────────────────────────────────────────────────


def estimate_macros(
    db: Session, *, user_id: uuid.UUID, description: str
) -> MacroEstimateResponse:
    """Estimate macros for a food description. Never raises."""
    settings = get_settings()
    if not settings.ai_enabled:
        return _unavailable(
            "AI macro estimation is off. You can still enter the values manually."
        )

    provider: str = settings.ai_provider
    model_id: str = settings.ai_model

    try:
        prompt = _build_prompt(description)
        text, provider, model_id, inp_tok, out_tok = ai_service.call_ai(
            prompt, max_tokens=300
        )
        parsed = ai_service.parse_json_reply(text)

        name = str(parsed.get("name") or "").strip() or description[:100]
        per100_cal = _num(parsed.get("calories_per_100g"))
        per100_pro = _num(parsed.get("protein_per_100g"))
        per100_carb = _num(parsed.get("carbs_per_100g"))
        per100_fat = _num(parsed.get("fat_per_100g"))

        serving = _num(parsed.get("serving_size_g"))
        if serving <= 0:
            serving = 100.0
        serving_unit = str(parsed.get("serving_unit") or "serving").strip()[:50]

        confidence = str(parsed.get("confidence") or "low").lower().strip()
        if confidence not in _CONFIDENCE:
            confidence = "low"

        if per100_cal == 0 and per100_pro == 0 and per100_carb == 0 and per100_fat == 0:
            raise ValueError("AI returned all-zero macros.")

        # Portion totals — computed here, not by the model.
        factor = serving / 100.0
        portion = MacroPortion(
            grams=serving,
            calories_kcal=round(per100_cal * factor, 1),
            protein_g=round(per100_pro * factor, 1),
            carbs_g=round(per100_carb * factor, 1),
            fat_g=round(per100_fat * factor, 1),
        )

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

        return MacroEstimateResponse(
            ai_available=True,
            name=name,
            serving_size_g=serving,
            serving_unit=serving_unit,
            calories_per_100g=per100_cal,
            protein_per_100g=per100_pro,
            carbs_per_100g=per100_carb,
            fat_per_100g=per100_fat,
            portion=portion,
            confidence=confidence,
            provider=provider,
            model_id=model_id,
            prompt_version=PROMPT_VERSION,
            log_id=str(log.id),
        )

    except (AIUnavailableError, ValueError, KeyError, TypeError) as exc:
        # Log the failure (best-effort) and degrade gracefully.
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
            # Logging must never break the user-facing response.
            db.rollback()
        return _unavailable(
            "Couldn't estimate macros right now. You can enter the values manually."
        )
