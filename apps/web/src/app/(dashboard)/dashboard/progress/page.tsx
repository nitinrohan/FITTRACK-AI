"use client";

/**
 * /dashboard/progress - Progress charts.
 *
 * Each metric is shown as a chart PLUS an accessible alternative: a one-line
 * text summary (always visible) and a collapsible data table. The chart SVG is
 * marked decorative (aria-hidden) so assistive tech reads the summary/table
 * instead - meeting the "charts need a text alternative" accessibility rule.
 */

import { useId } from "react";
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
import { cn } from "@/lib/utils";
import { useProgress } from "@/features/progress/use-progress";
import type { MetricSeries } from "@/types/progress";

const RANGES = [
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

export default function ProgressPage() {
  const { data, isLoading, error, days, setDays, reload } = useProgress(30);

  const hasAny =
    !!data && (!!data.weight || !!data.workouts || !!data.calories);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Progress</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Your trends over time - weight, workouts, and calories.
          </p>
        </div>
        <div
          className="flex gap-1 rounded-xl border border-surface-200 bg-surface-50 p-1 dark:border-surface-700 dark:bg-surface-800"
          role="group"
          aria-label="Select time range"
        >
          {RANGES.map((r) => (
            <button
              key={r.days}
              type="button"
              aria-pressed={days === r.days}
              onClick={() => setDays(r.days)}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
                days === r.days
                  ? "bg-white text-surface-900 shadow-sm dark:bg-surface-700 dark:text-surface-50"
                  : "text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200",
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => reload()}
            className="shrink-0 rounded-lg border border-red-300 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div role="status" className="py-16 text-center text-sm text-surface-500 dark:text-surface-400">
          Loading your progress…
        </div>
      ) : !hasAny ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data?.weight && <MetricChartCard series={data.weight} chartType="line" />}
          {data?.calories && <MetricChartCard series={data.calories} chartType="line" />}
          {data?.workouts && (
            <div className="lg:col-span-2">
              <MetricChartCard series={data.workouts} chartType="bar" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Metric card (chart + accessible summary + data table) ───────────────────────

function MetricChartCard({
  series,
  chartType,
}: {
  series: MetricSeries;
  chartType: "line" | "bar";
}) {
  const tableId = useId();
  const summary = summarise(series);

  return (
    <section
      aria-label={series.label}
      className="rounded-xl border border-surface-200 bg-white p-5 dark:border-surface-700 dark:bg-surface-800"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-surface-500">
        {series.label}
      </h2>

      {/* Accessible text summary - always visible */}
      <p className="mt-1 text-sm text-surface-700 dark:text-surface-200">{summary}</p>

      {/* Chart - decorative; the summary + table are the accessible alternative */}
      <div className="mt-3 h-56" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "line" ? (
            <LineChart data={series.points} margin={{ top: 5, right: 8, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={shortDate} minTickGap={24} />
              <YAxis tick={{ fontSize: 10 }} width={40} domain={["auto", "auto"]} />
              <Tooltip labelFormatter={shortDate} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 2 }}
                name={series.unit}
              />
            </LineChart>
          ) : (
            <BarChart data={series.points} margin={{ top: 5, right: 8, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={shortDate} minTickGap={24} />
              <YAxis tick={{ fontSize: 10 }} width={40} allowDecimals={false} />
              <Tooltip labelFormatter={shortDate} />
              <Bar dataKey="value" fill="#22c55e" radius={[2, 2, 0, 0]} name={series.unit} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Data table - keyboard-accessible alternative to the chart */}
      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-surface-500 hover:text-surface-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-400">
          Show data table
        </summary>
        <div className="mt-2 max-h-48 overflow-auto rounded-lg border border-surface-200 dark:border-surface-700">
          <table className="w-full text-left text-xs" id={tableId}>
            <caption className="sr-only">{series.label} data over time</caption>
            <thead className="sticky top-0 bg-surface-50 dark:bg-surface-700">
              <tr>
                <th scope="col" className="px-3 py-1.5 font-medium text-surface-600 dark:text-surface-200">
                  Date
                </th>
                <th scope="col" className="px-3 py-1.5 text-right font-medium text-surface-600 dark:text-surface-200">
                  {series.label} ({series.unit})
                </th>
              </tr>
            </thead>
            <tbody>
              {series.points.map((p) => (
                <tr key={p.date} className="border-t border-surface-100 dark:border-surface-700">
                  <td className="px-3 py-1.5 text-surface-700 dark:text-surface-300">{p.date}</td>
                  <td className="px-3 py-1.5 text-right text-surface-900 dark:text-surface-100">
                    {p.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

// ── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-surface-300 py-16 text-center dark:border-surface-700">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 dark:bg-brand-950">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6 text-brand-600 dark:text-brand-400" aria-hidden="true">
          <path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M7 14l3-3 3 3 5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="mt-3 font-semibold text-surface-900 dark:text-surface-50">No trends yet</p>
      <p className="mt-1 max-w-xs text-sm text-surface-500 dark:text-surface-400">
        Log some weight, workouts, or meals and your progress charts will appear here.
      </p>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function shortDate(iso: string): string {
  // "2026-06-24" -> "Jun 24"
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function summarise(s: MetricSeries): string {
  if (s.count === 0) return "No data in this range.";
  if (s.metric === "weight") {
    const dir = (s.change ?? 0) <= 0 ? "down" : "up";
    const amt = Math.abs(s.change ?? 0);
    return `${s.first} → ${s.latest} ${s.unit} (${dir} ${amt}), average ${s.average}.`;
  }
  if (s.metric === "workouts") {
    return `${s.total} workouts over ${s.count} days; busiest day ${s.maximum}.`;
  }
  // calories
  return `Average ${s.average} ${s.unit} across ${s.count} logged days (range ${s.minimum}-${s.maximum}).`;
}
