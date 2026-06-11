/**
 * Shared client-side utilities.
 *
 * This module intentionally contains only small, pure helper functions
 * with no side effects. Business logic belongs in feature modules.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS class names, resolving conflicts.
 *
 * Usage:
 *   cn("px-4 py-2", isActive && "bg-brand-500", className)
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format a number with a fixed number of decimal places,
 * removing trailing zeros (e.g. 1.50 → "1.5", 1.00 → "1").
 */
export function formatNumber(
  value: number,
  maxDecimals: number = 1
): string {
  return parseFloat(value.toFixed(maxDecimals)).toString();
}

/**
 * Return a user-facing label for a unit abbreviation.
 */
export function unitLabel(unit: string): string {
  const labels: Record<string, string> = {
    kg: "kg",
    lb: "lb",
    lbs: "lb",
    km: "km",
    mi: "mi",
    m: "m",
    ml: "ml",
    L: "L",
    fl_oz: "fl oz",
    cup: "cup",
    kcal: "kcal",
    kJ: "kJ",
    cm: "cm",
    in: "in",
    steps: "steps",
    min: "min",
    h: "h",
    reps: "reps",
  };
  return labels[unit] ?? unit;
}

/**
 * Clamp a number between min and max (inclusive).
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Type-safe assertion that a value is not null or undefined.
 * Throws in development; fails silently (returns undefined) in production.
 */
export function assertDefined<T>(
  value: T | null | undefined,
  message?: string
): T {
  if (value === null || value === undefined) {
    throw new Error(message ?? "Expected a defined value");
  }
  return value;
}
