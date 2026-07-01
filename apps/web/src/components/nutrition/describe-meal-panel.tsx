"use client";

/**
 * DescribeMealPanel - "describe everything you ate" multi-item AI flow.
 *
 * Step 1: free-text description of multiple foods (e.g.
 *   "45g oats, 200ml almond milk, 2 belvita biscuits, 1 scoop whey protein")
 * Step 2: an editable per-item preview table (Food | Calories | Protein |
 *   Carbs | Fat | Fiber) with a totals row - the user can adjust each
 *   item's quantity or remove a row before saving.
 * Step 3 (Save & log all): creates one Food + one FoodLog per item in a
 *   single call, then the parent refreshes daily totals / charts / insight.
 *
 * Safety: nothing is saved until the user presses "Save & log all" - this
 * mirrors the single-item AI estimate flow's preview-then-approve pattern.
 */

import { useId, useState } from "react";
import { cn } from "@/lib/utils";
import { nutritionApi } from "@/lib/nutrition-api";
import { recipesApi } from "@/lib/recipe-api";
import type {
  LogMealItemPayload,
  MealItemEstimate,
  MealType,
} from "@/types/nutrition";
import { MEAL_TYPE_LABELS, MEAL_TYPE_ORDER } from "@/types/nutrition";

interface EditableItem {
  name: string;
  quantity_g: number;
  serving_unit: string | null;
  calories_per_100g: number;
  protein_per_100g: number;
  carbs_per_100g: number;
  fat_per_100g: number;
  fiber_per_100g: number | null;
  confidence: string;
}

function toEditable(item: MealItemEstimate): EditableItem {
  return {
    name: item.name,
    quantity_g: item.quantity_g,
    serving_unit: item.serving_unit,
    calories_per_100g: item.calories_per_100g,
    protein_per_100g: item.protein_per_100g,
    carbs_per_100g: item.carbs_per_100g,
    fat_per_100g: item.fat_per_100g,
    fiber_per_100g: item.fiber_per_100g,
    confidence: item.confidence,
  };
}

