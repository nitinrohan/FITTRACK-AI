"""Provider-independent AI service layer.

Design:
  - All external HTTP calls go through _call_anthropic() or _call_openai().
  - Both return a plain string (the model's text reply).
  - The caller is responsible for parsing and validating that string.
  - When AI is unavailable (provider="none", missing key, or HTTP error)
    we raise AIUnavailableError so the caller can fall back gracefully.
  - We never log raw prompts or responses in application logs because they
    may contain the user's personal health data.  The database log is
    controlled by the user's privacy settings (future work).

Prompt versioning:
  - Every prompt template has a version string (e.g. "weekly_v1").
  - Changing a prompt increments the version so we can correlate logs.

Cost estimation:
  - Prices are hard-coded at write time and will need updating.
  - Anthropic claude-3-5-haiku: $0.80 / 1M input tokens, $4.00 / 1M output.
  - OpenAI gpt-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Custom exception ──────────────────────────────────────────────────────────


class AIUnavailableError(Exception):
    """Raised when the AI provider is not configured or the call failed."""


# ── Token-cost estimation ─────────────────────────────────────────────────────

_COST_TABLE: dict[str, dict[str, float]] = {
    # provider → {"input": cost_per_1m_tokens, "output": cost_per_1m_tokens}
    "anthropic": {"input": 0.80, "output": 4.00},
    "openai": {"input": 0.15, "output": 0.60},
}


def estimate_cost(
    provider: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Return estimated USD cost or None if token counts unavailable."""
    table = _COST_TABLE.get(provider)
    if table is None or input_tokens is None or output_tokens is None:
        return None
    return round(
        (input_tokens * table["input"] + output_tokens * table["output"]) / 1_000_000,
        6,
    )


# ── Per-provider callers ──────────────────────────────────────────────────────


def _call_anthropic(
    prompt: str,
    model_id: str,
    api_key: str,
    *,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> tuple[str, int | None, int | None]:
    """Call Anthropic Messages API.

    Returns (text_reply, input_tokens, output_tokens).
    Raises AIUnavailableError on any failure.
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        text: str = data["content"][0]["text"]
        usage = data.get("usage", {})
        return (
            text,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
        )
    except httpx.HTTPStatusError as exc:
        raise AIUnavailableError(f"Anthropic API error: {exc.response.status_code}") from exc
    except Exception as exc:
        raise AIUnavailableError(f"Anthropic call failed: {exc}") from exc


def _call_openai(
    prompt: str,
    model_id: str,
    api_key: str,
    *,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> tuple[str, int | None, int | None]:
    """Call OpenAI Chat Completions API.

    Returns (text_reply, input_tokens, output_tokens).
    Raises AIUnavailableError on any failure.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        text: str = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return (
            text,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )
    except httpx.HTTPStatusError as exc:
        raise AIUnavailableError(f"OpenAI API error: {exc.response.status_code}") from exc
    except Exception as exc:
        raise AIUnavailableError(f"OpenAI call failed: {exc}") from exc


# ── Public interface ──────────────────────────────────────────────────────────


def call_ai(
    prompt: str,
    *,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> tuple[str, str, str, int | None, int | None]:
    """Call the configured AI provider with the given prompt.

    Returns (text_reply, provider, model_id, input_tokens, output_tokens).
    Raises AIUnavailableError when AI is not configured or the call fails.
    """
    settings = get_settings()

    if not settings.ai_enabled:
        raise AIUnavailableError("AI is not enabled (check AI_PROVIDER and API key).")

    provider = settings.ai_provider
    model_id = settings.ai_model

    if provider == "anthropic":
        text, inp, out = _call_anthropic(
            prompt,
            model_id,
            settings.anthropic_api_key,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    elif provider == "openai":
        text, inp, out = _call_openai(
            prompt,
            model_id,
            settings.openai_api_key,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    else:
        raise AIUnavailableError(f"Unknown AI provider: {provider!r}")

    return text, provider, model_id, inp, out


def parse_json_reply(text: str) -> dict[str, Any]:
    """Extract a JSON object from the model's text reply.

    Models sometimes wrap JSON in markdown code fences.
    This strips them before parsing.
    Raises ValueError if no valid JSON object is found.
    """
    # Strip markdown fences
    stripped = text.strip()
    for fence in ("```json", "```"):
        if stripped.startswith(fence):
            stripped = stripped[len(fence) :]
            break
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    stripped = stripped.strip()

    try:
        result = json.loads(stripped)
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object, got a different type.")
        return result
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON from AI reply: {exc}") from exc
