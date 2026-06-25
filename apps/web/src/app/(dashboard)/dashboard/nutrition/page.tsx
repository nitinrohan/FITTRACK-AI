"use client";

/**
 * /dashboard/nutrition — Daily nutrition log page.
 *
 * Features:
 *   - Date navigation (prev / today / next)
 *   - Macro summary bar (calories, protein, carbs, fat)
 *   - Per-meal sections (breakfast, lunch, dinner, snack, other)
 *     - Inline food search + add form per section
 *     - Per-entry delete with quantity display
 *   - Water tracker (log entries, running total)
 *   - All states: loading, empty, error
 */

import { useEffect, useId, useRef, useState } from "react";
import { useNutrition, useFoodSearch } from "@/features/nutrition/use-nutrition";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";
import { foodsApi, nutritionApi } from "@/lib/nutrition-api";
import type {
  FoodLogEntry,
  MacroEstimate,
  MacroTotals,
  MealSection,
  MealType,
  WaterLogEntry,
} from "@/types/nutrition";
import { MEAL_TYPE_LABELS, MEAL_TYPE_ORDER } from "@/types/nutrition";

// ── Date helpers ──────────────────────────────────────────────────────────────

function todayStr(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

function offsetDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0] ?? "";
}

function formatDateLabel(dateStr: string): string {
  const today = todayStr();
  const yesterday = offsetDate(today, -1);
  if (dateStr === today) return "Today";
  if (dateStr === yesterday) return "Yesterday";
  return new Date(dateStr + "T12:00:00").toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NutritionPage() {
  const [date, setDate] = useState(todayStr);

  const {
    daily,
    isLoading,
    error,
    refresh,
    logFood,
    deleteFoodLog,
    logWater,
    deleteWaterLog,
  } = useNutrition(date);

  const goToday = () => setDate(todayStr());
  const goPrev = () => setDate((d) => offsetDate(d, -1));
  const goNext = () => {
    const next = offsetDate(date, 1);
    if (next <= todayStr()) setDate(next);
  };

  const isFuture = date >= offsetDate(todayStr(), 1);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-surface-900 dark:text-surface-50">Nutrition</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Track your food and water intake
          </p>
        </div>

        {/* Date navigation */}
        <div className="flex items-center gap-1 rounded-xl border border-surface-200 bg-white p-1">
          <button
            onClick={goPrev}
            aria-label="Previous day"
            className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            <ChevronLeft />
          </button>
          <button
            onClick={goToday}
            className={cn(
              "min-w-[110px] rounded-lg px-3 py-1 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
              date === todayStr()
                ? "bg-brand-50 text-brand-700"
                : "text-surface-700 hover:bg-surface-100"
            )}
          >
            {formatDateLabel(date)}
          </button>
          <button
            onClick={goNext}
            disabled={isFuture}
            aria-label="Next day"
            className="rounded-lg p-1.5 text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-30 disabled:pointer-events-none"
          >
            <ChevronRight />
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading nutrition data…" />
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button
            onClick={() => void refresh()}
            className="ml-2 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && daily && (
        <div className="space-y-6">
          {/* Macro summary */}
          <MacroSummaryBar totals={daily.day_totals} />

          {/* Meal sections */}
          <div className="space-y-4">
            {MEAL_TYPE_ORDER.map((mealType) => {
              const section = daily.meals.find((m) => m.meal_type === mealType);
              return (
                <MealSectionCard
                  key={mealType}
                  mealType={mealType}
                  section={section ?? null}
                  date={date}
                  onLogFood={logFood}
                  onDeleteEntry={deleteFoodLog}
                />
              );
            })}
          </div>

          {/* Water tracker */}
          <WaterTracker
            entries={daily.water_logs}
            totalMl={daily.water_total_ml}
            date={date}
            onLogWater={logWater}
            onDeleteEntry={deleteWaterLog}
          />
        </div>
      )}
    </div>
  );
}

// ── Macro summary bar ─────────────────────────────────────────────────────────