function computed(item: EditableItem) {
  const factor = item.quantity_g / 100;
  return {
    calories: Math.round(item.calories_per_100g * factor),
    protein: round1(item.protein_per_100g * factor),
    carbs: round1(item.carbs_per_100g * factor),
    fat: round1(item.fat_per_100g * factor),
    fiber: item.fiber_per_100g !== null ? round1(item.fiber_per_100g * factor) : null,
  };
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

interface DescribeMealPanelProps {
  date: string;
  onLogged: () => Promise<void> | void;
  onCancel: () => void;
}

export function DescribeMealPanel({ date, onLogged, onCancel }: DescribeMealPanelProps) {
  const fid = useId();
  const [description, setDescription] = useState("");
  const [mealType, setMealType] = useState<MealType>("other");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiAvailable, setAiAvailable] = useState<boolean | null>(null);
  const [aiMessage, setAiMessage] = useState<string | null>(null);
  const [estimateLogId, setEstimateLogId] = useState<string | null>(null);
  const [items, setItems] = useState<EditableItem[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveAsRecipe, setSaveAsRecipe] = useState(false);
  const [recipeName, setRecipeName] = useState("");
  const [recipeSaveError, setRecipeSaveError] = useState<string | null>(null);

  async function handleEstimate(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setItems(null);
    try {
      const result = await nutritionApi.estimateMeal(description.trim());
      setAiAvailable(result.ai_available);
      setAiMessage(result.message);
      setEstimateLogId(result.log_id);
      if (result.ai_available) {
        setItems(result.items.map(toEditable));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't estimate this meal.");
    } finally {
      setLoading(false);
    }
  }

  function updateItem(index: number, patch: Partial<EditableItem>) {
    setItems((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      next[index] = { ...next[index]!, ...patch };
      return next;
    });
  }

  function removeItem(index: number) {
    setItems((prev) => (prev ? prev.filter((_, i) => i !== index) : prev));
  }

  const totals = items?.reduce(
    (acc, item) => {
      const c = computed(item);
      return {
        calories: acc.calories + c.calories,
        protein: round1(acc.protein + c.protein),
        carbs: round1(acc.carbs + c.carbs),
        fat: round1(acc.fat + c.fat),
        fiber: c.fiber !== null ? round1((acc.fiber ?? 0) + c.fiber) : acc.fiber,
      };
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 as number | null }
  );

  async function handleSave() {
    if (!items || items.length === 0) {
      setError("Add at least one item before saving.");
      return;
    }
    if (saveAsRecipe && !recipeName.trim()) {
      setError("Give the recipe a name, or uncheck \"Save as a recipe\".");
      return;
    }
    setSaving(true);
    setError(null);
    setRecipeSaveError(null);
    try {
      const payload: LogMealItemPayload[] = items.map((item) => ({
        name: item.name.trim() || "Food",
        quantity_g: item.quantity_g,
        ...(item.serving_unit ? { serving_unit: item.serving_unit } : {}),
        calories_per_100g: item.calories_per_100g,
        protein_per_100g: item.protein_per_100g,
        carbs_per_100g: item.carbs_per_100g,
        fat_per_100g: item.fat_per_100g,
        ...(item.fiber_per_100g !== null ? { fiber_per_100g: item.fiber_per_100g } : {}),
      }));
      const result = await nutritionApi.logMeal({
        logged_date: date,
        meal_type: mealType,
        items: payload,
        ...(estimateLogId ? { estimate_log_id: estimateLogId } : {}),
      });

      // Optionally save the just-logged foods as a reusable recipe, using
      // the Food records logMeal just created - so next time this exact
      // combo is eaten, it can be re-logged without re-running AI.
      if (saveAsRecipe) {
        try {
          await recipesApi.create({
            name: recipeName.trim(),
            items: result.entries.map((entry) => ({
              food_id: entry.food_id,
              quantity_g: entry.quantity_g,
            })),
          });
        } catch (err) {
          // The meal is already logged successfully at this point - only
          // the recipe-save step failed. Keep the panel open so the user
          // sees this rather than silently losing it when the panel closes.
          setRecipeSaveError(
            err instanceof Error ? err.message : "Meal logged, but saving it as a recipe failed."
          );
          setSaving(false);
          return;
        }
      }

      await onLogged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save this meal.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50/40 p-4 dark:border-brand-900 dark:bg-brand-950/20">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-surface-900 dark:text-surface-50">
          Log everything you ate
        </h2>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-2 py-1 text-xs text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-400 dark:hover:bg-surface-700"
        >
          Close
        </button>
      </div>

      {/* Step 1: describe */}
      {!items && (
        <form onSubmit={(e) => void handleEstimate(e)} className="space-y-3">
          <div>
            <label
              htmlFor={`${fid}-desc`}
              className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300"
            >
              Describe everything you had, with quantities
            </label>
            <textarea
              id={`${fid}-desc`}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={3}
              placeholder="e.g. 45g oats, 200ml unsweetened almond milk, 1 tsp chia seeds, 2 belvita biscuits, 1 scoop whey protein"
              className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
            />
          </div>

          <div className="max-w-[160px]">
            <label
              htmlFor={`${fid}-meal`}
              className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300"
            >
              Log as
            </label>
            <select
              id={`${fid}-meal`}
              value={mealType}
              onChange={(e) => setMealType(e.target.value as MealType)}
              className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
            >
              {MEAL_TYPE_ORDER.map((mt) => (
                <option key={mt} value={mt}>
                  {MEAL_TYPE_LABELS[mt]}
                </option>
              ))}
            </select>
          </div>

          {aiAvailable === false && (
            <p
              role="status"
              className="rounded-lg bg-surface-50 px-3 py-2 text-xs text-surface-600 dark:bg-surface-700 dark:text-surface-300"
            >
              {aiMessage ?? "AI estimate unavailable. Add foods individually instead."}
            </p>
          )}
          {error && (
            <p className="text-xs text-red-600 dark:text-red-400" role="alert">
              {error}
            </p>
          )}

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={loading || !description.trim()}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
            >
              {loading ? "Analyzing…" : "Estimate macros"}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Step 2: editable preview table */}
      {items && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <span aria-hidden="true">⚠</span>
            <span>Approximate nutrition breakdown - review and edit quantities before saving.</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-surface-200 dark:border-surface-700">
            <table className="w-full min-w-[560px] text-left text-xs">
              <caption className="sr-only">Estimated macros per item</caption>
              <thead className="bg-surface-50 dark:bg-surface-700">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium text-surface-600 dark:text-surface-200">
                    Food
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium text-surface-600 dark:text-surface-200">
                    Qty (g)
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-surface-600 dark:text-surface-200">
                    Calories
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-surface-600 dark:text-surface-200">
                    Protein
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-surface-600 dark:text-surface-200">
                    Carbs
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-surface-600 dark:text-surface-200">
                    Fat
                  </th>
                  <th scope="col" className="px-3 py-2 text-right font-medium text-surface-600 dark:text-surface-200">
                    Fiber
                  </th>
                  <th scope="col" className="px-3 py-2">
                    <span className="sr-only">Remove</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => {
                  const c = computed(item);
                  return (
                    <tr key={i} className="border-t border-surface-100 dark:border-surface-700">
                      <td className="px-3 py-1.5">
                        <label className="sr-only" htmlFor={`${fid}-name-${i}`}>
                          Food name
                        </label>
                        <input
                          id={`${fid}-name-${i}`}
                          type="text"
                          value={item.name}
                          onChange={(e) => updateItem(i, { name: e.target.value })}
                          className="w-36 rounded border border-surface-200 bg-white px-2 py-1 text-xs text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/30 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
                        />
                      </td>
                      <td className="px-3 py-1.5">
                        <label className="sr-only" htmlFor={`${fid}-qty-${i}`}>
                          Quantity in grams for {item.name}
                        </label>
                        <input
                          id={`${fid}-qty-${i}`}
                          type="number"
                          min="0.1"
                          step="any"
                          value={item.quantity_g}
                          onChange={(e) =>
                            updateItem(i, { quantity_g: parseFloat(e.target.value) || 0 })
                          }
                          className="w-20 rounded border border-surface-200 bg-white px-2 py-1 text-xs text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/30 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-right text-surface-900 dark:text-surface-100">
                        {c.calories} kcal
                      </td>
                      <td className="px-3 py-1.5 text-right text-surface-700 dark:text-surface-200">{c.protein} g</td>
                      <td className="px-3 py-1.5 text-right text-surface-700 dark:text-surface-200">{c.carbs} g</td>
                      <td className="px-3 py-1.5 text-right text-surface-700 dark:text-surface-200">{c.fat} g</td>
                      <td className="px-3 py-1.5 text-right text-surface-700 dark:text-surface-200">
                        {c.fiber ?? "-"}
                        {c.fiber !== null ? " g" : ""}
                      </td>
                      <td className="px-3 py-1.5">
                        <button
                          type="button"
                          onClick={() => removeItem(i)}
                          aria-label={`Remove ${item.name}`}
                          className="rounded px-1.5 py-0.5 text-surface-400 hover:bg-red-50 hover:text-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {totals && (
                <tfoot>
                  <tr className="border-t-2 border-surface-200 font-medium dark:border-surface-600">
                    <td className="px-3 py-2 text-surface-900 dark:text-surface-50" colSpan={2}>
                      Total
                    </td>
                    <td className="px-3 py-2 text-right text-surface-900 dark:text-surface-50">
                      {Math.round(totals.calories)} kcal
                    </td>
                    <td className="px-3 py-2 text-right text-surface-900 dark:text-surface-50">
                      {totals.protein} g
                    </td>
                    <td className="px-3 py-2 text-right text-surface-900 dark:text-surface-50">
                      {totals.carbs} g
                    </td>
                    <td className="px-3 py-2 text-right text-surface-900 dark:text-surface-50">
                      {totals.fat} g
                    </td>
                    <td className="px-3 py-2 text-right text-surface-900 dark:text-surface-50">
                      {totals.fiber ?? "-"}
                      {totals.fiber !== null ? " g" : ""}
                    </td>
                    <td />
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          {/* Optionally save this exact combo as a reusable recipe */}
          <div className="rounded-lg border border-surface-200 bg-white p-2.5 dark:border-surface-700 dark:bg-surface-900">
            <label className="flex items-center gap-2 text-xs font-medium text-surface-700 dark:text-surface-200">
              <input
                type="checkbox"
                checked={saveAsRecipe}
                onChange={(e) => setSaveAsRecipe(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-surface-300 text-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
              />
              Also save this as a recipe, so I can re-log it later without re-describing it
            </label>
            {saveAsRecipe && (
              <input
                type="text"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                maxLength={200}
                placeholder="Recipe name, e.g. Morning shake"
                aria-label="Recipe name"
                className="mt-2 w-full rounded-lg border border-surface-200 bg-white px-3 py-1.5 text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
              />
            )}
          </div>

          {error && (
            <p className="text-xs text-red-600 dark:text-red-400" role="alert">
              {error}
            </p>
          )}

          {recipeSaveError ? (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-200">
              <p role="alert">{recipeSaveError}</p>
              <button
                type="button"
                onClick={() => void onLogged()}
                className="mt-1 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700"
              >
                OK, done
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving || items.length === 0}
                className={cn(
                  "rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
                )}
              >
                {saving ? "Saving…" : `Save & log all (${items.length})`}
              </button>
              <button
                type="button"
                onClick={() => setItems(null)}
                className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
              >
                Re-describe
              </button>
              <button
                type="button"
                onClick={onCancel}
                className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
