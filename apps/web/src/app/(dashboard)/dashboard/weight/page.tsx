"use client";

/**
 * Weight page — /dashboard/weight
 *
 * Features:
 * - Stats summary bar: latest, change, 7-day average
 * - SVG sparkline chart of the most-recent entries
 * - Log entry form (weight + unit, optional body fat, date, notes)
 * - Scrollable entry history list
 * - Delete with confirmation
 * - All WCAG 2.2 AA: accessible chart alt text, keyboard navigation
 */

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useWeight } from "@/features/weight/use-weight";
import { cn } from "@/lib/utils";
import type { WeightEntry } from "@/types/weight";

// ── Form schema ───────────────────────────────────────────────────────────────

const logSchema = z.object({
  weight: z.preprocess(
    (v) => (v === "" ? undefined : Number(v)),
    z.number({ required_error: "Weight is required" }).positive("Must be > 0").max(700)
  ),
  display_unit: z.enum(["kg", "lbs"]),
  body_fat_pct: z.preprocess(
    (v) => (v === "" || v === null || v === undefined ? undefined : Number(v)),
    z.number().min(0).max(100).optional()
  ),
  measured_at: z.string().min(1, "Date is required"),
  notes: z.string().max(500).optional().or(z.literal("")),
});

type LogFormData = z.infer<typeof logSchema>;

function todayISO(): string {
  return new Date().toISOString().split("T")[0]!;
}

// ── Sparkline chart ───────────────────────────────────────────────────────────

interface SparklineProps {
  entries: WeightEntry[]; // newest-first — we reverse for chart
  height?: number;
}

function Sparkline({ entries, height = 64 }: SparklineProps) {
  // Reverse so oldest is on the left
  const points = [...entries].reverse();
  if (points.length < 2) return null;

  const weights = points.map((e) => e.weight_kg);
  const minW = Math.min(...weights);
  const maxW = Math.max(...weights);
  const range = maxW - minW || 1;

  const W = 300;
  const H = height;
  const pad = 4;

  const coords = points.map((e, i) => {
    const x = pad + ((W - pad * 2) * i) / (points.length - 1);
    const y = H - pad - ((e.weight_kg - minW) / range) * (H - pad * 2);
    return { x, y };
  });

  const pathD = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  // Area fill below the line
  const areaD =
    pathD +
    ` L ${coords.at(-1)!.x.toFixed(1)} ${H} L ${coords[0]!.x.toFixed(1)} ${H} Z`;

  const latest = weights.at(-1)!;
  const earliest = weights[0]!;
  const trend = latest - earliest;

  return (
    <figure className="w-full" aria-label="Weight trend chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height }}
        role="img"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="wgrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill="url(#wgrad)" />
        <path
          d={pathD}
          fill="none"
          stroke="#6366f1"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Latest dot */}
        <circle
          cx={coords.at(-1)!.x}
          cy={coords.at(-1)!.y}
          r="3"
          fill="#6366f1"
        />
      </svg>
      <figcaption className="sr-only">
        Weight trend: from {earliest.toFixed(1)} kg to {latest.toFixed(1)} kg.
        Overall change: {trend > 0 ? "+" : ""}
        {trend.toFixed(1)} kg over {points.length} entries.
      </figcaption>
    </figure>
  );
}

// ── Stats bar ─────────────────────────────────────────────────────────────────

function StatBadge({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: "green" | "red" | "neutral";
}) {
  const colours = {
    green: "text-emerald-700",
    red: "text-red-600",
    neutral: "text-surface-900",
  };
  return (
    <div className="flex flex-col">
      <span className="text-xs text-surface-500">{label}</span>
      <span
        className={cn(
          "text-lg font-bold tabular-nums",
          colours[highlight ?? "neutral"]
        )}
      >
        {value}
      </span>
      {sub && <span className="text-xs text-surface-500">{sub}</span>}
    </div>
  );
}

// ── Log form ──────────────────────────────────────────────────────────────────

interface LogFormProps {
  onLog: (data: LogFormData) => Promise<void>;
}

