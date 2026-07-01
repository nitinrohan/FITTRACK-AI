"use client";

/**
 * /dashboard/recipes - Saved food combinations you can re-log later.
 *
 * Features:
 *   - List of saved recipes with per-item macros + totals
 *   - Create a recipe by searching foods and adding quantities
 *   - "Log this" - re-log a recipe to any date/meal, optionally scaled
 *     (e.g. 0.5x logs half the saved quantities)
 *   - Delete with confirmation
 *   - All states: loading, empty, error, validation, destructive-confirm
 */

import { useEffect, useId, useRef, useState } from "react";
import { useRecipes } from "@/features/recipes/use-recipes";
import { useFoodSearch } from "@/features/nutrition/use-nutrition";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";
import type { CreateRecipePayload, Recipe } from "@/types/recipe";
import type { MealType } from "@/types/nutrition";
import { MEAL_TYPE_LABELS, MEAL_TYPE_ORDER } from "@/types/nutrition";

function todayStr(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

export default function RecipesPage() {
  const { recipes, isLoading, error, refresh, create, remove, logRecipe } = useRecipes();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-surface-900 dark:text-surface-50">Recipes</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Save a combination of foods once, log it again in one tap
          </p>
        </div>
        {!showCreate && (
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            New recipe
          </button>
        )}
      </div>

      {showCreate && (
        <CreateRecipeForm
          onCreate={async (payload) => {
            await create(payload);
            setShowCreate(false);
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading recipes…" />
        </div>
      )}

      {!isLoading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
          <button onClick={() => void refresh()} className="ml-2 underline hover:no-underline">
            Retry
          </button>
        </div>
      )}

      {!isLoading && !error && recipes.length === 0 && !showCreate && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-surface-300 py-16 text-center dark:border-surface-700">
          <p className="font-semibold text-surface-900 dark:text-surface-50">No recipes yet</p>
          <p className="mt-1 max-w-xs text-sm text-surface-500 dark:text-surface-400">
            Save a combination of foods you eat often - like a shake or a go-to lunch - and log it again in one tap.
          </p>
        </div>
      )}

      {!isLoading && !error && recipes.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {recipes.map((recipe) => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onLog={(payload) => logRecipe(recipe.id, payload)}
              onDelete={() => remove(recipe.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Recipe card ───────────────────────────────────────────────────────────────

function RecipeCard({
  recipe,
  onLog,
  onDelete,
}: {
  recipe: Recipe;
  onLog: (payload: { logged_date: string; meal_type?: MealType; scale_factor?: number }) => Promise<unknown>;
  onDelete: () => Promise<void>;
}) {
  const [showLog, setShowLog] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onDelete();
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-700 dark:bg-surface-800">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-medium text-surface-900 dark:text-surface-50">{recipe.name}</h2>
          {recipe.description && (
            <p className="mt-0.5 text-xs text-surface-500 dark:text-surface-400">{recipe.description}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {confirmDelete ? (
            <>
              <button
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950"
              >
                {deleting ? "…" : "Delete"}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded px-2 py-0.5 text-xs text-surface-500 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-700"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              aria-label={`Delete ${recipe.name}`}
              className="rounded p-1 text-surface-400 hover:bg-red-50 hover:text-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:hover:bg-red-950"
            >
              <TrashIcon />
            </button>
          )}
        </div>
      </div>

      <ul className="mt-3 space-y-1 text-xs text-surface-600 dark:text-surface-300">
        {recipe.items.map((item) => (
          <li key={item.food_id} className="flex justify-between gap-2">
            <span className="truncate">
              {item.food_name} <span className="text-surface-400">({item.quantity_g}g)</span>
            </span>
            <span className="shrink-0 text-surface-500 dark:text-surface-400">
              {Math.round(item.calories)} kcal
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-3 flex flex-wrap gap-3 border-t border-surface-100 pt-2 text-xs text-surface-500 dark:border-surface-700 dark:text-surface-400">
        <span className="font-medium text-surface-700 dark:text-surface-200">
          {Math.round(recipe.totals.calories)} kcal
        </span>
        <span>P {recipe.totals.protein_g}g</span>
        <span>C {recipe.totals.carbs_g}g</span>
        <span>F {recipe.totals.fat_g}g</span>
        <span>Fiber {recipe.totals.fiber_g}g</span>
      </div>

      {!showLog ? (
        <button
          type="button"
          onClick={() => setShowLog(true)}
          className="mt-3 w-full rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          Log this
        </button>
      ) : (
        <LogRecipeForm onLog={onLog} onDone={() => setShowLog(false)} />
      )}
    </div>
  );
}

// ── Log-recipe inline form ────────────────────────────────────────────────────

function LogRecipeForm({
  onLog,
  onDone,
}: {
  onLog: (payload: { logged_date: string; meal_type?: MealType; scale_factor?: number }) => Promise<unknown>;
  onDone: () => void;
}) {
  const fid = useId();
  const [date, setDate] = useState(todayStr());
  const [mealType, setMealType] = useState<MealType>("other");
  const [scale, setScale] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const scaleNum = parseFloat(scale);
    if (isNaN(scaleNum) || scaleNum <= 0) {
      setError("Enter a scale greater than 0 (1 = log exactly as saved).");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onLog({ logged_date: date, meal_type: mealType, scale_factor: scaleNum });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log this recipe.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="mt-3 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700 dark:bg-brand-950 dark:text-brand-300" role="status">
        Logged! Check the Nutrition page for {date}.
        <button type="button" onClick={onDone} className="ml-2 underline hover:no-underline">
          Close
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="mt-3 space-y-2 rounded-lg border border-surface-200 bg-surface-50 p-2.5 dark:border-surface-700 dark:bg-surface-900">
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label htmlFor={`${fid}-date`} className="mb-1 block text-[11px] text-surface-500 dark:text-surface-400">
            Date
          </label>
          <input
            id={`${fid}-date`}
            type="date"
            value={date}
            max={todayStr()}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded border border-surface-200 bg-white px-1.5 py-1 text-xs text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/30 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <div>
          <label htmlFor={`${fid}-meal`} className="mb-1 block text-[11px] text-surface-500 dark:text-surface-400">
            Meal
          </label>
          <select
            id={`${fid}-meal`}
            value={mealType}
            onChange={(e) => setMealType(e.target.value as MealType)}
            className="w-full rounded border border-surface-200 bg-white px-1.5 py-1 text-xs text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/30 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          >
            {MEAL_TYPE_ORDER.map((mt) => (
              <option key={mt} value={mt}>
                {MEAL_TYPE_LABELS[mt]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={`${fid}-scale`} className="mb-1 block text-[11px] text-surface-500 dark:text-surface-400">
            Scale (1 = as saved)
          </label>
          <input
            id={`${fid}-scale`}
            type="number"
            min="0.1"
            step="any"
            value={scale}
            onChange={(e) => setScale(e.target.value)}
            className="w-full rounded border border-surface-200 bg-white px-1.5 py-1 text-xs text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/30 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
      </div>
      {error && (
        <p className="text-xs text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {submitting ? "Logging…" : "Confirm"}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-lg px-2.5 py-1 text-xs text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ── Create recipe form ────────────────────────────────────────────────────────

interface DraftItem {
  food_id: string;
  name: string;
  quantity_g: number;
}

function CreateRecipeForm({
  onCreate,
  onCancel,
}: {
  onCreate: (payload: CreateRecipePayload) => Promise<void>;
  onCancel: () => void;
}) {
  const fid = useId();
  const { results, isSearching, search, clear } = useFoodSearch();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [query, setQuery] = useState("");
  const [quantity, setQuantity] = useState("100");
  const [items, setItems] = useState<DraftItem[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleQueryChange(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void search(value), 350);
  }

  function addItem(foodId: string, foodName: string) {
    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setError("Enter a valid quantity greater than 0 before adding.");
      return;
    }
    setItems((prev) => [...prev, { food_id: foodId, name: foodName, quantity_g: qty }]);
    setQuery("");
    setQuantity("100");
    clear();
    setError(null);
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Give the recipe a name.");
      return;
    }
    if (items.length === 0) {
      setError("Add at least one food.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({
        name: name.trim(),
        ...(description.trim() ? { description: description.trim() } : {}),
        items: items.map((i) => ({ food_id: i.food_id, quantity_g: i.quantity_g })),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save recipe.");
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="space-y-3 rounded-xl border border-brand-200 bg-brand-50/40 p-4 dark:border-brand-900 dark:bg-brand-950/20"
    >
      <div>
        <label htmlFor={`${fid}-name`} className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
          Recipe name
        </label>
        <input
          id={`${fid}-name`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={200}
          placeholder="e.g. Morning shake"
          className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
        />
      </div>

      <div>
        <label htmlFor={`${fid}-desc`} className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
          Description (optional)
        </label>
        <input
          id={`${fid}-desc`}
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={1000}
          className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
        />
      </div>

      {items.length > 0 && (
        <ul className="space-y-1 rounded-lg border border-surface-200 bg-white p-2 text-xs dark:border-surface-700 dark:bg-surface-900">
          {items.map((item, i) => (
            <li key={i} className="flex items-center justify-between gap-2 text-surface-700 dark:text-surface-200">
              <span>
                {item.name} - {item.quantity_g}g
              </span>
              <button
                type="button"
                onClick={() => removeItem(i)}
                aria-label={`Remove ${item.name}`}
                className="rounded px-1.5 text-surface-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="relative">
        <label htmlFor={`${fid}-search`} className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300">
          Add a food
        </label>
        <div className="flex gap-2">
          <input
            id={`${fid}-search`}
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="Search food…"
            autoComplete="off"
            className="flex-1 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
          <input
            type="number"
            min="1"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            aria-label="Quantity in grams"
            className="w-20 rounded-lg border border-surface-200 bg-white px-2 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        {isSearching && <span className="mt-1 block text-xs text-surface-500">Searching…</span>}
        {results.length > 0 && (
          <ul
            role="listbox"
            aria-label="Food search results"
            className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-surface-200 bg-white shadow-md dark:border-surface-600 dark:bg-surface-800"
          >
            {results.map((food) => (
              <li key={food.id} role="option" aria-selected={false}>
                <button
                  type="button"
                  onClick={() => addItem(food.id, food.name)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-50 dark:hover:bg-surface-700"
                >
                  <span className="font-medium text-surface-900 dark:text-surface-50">{food.name}</span>
                  <span className="text-xs text-surface-500 dark:text-surface-400">{food.calories_per_100g} kcal/100g</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting}
          className={cn(
            "rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50"
          )}
        >
          {submitting ? "Saving…" : "Save recipe"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function TrashIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  );
}