function MacroSummaryBar({ totals }: { totals: MacroTotals }) {
  const macros = [
    { label: "Calories", value: Math.round(totals.calories), unit: "kcal", color: "bg-orange-400" },
    { label: "Protein", value: Math.round(totals.protein_g), unit: "g", color: "bg-brand-500" },
    { label: "Carbs", value: Math.round(totals.carbs_g), unit: "g", color: "bg-yellow-400" },
    { label: "Fat", value: Math.round(totals.fat_g), unit: "g", color: "bg-pink-400" },
  ];

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4">
      <h2 className="mb-3 text-sm font-medium text-surface-500">
        Daily totals
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {macros.map(({ label, value, unit, color }) => (
          <div key={label} className="rounded-lg bg-surface-50 p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <span className={cn("h-2 w-2 rounded-full", color)} aria-hidden="true" />
              <span className="text-xs text-surface-500">{label}</span>
            </div>
            <div className="text-xl font-semibold text-surface-900">
              {value}
              <span className="ml-0.5 text-xs font-normal text-surface-500">{unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Meal section card ─────────────────────────────────────────────────────────

interface MealSectionCardProps {
  mealType: MealType;
  section: MealSection | null;
  date: string;
  onLogFood: (payload: {
    food_id: string;
    logged_date: string;
    meal_type: MealType;
    quantity_g: number;
  }) => Promise<void>;
  onDeleteEntry: (id: string) => Promise<void>;
}

function MealSectionCard({
  mealType,
  section,
  date,
  onLogFood,
  onDeleteEntry,
}: MealSectionCardProps) {
  const [showAdd, setShowAdd] = useState(false);
  const entries = section?.entries ?? [];
  const totals = section?.totals;

  return (
    <div className="rounded-xl border border-surface-200 bg-white">
      {/* Meal header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-100">
        <div className="flex items-center gap-2">
          <h2 className="font-medium text-surface-900">
            {MEAL_TYPE_LABELS[mealType]}
          </h2>
          {totals && entries.length > 0 && (
            <span className="text-xs text-surface-500">
              {Math.round(totals.calories)} kcal
            </span>
          )}
        </div>
        <button
          onClick={() => setShowAdd((v) => !v)}
          aria-expanded={showAdd}
          className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
        >
          <PlusIcon />
          Add food
        </button>
      </div>

      {/* Add food form */}
      {showAdd && (
        <div className="border-b border-surface-100 px-4 py-3 bg-surface-50">
          <AddFoodForm
            mealType={mealType}
            date={date}
            onAdd={async (food_id, quantity_g) => {
              await onLogFood({ food_id, logged_date: date, meal_type: mealType, quantity_g });
              setShowAdd(false);
            }}
            onCancel={() => setShowAdd(false)}
          />
        </div>
      )}

      {/* Entries */}
      {entries.length === 0 && !showAdd ? (
        <p className="px-4 py-4 text-sm text-surface-500 italic">
          Nothing logged yet — add a food above.
        </p>
      ) : (
        <ul className="divide-y divide-surface-100" aria-label={`${MEAL_TYPE_LABELS[mealType]} entries`}>
          {entries.map((entry) => (
            <FoodLogRow
              key={entry.id}
              entry={entry}
              onDelete={onDeleteEntry}
            />
          ))}
        </ul>
      )}

      {/* Meal macro summary (only when entries exist) */}
      {totals && entries.length > 0 && (
        <div className="flex flex-wrap gap-3 border-t border-surface-100 px-4 py-2 text-xs text-surface-500">
          <span>P {Math.round(totals.protein_g)}g</span>
          <span>C {Math.round(totals.carbs_g)}g</span>
          <span>F {Math.round(totals.fat_g)}g</span>
        </div>
      )}
    </div>
  );
}

// ── Food log row ──────────────────────────────────────────────────────────────

function FoodLogRow({
  entry,
  onDelete,
}: {
  entry: FoodLogEntry;
  onDelete: (id: string) => Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);
  const [confirm, setConfirm] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onDelete(entry.id);
    } finally {
      setDeleting(false);
      setConfirm(false);
    }
  }

  return (
    <li className="flex items-center justify-between gap-3 px-4 py-2.5">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-surface-900">
          {entry.food_name}
          {entry.food_brand && (
            <span className="ml-1 text-xs font-normal text-surface-500">
              {entry.food_brand}
            </span>
          )}
        </p>
        <p className="text-xs text-surface-500">
          {entry.quantity_g}g · {Math.round(entry.calories)} kcal · P{Math.round(entry.protein_g)}g C{Math.round(entry.carbs_g)}g F{Math.round(entry.fat_g)}g
        </p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {confirm ? (
          <>
            <button
              onClick={() => void handleDelete()}
              disabled={deleting}
              className="rounded px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 disabled:opacity-50"
            >
              {deleting ? "…" : "Yes, delete"}
            </button>
            <button
              onClick={() => setConfirm(false)}
              className="rounded px-2 py-0.5 text-xs text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirm(true)}
            aria-label={`Remove ${entry.food_name}`}
            className="rounded p-1 text-surface-500 hover:text-red-500 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
          >
            <TrashIcon />
          </button>
        )}
      </div>
    </li>
  );
}

// ── Add food form ─────────────────────────────────────────────────────────────

interface AddFoodFormProps {
  mealType: MealType;
  date: string;
  onAdd: (food_id: string, quantity_g: number) => Promise<void>;
  onCancel: () => void;
}

function AddFoodForm({ onAdd, onCancel }: AddFoodFormProps) {
  const [mode, setMode] = useState<"search" | "ai">("search");

  return (
    <div className="space-y-3">
      <div className="flex gap-1" role="tablist" aria-label="Add food method">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "search"}
          onClick={() => setMode("search")}
          className={addModeClass(mode === "search")}
        >
          Search
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "ai"}
          onClick={() => setMode("ai")}
          className={addModeClass(mode === "ai")}
        >
          Estimate with AI
        </button>
      </div>
      {mode === "search" ? (
        <SearchFoodForm onAdd={onAdd} onCancel={onCancel} />
      ) : (
        <AiEstimatePanel onAdd={onAdd} onCancel={onCancel} />
      )}
    </div>
  );
}

function addModeClass(active: boolean): string {
  return cn(
    "rounded-lg px-3 py-1 text-xs font-medium transition-colors",
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
    active
      ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
      : "text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200",
  );
}

function SearchFoodForm({ onAdd, onCancel }: Pick<AddFoodFormProps, "onAdd" | "onCancel">) {
  const { results, isSearching, searchError, search, clear } = useFoodSearch();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<{ id: string; name: string; serving_size_g: number | null } | null>(null);
  const [quantity, setQuantity] = useState("100");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleQueryChange(value: string) {
    setQuery(value);
    setSelected(null);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void search(value);
    }, 350);
  }

  function handleSelect(food: { id: string; name: string; serving_size_g: number | null }) {
    setSelected(food);
    setQuery(food.name);
    if (food.serving_size_g) setQuantity(String(food.serving_size_g));
    clear();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setSubmitError("Enter a valid quantity greater than 0.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onAdd(selected.id, qty);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to log food.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
      {/* Food search input */}
      <div className="relative">
        <label htmlFor="food-search" className="mb-1 block text-xs font-medium text-surface-600">
          Search food
        </label>
        <input
          id="food-search"
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="e.g. chicken breast, banana…"
          autoComplete="off"
          className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />
        {isSearching && (
          <span className="absolute right-3 top-8 text-xs text-surface-500">Searching…</span>
        )}

        {/* Search results dropdown */}
        {results.length > 0 && !selected && (
          <ul
            role="listbox"
            aria-label="Food search results"
            className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-surface-200 bg-white shadow-md"
          >
            {results.map((food) => (
              <li key={food.id} role="option" aria-selected={false}>
                <button
                  type="button"
                  onClick={() => handleSelect(food)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-50 focus-visible:bg-surface-50 focus-visible:outline-none"
                >
                  <span>
                    <span className="font-medium text-surface-900">{food.name}</span>
                    {food.brand && (
                      <span className="ml-1 text-xs text-surface-500">{food.brand}</span>
                    )}
                    {food.is_system && (
                      <span className="ml-1 rounded bg-surface-100 px-1 py-0.5 text-[10px] text-surface-500">
                        Library
                      </span>
                    )}
                  </span>
                  <span className="ml-3 shrink-0 text-xs text-surface-500">
                    {food.calories_per_100g} kcal/100g
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {searchError && (
          <p className="mt-1 text-xs text-red-600" role="alert">
            {searchError}
          </p>
        )}
      </div>

      {/* Quantity field — shown once a food is selected */}
      {selected && (
        <div>
          <label htmlFor="food-quantity" className="mb-1 block text-xs font-medium text-surface-600">
            Quantity (g)
          </label>
          <input
            id="food-quantity"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            min="1"
            step="any"
            required
            className="w-28 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
          <span className="ml-2 text-xs text-surface-500">grams</span>
        </div>
      )}

      {submitError && (
        <p className="text-xs text-red-600" role="alert">
          {submitError}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={!selected || submitting}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
        >
          {submitting ? "Adding…" : "Add"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ── AI macro estimate panel ─────────────────────────────────────────────────────

function AiEstimatePanel({
  onAdd,
  onCancel,
}: Pick<AddFoodFormProps, "onAdd" | "onCancel">) {
  const fid = useId();
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [estimate, setEstimate] = useState<MacroEstimate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Editable preview fields (seeded from the estimate, then user-adjustable).
  const [name, setName] = useState("");
  const [cal, setCal] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("serving");

  async function handleEstimate(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setEstimate(null);
    try {
      const est = await nutritionApi.estimateMacros(description.trim());
      setEstimate(est);
      if (est.ai_available) {
        setName(est.name ?? description.trim());
        setCal(String(est.calories_per_100g ?? 0));
        setProtein(String(est.protein_per_100g ?? 0));
        setCarbs(String(est.carbs_per_100g ?? 0));
        setFat(String(est.fat_per_100g ?? 0));
        setQuantity(String(est.serving_size_g ?? 100));
        setUnit(est.serving_unit ?? "serving");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Estimate failed.");
    } finally {
      setLoading(false);
    }
  }

  const qtyNum = parseFloat(quantity) || 0;
  const factor = qtyNum / 100;
  const portionCal = Math.round((parseFloat(cal) || 0) * factor);

  async function handleSave() {
    const qty = parseFloat(quantity);
    const calories = parseFloat(cal);
    if (!name.trim()) {
      setError("Give the food a name.");
      return;
    }
    if (isNaN(qty) || qty <= 0) {
      setError("Enter a quantity greater than 0.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const food = await foodsApi.create({
        name: name.trim(),
        calories_per_100g: Math.max(0, calories || 0),
        protein_per_100g: Math.max(0, parseFloat(protein) || 0),
        carbs_per_100g: Math.max(0, parseFloat(carbs) || 0),
        fat_per_100g: Math.max(0, parseFloat(fat) || 0),
        serving_size_g: qty,
        serving_unit: unit || undefined,
      });
      await onAdd(food.id, qty);
      if (estimate?.log_id) {
        void nutritionApi.recordMacroDecision(estimate.log_id, true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save food.");
      setSaving(false);
    }
  }

  function handleCancel() {
    if (estimate?.log_id) {
      void nutritionApi.recordMacroDecision(estimate.log_id, false);
    }
    onCancel();
  }

  // ── Step 1: describe ──────────────────────────────────────────────────────
  if (!estimate || !estimate.ai_available) {
    return (
      <form onSubmit={(e) => void handleEstimate(e)} className="space-y-3">
        <div>
          <label
            htmlFor={`${fid}-desc`}
            className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300"
          >
            Describe what you ate or drank
          </label>
          <input
            id={`${fid}-desc`}
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={280}
            placeholder="e.g. two boiled eggs and a slice of wholegrain toast"
            className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>

        {estimate && !estimate.ai_available && (
          <p
            role="status"
            className="rounded-lg bg-surface-50 px-3 py-2 text-xs text-surface-600 dark:bg-surface-700 dark:text-surface-300"
          >
            {estimate.message ??
              "AI estimate unavailable. Switch to Search, or save a food manually."}
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
            {loading ? "Estimating…" : "Estimate macros"}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
          >
            Cancel
          </button>
        </div>
      </form>
    );
  }

  // ── Step 2: editable preview ──────────────────────────────────────────────
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-200">
        <span aria-hidden="true">⚠</span>
        <span>
          {estimate.disclaimer}
          {estimate.confidence ? ` (${estimate.confidence} confidence)` : ""}
        </span>
      </div>

      <div>
        <label
          htmlFor={`${fid}-name`}
          className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300"
        >
          Food name
        </label>
        <input
          id={`${fid}-name`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
        />
      </div>

      <fieldset>
        <legend className="mb-1 text-xs font-medium text-surface-600 dark:text-surface-300">
          Per 100 g (editable)
        </legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <MacroField id={`${fid}-cal`} label="Calories" value={cal} onChange={setCal} />
          <MacroField id={`${fid}-pro`} label="Protein g" value={protein} onChange={setProtein} />
          <MacroField id={`${fid}-carb`} label="Carbs g" value={carbs} onChange={setCarbs} />
          <MacroField id={`${fid}-fat`} label="Fat g" value={fat} onChange={setFat} />
        </div>
      </fieldset>

      <div className="flex items-end gap-2">
        <div>
          <label
            htmlFor={`${fid}-qty`}
            className="mb-1 block text-xs font-medium text-surface-600 dark:text-surface-300"
          >
            Quantity (g)
          </label>
          <input
            id={`${fid}-qty`}
            type="number"
            min="1"
            step="any"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-28 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <p className="pb-2 text-xs text-surface-500 dark:text-surface-400">
          ≈ <span className="font-semibold text-surface-800 dark:text-surface-100">{portionCal}</span> kcal for this portion
        </p>
      </div>

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving…" : "Save & log"}
        </button>
        <button
          type="button"
          onClick={() => setEstimate(null)}
          className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
        >
          Re-estimate
        </button>
        <button
          type="button"
          onClick={handleCancel}
          className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-300 dark:hover:bg-surface-700"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function MacroField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-[11px] text-surface-500 dark:text-surface-400">
        {label}
      </label>
      <input
        id={id}
        type="number"
        min="0"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-surface-200 bg-white px-2 py-1.5 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
      />
    </div>
  );
}

// ── Water tracker ─────────────────────────────────────────────────────────────

interface WaterTrackerProps {
  entries: WaterLogEntry[];
  totalMl: number;
  date: string;
  onLogWater: (payload: { logged_date: string; amount_ml: number }) => Promise<void>;
  onDeleteEntry: (id: string) => Promise<void>;
}

function WaterTracker({
  entries,
  totalMl,
  date,
  onLogWater,
  onDeleteEntry,
}: WaterTrackerProps) {
  const [amount, setAmount] = useState("250");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ml = parseInt(amount, 10);
    if (isNaN(ml) || ml <= 0 || ml > 10000) {
      setError("Enter a value between 1 and 10 000 ml.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onLogWater({ logged_date: date, amount_ml: ml });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log water.");
    } finally {
      setSubmitting(false);
    }
  }

  const totalL = (totalMl / 1000).toFixed(2).replace(/\.?0+$/, "");

  return (
    <div className="rounded-xl border border-surface-200 bg-white">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-100">
        <div className="flex items-center gap-2">
          <WaterIcon />
          <h2 className="font-medium text-surface-900">Water</h2>
          {totalMl > 0 && (
            <span className="text-xs text-surface-500">{totalL} L today</span>
          )}
        </div>
      </div>

      {/* Quick-add form */}
      <form
        onSubmit={(e) => void handleAdd(e)}
        className="flex flex-wrap items-end gap-2 px-4 py-3 border-b border-surface-100 bg-surface-50"
      >
        <div>
          <label htmlFor="water-amount" className="mb-1 block text-xs font-medium text-surface-600">
            Amount (ml)
          </label>
          <input
            id="water-amount"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            min="1"
            max="10000"
            required
            className="w-28 rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        {/* Common quick-amounts */}
        <div className="flex gap-1">
          {[150, 250, 330, 500].map((ml) => (
            <button
              key={ml}
              type="button"
              onClick={() => setAmount(String(ml))}
              className={cn(
                "rounded-lg px-2.5 py-2 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
                amount === String(ml)
                  ? "bg-brand-100 text-brand-700"
                  : "bg-white border border-surface-200 text-surface-600 hover:bg-surface-100"
              )}
            >
              {ml}ml
            </button>
          ))}
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
        >
          {submitting ? "…" : "Log"}
        </button>
        {error && (
          <p className="w-full text-xs text-red-600" role="alert">
            {error}
          </p>
        )}
      </form>

      {/* Entries */}
      {entries.length === 0 ? (
        <p className="px-4 py-4 text-sm text-surface-500 italic">
          No water logged yet.
        </p>
      ) : (
        <ul className="divide-y divide-surface-100" aria-label="Water log entries">
          {entries.map((entry) => (
            <WaterLogRow key={entry.id} entry={entry} onDelete={onDeleteEntry} />
          ))}
        </ul>
      )}
    </div>
  );
}

function WaterLogRow({
  entry,
  onDelete,
}: {
  entry: WaterLogEntry;
  onDelete: (id: string) => Promise<void>;
}) {
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onDelete(entry.id);
    } finally {
      setDeleting(false);
    }
  }

  const time = new Date(entry.created_at).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <li className="flex items-center justify-between px-4 py-2.5">
      <div className="text-sm text-surface-700">
        <span className="font-medium">{entry.amount_ml} ml</span>
        <span className="ml-2 text-xs text-surface-500">{time}</span>
        {entry.notes && (
          <span className="ml-2 text-xs text-surface-500 italic">{entry.notes}</span>
        )}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {confirm ? (
          <>
            <button
              onClick={() => void handleDelete()}
              disabled={deleting}
              className="rounded px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 disabled:opacity-50"
            >
              {deleting ? "…" : "Remove"}
            </button>
            <button
              onClick={() => setConfirm(false)}
              className="rounded px-2 py-0.5 text-xs text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirm(true)}
            aria-label="Remove water entry"
            className="rounded p-1 text-surface-500 hover:text-red-500 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
          >
            <TrashIcon />
          </button>
        )}
      </div>
    </li>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function ChevronLeft() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
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

function WaterIcon() {
  return (
    <svg className="h-4 w-4 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2C6 10 4 14 4 17a8 8 0 0 0 16 0c0-3-2-7-8-15z" />
    </svg>
  );
}
