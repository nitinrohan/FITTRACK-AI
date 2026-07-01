"""Shared, tested macro-scaling calculations used across the nutrition domain.

Both `nutrition_service` (food logs) and `recipe_service` (saved recipes)
scale per-100g macro values to an actual quantity eaten and sum a list of
entries into day/recipe totals. This module is the single place that math
lives, per the project's "avoid duplicated logic" rule.

Formula: displayed_value = (per_100g_value * quantity_g) / 100, rounded to
1 decimal place for display. Fiber is optional - `None` (missing) is
distinguished from `0` (measured zero) throughout.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


def scale_macro(per_100g: float, quantity_g: float) -> float:
    """Scale a per-100g value to the actual quantity eaten."""
    return round(per_100g * quantity_g / 100, 1)


def scale_optional_macro(per_100g: float | None, quantity_g: float) -> float | None:
    """Same as scale_macro, but preserves `None` (unknown) rather than treating
    a missing value as zero."""
    if per_100g is None:
        return None
    return scale_macro(per_100g, quantity_g)


class _MacroEntry(Protocol):
    """Structural type for anything with scaled macro fields (FoodLogResponse,
    RecipeItemResponse, ...) - lets sum_macro_totals work across domains."""

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


def sum_macro_totals(entries: Sequence[_MacroEntry]) -> tuple[float, float, float, float, float]:
    """Sum a list of scaled macro entries.

    Returns (calories, protein_g, carbs_g, fat_g, fiber_g) rounded to 1
    decimal place. Missing fiber values are treated as 0 for the total
    (matches existing MacroTotals.fiber_g behaviour, which is always a
    number - never null - because "total fiber logged" of an empty/unknown
    set is meaningfully 0, unlike a single food's fiber which can be unknown).
    """
    return (
        round(sum(e.calories for e in entries), 1),
        round(sum(e.protein_g for e in entries), 1),
        round(sum(e.carbs_g for e in entries), 1),
        round(sum(e.fat_g for e in entries), 1),
        round(sum(e.fiber_g or 0 for e in entries), 1),
    )
