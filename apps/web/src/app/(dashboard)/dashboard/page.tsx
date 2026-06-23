"use client";

/**
 * Dashboard page — /dashboard
 *
 * Widgets:
 *   - Weight trend line chart (30 days, Recharts)
 *   - Workout frequency bar chart (28 days, Recharts)
 *   - Today's nutrition macro ring + water
 *   - Active goals progress bars
 *   - Latest measurements snapshot
 *   - Quick-action buttons
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useAuth } from "@/features/auth/use-auth";
import { aiApi } from "@/lib/ai-api";
import { dashboardApi } from "@/lib/dashboard-api";
import type { WeeklySummaryResponse } from "@/types/ai";
import type {
  DashboardSummary,
  GoalSummaryItem,
  GoalsSummarySection,
  LatestMeasurementSection,
  TodayNutritionSection,
  WeightTrendSection,
  WorkoutFrequencySection,
} from "@/types/dashboard";

// ── Hook ──────────────────────────────────────────────────────────────────────

function useDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const summary = await dashboardApi.getSummary();
      setData(summary);
    } catch {
      setError("Failed to load dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error };
}

// ── Shared card wrapper ────────────────────────────────────────────────────────

function Widget({
  title,
  href,
  linkLabel,
  children,
}: {
  title: string;
  href?: string;
  linkLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-[180px] flex-col gap-3 rounded-xl border border-surface-200 bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-surface-500">
        {title}
      </p>
      <div className="flex-1">{children}</div>
      {href && linkLabel && (
        <Link
          href={href}
          className="text-xs font-medium text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded self-start"
        >
          {linkLabel} →
        </Link>
      )}
    </div>
  );
}

// ── Weight trend chart ────────────────────────────────────────────────────────

function WeightTrendWidget({ data }: { data: WeightTrendSection }) {
  const hasData = data.points.length > 0;

  // Abbreviate x-axis labels to "Jun 1" style
  function formatDate(dateStr: string) {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  // Show every Nth tick so the axis doesn't crowd
  const ticks = data.points
    .filter((_, i) => i % Math.ceil(data.points.length / 5) === 0)
    .map((p) => p.date);

  const yVals = data.points.map((p) => p.weight_kg);
  const yMin = yVals.length ? Math.floor(Math.min(...yVals) - 1) : 0;
  const yMax = yVals.length ? Math.ceil(Math.max(...yVals) + 1) : 100;

  return (
    <Widget
      title="Weight (30 days)"
      href="/dashboard/weight"
      linkLabel="View history"
    >
      {!hasData ? (
        <EmptyWidgetState message="No weight entries yet." />
      ) : (
        <>
          <div className="mb-2 flex items-baseline gap-3">
            {data.latest_kg !== null && (
              <span className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                {data.latest_kg.toFixed(1)}{" "}
                <span className="text-sm font-medium text-surface-500">kg</span>
              </span>
            )}
            {data.change_kg !== null && (
              <span
                className={
                  data.change_kg < -0.1
                    ? "text-xs font-medium text-emerald-600"
                    : data.change_kg > 0.1
                      ? "text-xs font-medium text-red-500"
                      : "text-xs font-medium text-surface-500"
                }
              >
                {data.change_kg > 0 ? "+" : ""}
                {data.change_kg.toFixed(1)} kg
              </span>
            )}
            {data.moving_avg_7d_kg !== null && (
              <span className="text-xs text-surface-500">
                7d avg {data.moving_avg_7d_kg.toFixed(1)} kg
              </span>
            )}
          </div>

          <ResponsiveContainer width="100%" height={140}>
            <LineChart
              data={data.points}
              margin={{ top: 4, right: 4, bottom: 0, left: -20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                ticks={ticks}
                tickFormatter={formatDate}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[yMin, yMax]}
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v: number) => [`${v.toFixed(1)} kg`, "Weight"]}
                labelFormatter={formatDate}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid #e5e7eb",
                }}
              />
              <Line
                type="monotone"
                dataKey="weight_kg"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </Widget>
  );
}

// ── Workout frequency chart ───────────────────────────────────────────────────

function WorkoutFrequencyWidget({ data }: { data: WorkoutFrequencySection }) {
  function formatDate(dateStr: string) {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  // Show every ~5th date on the axis
  const ticks = data.points
    .filter((_, i) => i % 7 === 0 || i === data.points.length - 1)
    .map((p) => p.date);

  return (
    <Widget
      title="Workouts (28 days)"
      href="/dashboard/workouts"
      linkLabel="View workouts"
    >
      <div className="mb-2 flex items-baseline gap-3">
        <span className="text-2xl font-bold text-surface-900 dark:text-surface-50">
          {data.total_28d}
        </span>
        <span className="text-xs text-surface-500">completed</span>
        {data.last_workout_date && (
          <span className="text-xs text-surface-500">
            last: {formatDate(data.last_workout_date)}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={120}>
        <BarChart
          data={data.points}
          margin={{ top: 4, right: 4, bottom: 0, left: -20 }}
          barSize={6}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="date"
            ticks={ticks}
            tickFormatter={formatDate}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(v: number) => [v, "Workouts"]}
            labelFormatter={formatDate}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
            }}
          />
          <Bar dataKey="count" fill="#6366f1" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Widget>
  );
}

// ── Today's nutrition ─────────────────────────────────────────────────────────

function MacroBar({
  label,
  value,
  max,
  color,
  unit = "g",
}: {
  label: string;
  value: number;
  max: number;
  color: string;
  unit?: string;
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-surface-500">
        <span>{label}</span>
        <span className="font-medium text-surface-700">
          {value.toFixed(0)}
          {unit}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-100">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemax={max}
          aria-label={label}
        />
      </div>
    </div>
  );
}

function TodayNutritionWidget({ data }: { data: TodayNutritionSection }) {
  return (
    <Widget
      title="Today's nutrition"
      href="/dashboard/nutrition"
      linkLabel="Open nutrition log"
    >
      <div className="mb-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-surface-900 dark:text-surface-50">
          {data.calories_kcal.toFixed(0)}
        </span>
        <span className="text-xs text-surface-500">kcal</span>
      </div>

      <div className="space-y-2">
        <MacroBar
          label="Protein"
          value={data.protein_g}
          max={200}
          color="#6366f1"
        />
        <MacroBar
          label="Carbs"
          value={data.carbs_g}
          max={300}
          color="#f59e0b"
        />
        <MacroBar
          label="Fat"
          value={data.fat_g}
          max={100}
          color="#10b981"
        />
        <MacroBar
          label="Water"
          value={data.water_ml}
          max={2500}
          color="#38bdf8"
          unit="ml"
        />
      </div>
    </Widget>
  );
}

// ── Goals progress ────────────────────────────────────────────────────────────

function GoalProgressItem({ goal }: { goal: GoalSummaryItem }) {
  const pct = goal.progress_pct ?? 0;
  const clipped = Math.min(Math.max(pct, 0), 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="truncate text-xs text-surface-700">{goal.title}</span>
        <span className="shrink-0 text-xs font-medium text-surface-500">
          {clipped.toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-surface-100">
        <div
          className="h-1.5 rounded-full bg-brand-500 transition-all duration-500"
          style={{ width: `${clipped}%` }}
          role="progressbar"
          aria-valuenow={clipped}
          aria-valuemax={100}
          aria-label={goal.title}
        />
      </div>
    </div>
  );
}

function GoalsWidget({ data }: { data: GoalsSummarySection }) {
  return (
    <Widget
      title="Active goals"
      href="/dashboard/goals"
      linkLabel="View all goals"
    >
      <div className="mb-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-surface-900 dark:text-surface-50">{data.count}</span>
        <span className="text-xs text-surface-500">active</span>
        {data.avg_progress_pct !== null && (
          <span className="text-xs text-surface-500">
            · {data.avg_progress_pct.toFixed(0)}% avg
          </span>
        )}
      </div>
      <div className="space-y-3">
        {data.goals.slice(0, 5).map((g) => (
          <GoalProgressItem key={g.id} goal={g} />
        ))}
      </div>
    </Widget>
  );
}

// ── Latest measurements ───────────────────────────────────────────────────────

const MEAS_LABELS: Partial<Record<keyof LatestMeasurementSection, string>> = {
  waist_cm: "Waist",
  chest_cm: "Chest",
  hips_cm: "Hips",
  neck_cm: "Neck",
  left_arm_cm: "L. arm",
  right_arm_cm: "R. arm",
  left_thigh_cm: "L. thigh",
  right_thigh_cm: "R. thigh",
};

function LatestMeasurementWidget({
  data,
}: {
  data: LatestMeasurementSection;
}) {
  const fields = Object.keys(MEAS_LABELS) as (keyof LatestMeasurementSection)[];
  const recorded = fields.filter((k) => data[k] != null);

  function formatDate(dateStr: string) {
    return new Date(dateStr + "T12:00:00").toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  return (
    <Widget
      title="Latest measurements"
      href="/dashboard/measurements"
      linkLabel="View all"
    >
      <p className="mb-3 text-xs text-surface-500">{formatDate(data.date)}</p>
      {recorded.length === 0 ? (
        <p className="text-sm text-surface-500 italic">No values recorded.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {recorded.map((k) => (
            <div key={k as string} className="rounded-lg bg-surface-50 px-3 py-2">
              <p className="text-[11px] text-surface-500">
                {MEAS_LABELS[k]}
              </p>
              <p className="text-sm font-semibold text-surface-800">
                {(data[k] as number).toFixed(1)} cm
              </p>
            </div>
          ))}
        </div>
      )}
    </Widget>
  );
}

// ── AI insights widget ────────────────────────────────────────────────────────

type AISummaryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; data: WeeklySummaryResponse; dismissed: boolean }
  | { status: "error"; message: string };

function AIInsightsWidget() {
  const [state, setState] = useState<AISummaryState>({ status: "idle" });

  async function generate() {
    setState({ status: "loading" });
    try {
      const data = await aiApi.getWeeklySummary();
      setState({ status: "done", data, dismissed: false });
    } catch {
      setState({ status: "error", message: "Could not generate summary." });
    }
  }

  async function dismiss() {
    if (state.status !== "done") return;
    if (state.data.log_id) {
      try {
        await aiApi.recordDecision({ log_id: state.data.log_id, accepted: false });
      } catch {
        // best-effort
      }
    }
    setState({ status: "idle" });
  }

  async function accept() {
    if (state.status !== "done") return;
    if (state.data.log_id) {
      try {
        await aiApi.recordDecision({ log_id: state.data.log_id, accepted: true });
      } catch {
        // best-effort
      }
    }
    setState((prev) =>
      prev.status === "done" ? { ...prev, dismissed: true } : prev
    );
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SparklesIcon />
          <p className="text-sm font-semibold text-surface-800">AI weekly summary</p>
          {state.status !== "idle" && !("dismissed" in state && state.dismissed) && (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-600">
              {state.status === "loading"
                ? "Generating…"
                : state.status === "done" && state.data.ai_available
                  ? "AI"
                  : state.status === "done"
                    ? "Rule-based"
                    : ""}
            </span>
          )}
        </div>

        {state.status === "idle" && (
          <button
            onClick={() => void generate()}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
          >
            Generate
          </button>
        )}
        {state.status === "done" && !state.dismissed && (
          <button
            onClick={() => void generate()}
            className="text-xs text-surface-500 hover:text-surface-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
          >
            Regenerate
          </button>
        )}
      </div>

      {/* Idle */}
      {state.status === "idle" && (
        <p className="mt-3 text-sm text-surface-500">
          Get a personalised review of your last 7 days — workouts, nutrition,
          weight, and goals.
        </p>
      )}

      {/* Loading */}
      {state.status === "loading" && (
        <div className="mt-4 flex items-center gap-2 text-sm text-surface-500">
          <LoadingSpinner size="sm" label="Generating summary…" />
          <span>Analysing your week…</span>
        </div>
      )}

      {/* Error */}
      {state.status === "error" && (
        <div className="mt-3 text-sm text-red-600">
          {state.message}{" "}
          <button
            onClick={() => void generate()}
            className="underline hover:no-underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
          >
            Try again
          </button>
        </div>
      )}

      {/* Result */}
      {state.status === "done" && !state.dismissed && (
        <div className="mt-4 space-y-4">
          {/* Encouragement */}
          {state.data.encouragement && (
            <p className="text-sm font-medium text-brand-700 italic">
              &ldquo;{state.data.encouragement}&rdquo;
            </p>
          )}

          {/* Highlights */}
          {state.data.highlights.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-surface-500">
                Highlights
              </p>
              <ul className="space-y-1.5">
                {state.data.highlights.map((h, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-surface-700">
                    <span className="mt-0.5 shrink-0 text-emerald-500">✓</span>
                    {h}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions */}
          {state.data.suggestions.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-surface-500">
                Suggestions for next week
              </p>
              <ul className="space-y-1.5">
                {state.data.suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-surface-700">
                    <span className="mt-0.5 shrink-0 text-brand-500">→</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Data snapshot */}
          <details className="text-xs text-surface-500">
            <summary className="cursor-pointer hover:text-surface-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded">
              Data used
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3">
              {[
                ["Week", `${state.data.data_snapshot.week_start} – ${state.data.data_snapshot.week_end}`],
                ["Weight entries", String(state.data.data_snapshot.weight_entries)],
                ["Workouts", String(state.data.data_snapshot.workouts_completed)],
                ["Food log days", `${state.data.data_snapshot.food_log_days}/7`],
                ["Water log days", `${state.data.data_snapshot.water_log_days}/7`],
                ["Active goals", String(state.data.data_snapshot.active_goals)],
              ].map(([label, value]) => (
                <div key={label}>
                  <span className="font-medium">{label}:</span> {value}
                </div>
              ))}
            </div>
          </details>

          {/* Accept / dismiss */}
          <div className="flex items-center gap-2 pt-1 border-t border-surface-100">
            <button
              onClick={() => void accept()}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
            >
              Helpful — thanks!
            </button>
            <button
              onClick={() => void dismiss()}
              className="rounded-lg px-3 py-1.5 text-xs text-surface-500 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Accepted / dismissed confirmation */}
      {state.status === "done" && state.dismissed && (
        <p className="mt-3 text-sm text-surface-500">
          Summary dismissed.{" "}
          <button
            onClick={() => void generate()}
            className="text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
          >
            Generate a new one
          </button>
        </p>
      )}
    </div>
  );
}

function SparklesIcon() {
  return (
    <svg
      className="h-4 w-4 text-brand-500"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3l1.09 3.26L16.5 7.5l-3.41 1.24L12 12l-1.09-3.26L7.5 7.5l3.41-1.24L12 3z" />
      <path d="M5 13l.74 2.26L8 16l-2.26.74L5 19l-.74-2.26L2 16l2.26-.74L5 13z" />
      <path d="M19 13l.74 2.26L22 16l-2.26.74L19 19l-.74-2.26L16 16l2.26-.74L19 13z" />
    </svg>
  );
}

// ── Quick actions ─────────────────────────────────────────────────────────────

const QUICK_ACTIONS = [
  { href: "/dashboard/weight", label: "Log weight" },
  { href: "/dashboard/workouts", label: "Start workout" },
  { href: "/dashboard/nutrition", label: "Log food" },
  { href: "/dashboard/goals", label: "New goal" },
] as const;

function QuickActions() {
  return (
    <div className="flex flex-wrap gap-2">
      {QUICK_ACTIONS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className="rounded-xl border border-surface-200 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 hover:bg-surface-50 hover:border-brand-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
        >
          {label}
        </Link>
      ))}
    </div>
  );
}

// ── Empty states ──────────────────────────────────────────────────────────────

function EmptyWidgetState({ message }: { message: string }) {
  return (
    <p className="flex flex-1 items-center justify-center py-8 text-center text-sm text-surface-500 italic">
      {message}
    </p>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, error } = useDashboard();

  const name = user?.profile?.display_name ?? "";
  const greeting = name ? `Welcome back, ${name}!` : "Welcome back!";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">{greeting}</h1>
        <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
          Here&rsquo;s your fitness snapshot.
        </p>
      </div>

      {/* Quick actions */}
      <QuickActions />

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading dashboard…" />
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Widgets */}
      {!isLoading && !error && data && (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Weight trend */}
          {data.weight_trend ? (
            <WeightTrendWidget data={data.weight_trend} />
          ) : (
            <Widget
              title="Weight (30 days)"
              href="/dashboard/weight"
              linkLabel="Start tracking"
            >
              <EmptyWidgetState message="No weight entries yet." />
            </Widget>
          )}

          {/* Workout frequency */}
          {data.workout_frequency ? (
            <WorkoutFrequencyWidget data={data.workout_frequency} />
          ) : (
            <Widget
              title="Workouts (28 days)"
              href="/dashboard/workouts"
              linkLabel="Log first workout"
            >
              <EmptyWidgetState message="No completed workouts yet." />
            </Widget>
          )}

          {/* Today's nutrition */}
          {data.today_nutrition ? (
            <TodayNutritionWidget data={data.today_nutrition} />
          ) : (
            <Widget
              title="Today's nutrition"
              href="/dashboard/nutrition"
              linkLabel="Open nutrition log"
            >
              <EmptyWidgetState message="Nothing logged today." />
            </Widget>
          )}

          {/* Goals */}
          {data.goals ? (
            <GoalsWidget data={data.goals} />
          ) : (
            <Widget
              title="Active goals"
              href="/dashboard/goals"
              linkLabel="Set your first goal"
            >
              <EmptyWidgetState message="No active goals." />
            </Widget>
          )}

          {/* Latest measurements — spans full width on large screens */}
          {data.latest_measurement && (
            <div className="lg:col-span-2">
              <LatestMeasurementWidget data={data.latest_measurement} />
            </div>
          )}

          {/* AI insights — always shown, spans full width */}
          <div className="lg:col-span-2">
            <AIInsightsWidget />
          </div>
        </div>
      )}

      {/* Empty overall state — no data at all */}
      {!isLoading && !error && data && isAllEmpty(data) && (
        <div className="rounded-xl border border-dashed border-surface-300 bg-white px-6 py-12 text-center">
          <h3 className="text-sm font-medium text-surface-700">
            Your dashboard is ready
          </h3>
          <p className="mt-1 text-sm text-surface-500">
            Start by logging your weight, a workout, or your first meal.
          </p>
        </div>
      )}
    </div>
  );
}

function isAllEmpty(data: DashboardSummary): boolean {
  return (
    data.weight_trend === null &&
    data.workout_frequency === null &&
    data.today_nutrition === null &&
    data.goals === null &&
    data.latest_measurement === null
  );
}