function LogWeightForm({ onLog }: LogFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LogFormData>({
    resolver: zodResolver(logSchema),
    defaultValues: {
      display_unit: "kg",
      measured_at: todayISO(),
    },
  });

  async function onValid(data: LogFormData) {
    await onLog(data);
    reset({ display_unit: data.display_unit, measured_at: todayISO() });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Log weight</CardTitle>
      </CardHeader>
      <CardBody>
        <form onSubmit={handleSubmit(onValid)} noValidate className="space-y-3">
          {/* Weight + unit row */}
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                label="Weight"
                id="w-weight"
                type="number"
                step="0.1"
                min="0.1"
                placeholder="75.0"
                required
                error={errors.weight?.message}
                {...register("weight")}
              />
            </div>
            <div className="w-24 pt-0">
              <label
                htmlFor="w-unit"
                className="mb-1 block text-sm font-medium text-surface-700"
              >
                Unit
              </label>
              <select
                id="w-unit"
                {...register("display_unit")}
                className="w-full h-11 rounded-lg border border-surface-200 bg-white px-3 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="kg">kg</option>
                <option value="lbs">lbs</option>
              </select>
            </div>
          </div>

          {/* Date + body fat */}
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Date"
              id="w-date"
              type="date"
              error={errors.measured_at?.message}
              {...register("measured_at")}
            />
            <Input
              label="Body fat % (optional)"
              id="w-bf"
              type="number"
              step="0.1"
              min="0"
              max="100"
              placeholder="18.5"
              error={errors.body_fat_pct?.message}
              {...register("body_fat_pct")}
            />
          </div>

          {/* Notes */}
          <div>
            <label
              htmlFor="w-notes"
              className="mb-1 block text-sm font-medium text-surface-700"
            >
              Notes{" "}
              <span className="font-normal text-surface-500">(optional)</span>
            </label>
            <textarea
              id="w-notes"
              rows={2}
              placeholder="e.g. after morning run…"
              {...register("notes")}
              className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
            />
          </div>

          <Button type="submit" isLoading={isSubmitting} fullWidth>
            Save entry
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}

// ── Entry row ─────────────────────────────────────────────────────────────────

interface EntryRowProps {
  entry: WeightEntry;
  onDelete: (entry: WeightEntry) => void;
}

function EntryRow({ entry, onDelete }: EntryRowProps) {
  const displayWeight =
    entry.display_unit === "lbs" && entry.weight_lbs !== null
      ? `${entry.weight_lbs.toFixed(1)} lbs`
      : `${entry.weight_kg.toFixed(1)} kg`;

  const date = new Date(`${entry.measured_at}T00:00:00`).toLocaleDateString(
    undefined,
    { month: "short", day: "numeric", year: "numeric" }
  );

  return (
    <li className="flex items-center justify-between gap-3 py-3 border-b border-surface-100 last:border-0">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-surface-900 tabular-nums">
            {displayWeight}
          </span>
          <span className="text-xs text-surface-500">{entry.weight_kg.toFixed(2)} kg</span>
          {entry.bmi !== null && (
            <span className="text-xs text-surface-500">BMI {entry.bmi}</span>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-surface-500">
          <span>{date}</span>
          {entry.body_fat_pct !== null && (
            <span>{entry.body_fat_pct.toFixed(1)}% body fat</span>
          )}
          {entry.notes && (
            <span className="truncate italic">&ldquo;{entry.notes}&rdquo;</span>
          )}
        </div>
      </div>
      <button
        type="button"
        aria-label={`Delete entry from ${date}`}
        onClick={() => onDelete(entry)}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-surface-500 hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      </button>
    </li>
  );
}

// ── Delete confirm ────────────────────────────────────────────────────────────

function DeleteConfirm({
  entry,
  isLoading,
  onConfirm,
  onCancel,
}: {
  entry: WeightEntry | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!entry) return null;
  const date = new Date(`${entry.measured_at}T00:00:00`).toLocaleDateString(
    undefined,
    { month: "long", day: "numeric", year: "numeric" }
  );
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="del-weight-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div className="absolute inset-0 bg-black/40" aria-hidden="true" onClick={onCancel} />
      <div className="relative mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2 id="del-weight-title" className="text-base font-semibold text-surface-900">
          Delete entry?
        </h2>
        <p className="mt-2 text-sm text-surface-600">
          The entry from <span className="font-medium">{date}</span> (
          {entry.weight_kg.toFixed(1)} kg) will be permanently deleted.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} isLoading={isLoading}>
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WeightPage() {
  const { entries, total, stats, isLoading, error, logWeight, deleteEntry } =
    useWeight(50);
  const [deletingEntry, setDeletingEntry] = useState<WeightEntry | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);

  async function handleLog(data: LogFormData) {
    setLogError(null);
    try {
      await logWeight({
        weight: data.weight,
        display_unit: data.display_unit,
        body_fat_pct: data.body_fat_pct,
        measured_at: data.measured_at,
        notes: data.notes || undefined,
      });
    } catch (err) {
      setLogError(err instanceof Error ? err.message : "Failed to save entry");
      throw err;
    }
  }

  async function handleDelete() {
    if (!deletingEntry) return;
    setIsDeleting(true);
    try {
      await deleteEntry(deletingEntry.id);
    } finally {
      setIsDeleting(false);
      setDeletingEntry(null);
    }
  }

  const changeSign =
    stats.change_kg !== null
      ? stats.change_kg < 0
        ? "green"
        : stats.change_kg > 0
          ? "red"
          : "neutral"
      : "neutral";

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Weight</h1>
        <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
          Track your body weight and composition over time.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: log form */}
        <div className="lg:col-span-1">
          {logError && (
            <div
              role="alert"
              className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {logError}
            </div>
          )}
          <LogWeightForm onLog={handleLog} />
        </div>

        {/* Right column: stats + chart + history */}
        <div className="space-y-4 lg:col-span-2">
          {isLoading && (
            <div className="flex justify-center py-16">
              <LoadingSpinner size="lg" label="Loading weight history…" />
            </div>
          )}

          {!isLoading && error && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          {!isLoading && !error && stats.count === 0 && (
            <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-200 py-14 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-400">
                <svg
                  viewBox="0 0 24 24"
                  className="h-7 w-7"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18M3 12h18M3 18h18" />
                </svg>
              </div>
              <h2 className="text-base font-semibold text-surface-700">
                No entries yet
              </h2>
              <p className="mt-1 max-w-xs text-sm text-surface-500">
                Log your first weight entry to start tracking your trend.
              </p>
            </div>
          )}

          {!isLoading && !error && stats.count > 0 && (
            <>
              {/* Stats */}
              <Card>
                <CardBody className="flex flex-wrap gap-6">
                  <StatBadge
                    label="Latest"
                    value={
                      stats.latest_kg !== null
                        ? `${stats.latest_kg.toFixed(1)} kg`
                        : "—"
                    }
                    sub={
                      entries[0]?.bmi !== null && entries[0]?.bmi !== undefined
                        ? `BMI ${entries[0].bmi} (estimate)`
                        : undefined
                    }
                  />
                  <StatBadge
                    label="Change"
                    value={
                      stats.change_kg !== null
                        ? `${stats.change_kg > 0 ? "+" : ""}${stats.change_kg.toFixed(1)} kg`
                        : "—"
                    }
                    sub={`over ${stats.count} entries`}
                    highlight={changeSign}
                  />
                  <StatBadge
                    label="7-day avg"
                    value={
                      stats.moving_avg_7d_kg !== null
                        ? `${stats.moving_avg_7d_kg.toFixed(1)} kg`
                        : "—"
                    }
                  />
                  <StatBadge
                    label="Range"
                    value={
                      stats.min_kg !== null && stats.max_kg !== null
                        ? `${stats.min_kg.toFixed(1)} – ${stats.max_kg.toFixed(1)} kg`
                        : "—"
                    }
                  />
                </CardBody>
              </Card>

              {/* Chart */}
              {entries.length >= 2 && (
                <Card>
                  <CardHeader>
                    <CardTitle as="h3">Trend</CardTitle>
                  </CardHeader>
                  <CardBody className="pt-2">
                    <Sparkline entries={entries.slice(0, 30)} />
                  </CardBody>
                </Card>
              )}

              {/* History */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle as="h3">History</CardTitle>
                    <span className="text-xs text-surface-500">
                      {total} total entr{total !== 1 ? "ies" : "y"}
                    </span>
                  </div>
                </CardHeader>
                <CardBody className="pt-0 pb-2">
                  <ul aria-label="Weight entry history">
                    {entries.map((e) => (
                      <EntryRow
                        key={e.id}
                        entry={e}
                        onDelete={setDeletingEntry}
                      />
                    ))}
                  </ul>
                </CardBody>
              </Card>
            </>
          )}
        </div>
      </div>

      <DeleteConfirm
        entry={deletingEntry}
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => setDeletingEntry(null)}
      />
    </div>
  );
}
