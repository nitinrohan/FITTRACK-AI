"use client";

/**
 * DailyInsightCard - today's macro totals vs. the user's own targets, plus
 * an AI-written explanation and suggestions for any remaining meals.
 *
 * Accessibility: the bar chart is decorative (aria-hidden); a text summary
 * and a data table are the accessible alternative, matching the Progress
 * page chart convention.
 *
 * Safety: read-only. Never creates/edits/deletes data. Always labelled as
 * an estimate, and clearly not medical/dietitian advice.
 */

import { useId, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDailyInsight, useNutritionTargets } from "@/features/nutrition/use-nutrition";
import { cn } from "@/lib/utils";
import type { UpdateNutritionTargetPayload } from "@/types/nutrition";

interface DailyInsightCardProps {
  date: string;
  refreshKey: number;
}

export function DailyInsightCard({ date, refreshKey }: DailyInsightCardProps) {
  const { insight, isLoading, error, refresh } = useDailyInsight(date, refreshKey);
  const targets = useNutritionTargets();
  const [showTargetForm, setShowTargetForm] = useState(false);
  const tableId = useId();

  if (isLoading) {
    return (
      <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-700 dark:bg-surface-800">
        <p className="text-sm text-surface-500 dark:text-surface-400" role="status">
          Loading today&apos;s insight…
        </p>
      </div>
    );
  }

  if (error || !insight) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        {error ?? "Couldn't load nutrition insight."}
        <button
          onClick={() => void refresh()}
          className="ml-2 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const chartData = insight.comparisons.map((c) => ({
    metric: c.label,
    current: c.current,
    target: c.target ?? 0,
    unit: c.unit,
  }));

  const summary = insight.comparisons
    .filter((c) => c.target !== null)
    .map((c) => `${c.label} ${c.current}/${c.target} ${c.unit} (${c.percent_of_target}%)`)
    .join(" · ");

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-700 dark:bg-surface-800">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-surface-900 dark:text-surface-50">
          Today vs. your targets
        </h2>
        <button
          type="button"
          onClick={() => setShowTargetForm((v) => !v)}
          className="rounded-lg px-2.5 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-brand-400 dark:hover:bg-brand-950"
        >
          {targets.targets?.is_set ? "Edit targets" : "Set targets"}
        </button>
      </div>

      {showTargetForm && (
        <div className="mb-4">
          <TargetForm
            initial={targets.targets}
            onSave={async (payload) => {
              await targets.update(payload);
              await refresh();
              setShowTargetForm(false);
            }}
            onCancel={() => setShowTargetForm(false)}
          />
        </div>
      )}

      {!targets.targets?.is_set && !showTargetForm && (
        <p className="mb-3 text-xs text-surface-500 dark:text-surface-400">
          No personal targets set yet - comparisons below will fill in once you set one.
        </p>
      )}

      {/* Accessible text summary - always visible */}
      {summary && (
        <p className="mb-2 text-sm text-surface-700 dark:text-surface-200">{summary}</p>
      )}

      {/* Chart - decorative; summary + table are the accessible alternative */}
      <div className="h-48" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 8, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="metric" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={36} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="current" fill="#22c55e" radius={[2, 2, 0, 0]} name="Logged" />
            <Bar dataKey="target" fill="#cbd5e1" radius={[2, 2, 0, 0]} name="Target" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Data table - keyboard-accessible alternative to the chart */}
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-surface-500 hover:text-surface-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-400">
          Show data table
        </summary>
        <table className="mt-2 w-full text-left text-xs" id={tableId}>
          <caption className="sr-only">Today&apos;s macros vs targets</caption>
          <thead>
            <tr>
              <th scope="col" className="px-2 py-1 font-medium text-surface-600 dark:text-surface-200">Metric</th>
              <th scope="col" className="px-2 py-1 text-right font-medium text-surface-600 dark:text-surface-200">Logged</th>
              <th scope="col" className="px-2 py-1 text-right font-medium text-surface-600 dark:text-surface-200">Target</th>
              <th scope="col" className="px-2 py-1 text-right font-medium text-surface-600 dark:text-surface-200">Remaining</th>
            </tr>
          </thead>
          <tbody>
            {insight.comparisons.map((c) => (
              <tr key={c.metric} className="border-t border-surface-100 dark:border-surface-700">
                <td className="px-2 py-1 text-surface-700 dark:text-surface-300">{c.label}</td>
                <td className="px-2 py-1 text-right text-surface-900 dark:text-surface-100">
                  {c.current} {c.unit}
                </td>
                <td className="px-2 py-1 text-right text-surface-700 dark:text-surface-300">
                  {c.target !== null ? `${c.target} ${c.unit}` : "not set"}
                </td>
                <td className="px-2 py-1 text-right text-surface-700 dark:text-surface-300">
                  {c.remaining !== null ? `${c.remaining} ${c.unit}` : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      {/* AI narrative */}
      <div className="mt-4 border-t border-surface-100 pt-3 dark:border-surface-700">
        {insight.highlights.length > 0 && (
          <ul className="space-y-1 text-sm text-surface-700 dark:text-surface-200">
            {insight.highlights.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        )}
        {insight.suggestions.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium uppercase tracking-wide text-surface-500 dark:text-surface-400">
              Suggestions
            </p>
            <ul className="mt-1 space-y-1 text-sm text-surface-700 dark:text-surface-200">
              {insight.suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}
        {insight.encouragement && (
          <p className="mt-2 text-sm italic text-surface-600 dark:text-surface-300">
            {insight.encouragement}
          </p>
        )}
        <p className="mt-3 text-xs text-surface-400 dark:text-surface-500">
          {insight.disclaimer}
          {!insight.ai_available && insight.message ? ` ${insight.message}` : ""}
        </p>
      </div>
    </div>
  );
}

// ── Targets quick-set form ───────────────────────────────────────────────────

function TargetForm({
  initial,
  onSave,
  onCancel,
}: {
  initial: { calorie_target_kcal: number | null; protein_target_g: number | null; carbs_target_g: number | null; fat_target_g: number | null; fiber_target_g: number | null } | null;
  onSave: (payload: UpdateNutritionTargetPayload) => Promise<void>;
  onCancel: () => void;
}) {
  const fid = useId();
  const [calories, setCalories] = useState(initial?.calorie_target_kcal?.toString() ?? "");
  const [protein, setProtein] = useState(initial?.protein_target_g?.toString() ?? "");
  const [carbs, setCarbs] = useState(initial?.carbs_target_g?.toString() ?? "");
  const [fat, setFat] = useState(initial?.fat_target_g?.toString() ?? "");
  const [fiber, setFiber] = useState(initial?.fiber_target_g?.toString() ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toNumOrNull(v: string): number | null {
    const n = parseFloat(v);
    return v.trim() === "" || isNaN(n) ? null : n;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave({
        calorie_target_kcal: toNumOrNull(calories),
        protein_target_g: toNumOrNull(protein),
        carbs_target_g: toNumOrNull(carbs),
        fat_target_g: toNumOrNull(fat),
        fiber_target_g: toNumOrNull(fiber),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save targets.");
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="rounded-lg border border-surface-200 bg-surface-50 p-3 dark:border-surface-700 dark:bg-surface-900"
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <TargetField id={`${fid}-cal`} label="Calories (kcal)" value={calories} onChange={setCalories} />
        <TargetField id={`${fid}-pro`} label="Protein (g)" value={protein} onChange={setProtein} />
        <TargetField id={`${fid}-carb`} label="Carbs (g)" value={carbs} onChange={setCarbs} />
        <TargetField id={`${fid}-fat`} label="Fat (g)" value={fat} onChange={setFat} />
        <TargetField id={`${fid}-fiber`} label="Fiber (g)" value={fiber} onChange={setFiber} />
      </div>
      {error && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
      <div className="mt-2 flex items-center gap-2">
        <button
          type="submit"
          disabled={saving}
          className={cn(
            "rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50"
          )}
        >
          {saving ? "Saving…" : "Save targets"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-3 py-1.5 text-xs text-surface-600 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-700"
        >
          Cancel
        </button>
      </div>
      <p className="mt-2 text-[11px] text-surface-500 dark:text-surface-400">
        Leave a field blank to clear that target. These are your own goals - FitTrack never sets or guesses one for you.
      </p>
    </form>
  );
}

function TargetField({
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
