"use client";

/**
 * /dashboard/measurements — Body measurements tracking page.
 *
 * Features:
 *   - "Current" snapshot card showing the most-recent value per field
 *   - Log form with measurement fields grouped by body area
 *   - Unit toggle: cm / inches
 *   - History list with delete confirmation
 *   - All states: loading, empty, error
 */

import { useState } from "react";
import { useMeasurements } from "@/features/measurements/use-measurements";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { cn } from "@/lib/utils";
import type { BodyMeasurement, DisplayUnit, MeasurementFieldKey } from "@/types/measurements";
import {
  MEASUREMENT_FIELD_KEYS,
  MEASUREMENT_GROUPS,
  MEASUREMENT_LABELS,
  formatMeasurement,
} from "@/types/measurements";

// ── Date helper ───────────────────────────────────────────────────────────────

function todayISO(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T12:00:00").toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MeasurementsPage() {
  const {
    entries,
    total,
    latest,
    isLoading,
    error,
    refresh,
    logMeasurement,
    deleteMeasurement,
  } = useMeasurements(30);

  const [unit, setUnit] = useState<DisplayUnit>("cm");
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-surface-900 dark:text-surface-50">
            Body Measurements
          </h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Track circumference measurements over time
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Unit toggle */}
          <UnitToggle unit={unit} onChange={setUnit} />

          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
          >
            <PlusIcon />
            Log measurements
          </button>
        </div>
      </div>

      {/* Log form */}
      {showForm && (
        <LogForm
          unit={unit}
          onSubmit={async (payload) => {
            await logMeasurement(payload);
            setShowForm(false);
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading measurements…" />
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

      {!isLoading && !error && (
        <div className="space-y-6">
          {/* Current snapshot */}
          {latest ? (
            <SnapshotCard entry={latest} unit={unit} />
          ) : (
            <EmptyState onLog={() => setShowForm(true)} />
          )}

          {/* History */}
          {entries.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-medium text-surface-500">
                History ({total} {total === 1 ? "entry" : "entries"})
              </h2>
              <div className="space-y-3">
                {entries.map((entry) => (
                  <EntryCard
                    key={entry.id}
                    entry={entry}
                    unit={unit}
                    onDelete={deleteMeasurement}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Unit toggle ───────────────────────────────────────────────────────────────

function UnitToggle({
  unit,
  onChange,
}: {
  unit: DisplayUnit;
  onChange: (u: DisplayUnit) => void;
}) {
  return (
    <div
      role="group"
      aria-label="Display unit"
      className="flex rounded-lg border border-surface-200 bg-white p-0.5 text-xs font-medium"
    >
      {(["cm", "in"] as DisplayUnit[]).map((u) => (
        <button
          key={u}
          onClick={() => onChange(u)}
          aria-pressed={unit === u}
          className={cn(
            "rounded-md px-3 py-1.5 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
            unit === u
              ? "bg-brand-600 text-white"
              : "text-surface-600 hover:bg-surface-100"
          )}
        >
          {u}
        </button>
      ))}
    </div>
  );
}

// ── Snapshot card ─────────────────────────────────────────────────────────────

function SnapshotCard({
  entry,
  unit,
}: {
  entry: BodyMeasurement;
  unit: DisplayUnit;
}) {
  const populated = MEASUREMENT_FIELD_KEYS.filter(
    (k) => (entry[k] ?? null) !== null
  );

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-medium text-surface-900">Current measurements</h2>
        <span className="text-xs text-surface-500">
          {formatDate(entry.measured_at)}
        </span>
      </div>

      {populated.length === 0 ? (
        <p className="text-sm text-surface-500 italic">No values recorded.</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {MEASUREMENT_GROUPS.map((group) => {
            const groupFields = group.fields.filter(
              (f) => (entry[f] ?? null) !== null
            );
            if (groupFields.length === 0) return null;
            return (
              <div key={group.label} className="col-span-full">
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-surface-500">
                  {group.label}
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {groupFields.map((field) => {
                    const val = entry[field];
                    if (val == null) return null;
                    return (
                      <div
                        key={field}
                        className="rounded-lg bg-surface-50 px-3 py-2"
                      >
                        <p className="text-[11px] text-surface-500">
                          {MEASUREMENT_LABELS[field]}
                        </p>
                        <p className="mt-0.5 text-base font-semibold text-surface-900">
                          {formatMeasurement(val, unit)}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Entry card (history) ──────────────────────────────────────────────────────

function EntryCard({
  entry,
  unit,
  onDelete,
}: {
  entry: BodyMeasurement;
  unit: DisplayUnit;
  onDelete: (id: string) => Promise<void>;
}) {
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const populated = MEASUREMENT_FIELD_KEYS.filter(
    (k) => (entry[k] ?? null) !== null
  );
  // Show up to 4 fields in collapsed view
  const preview = populated.slice(0, 4);

  async function handleDelete() {
    setDeleting(true);
    try {
      await onDelete(entry.id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-surface-700">
            {formatDate(entry.measured_at)}
            <span className="ml-2 text-xs font-normal text-surface-500">
              {entry.recorded_count} measurement
              {entry.recorded_count !== 1 ? "s" : ""}
            </span>
          </p>

          {/* Preview row */}
          <div className="mt-1.5 flex flex-wrap gap-3">
            {(expanded ? populated : preview).map((field) => {
              const val = entry[field];
              if (val == null) return null;
              return (
                <span key={field} className="text-xs text-surface-600">
                  <span className="font-medium">{MEASUREMENT_LABELS[field]}:</span>{" "}
                  {formatMeasurement(val, unit)}
                </span>
              );
            })}
            {!expanded && populated.length > 4 && (
              <button
                onClick={() => setExpanded(true)}
                className="text-xs text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
              >
                +{populated.length - 4} more
              </button>
            )}
            {expanded && populated.length > 4 && (
              <button
                onClick={() => setExpanded(false)}
                className="text-xs text-surface-500 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
              >
                Show less
              </button>
            )}
          </div>

          {entry.notes && (
            <p className="mt-1 text-xs text-surface-500 italic">{entry.notes}</p>
          )}
        </div>

        {/* Delete */}
        <div className="flex shrink-0 items-center gap-1">
          {confirm ? (
            <>
              <button
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 disabled:opacity-50"
              >
                {deleting ? "…" : "Delete"}
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
              aria-label="Delete entry"
              className="rounded p-1 text-surface-500 hover:text-red-500 hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
            >
              <TrashIcon />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Log form ──────────────────────────────────────────────────────────────────

interface LogFormProps {
  unit: DisplayUnit;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

function LogForm({ unit, onSubmit, onCancel }: LogFormProps) {
  const [values, setValues] = useState<Partial<Record<MeasurementFieldKey, string>>>({});
  const [date, setDate] = useState(todayISO);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateField(key: MeasurementFieldKey, raw: string) {
    setValues((v) => ({ ...v, [key]: raw }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Build payload — convert from display unit to cm
    const payload: Record<string, unknown> = {
      measured_at: date,
      notes: notes || undefined,
    };

    let hasAny = false;
    for (const key of MEASUREMENT_FIELD_KEYS) {
      const raw = values[key];
      if (raw === undefined || raw === "") continue;
      const num = parseFloat(raw);
      if (isNaN(num) || num <= 0) {
        setError(`Invalid value for ${MEASUREMENT_LABELS[key]}.`);
        return;
      }
      // Convert inches → cm if needed
      const cm = unit === "in" ? Math.round(num * 2.54 * 10) / 10 : num;
      if (cm > 300) {
        setError(`${MEASUREMENT_LABELS[key]} value is too large (max 300 cm).`);
        return;
      }
      payload[key] = cm;
      hasAny = true;
    }

    if (!hasAny) {
      setError("Enter at least one measurement.");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save.");
      setSubmitting(false);
    }
  }

  const placeholder = unit === "in" ? "e.g. 31.5" : "e.g. 80.0";

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="rounded-xl border border-surface-200 bg-white p-5 space-y-5"
    >
      <h2 className="font-medium text-surface-900">Log measurements</h2>

      {/* Date + notes */}
      <div className="flex flex-wrap gap-4">
        <div>
          <label htmlFor="meas-date" className="mb-1 block text-xs font-medium text-surface-600">
            Date
          </label>
          <input
            id="meas-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            max={todayISO()}
            required
            className="rounded-lg border border-surface-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="meas-notes" className="mb-1 block text-xs font-medium text-surface-600">
            Notes (optional)
          </label>
          <input
            id="meas-notes"
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={500}
            placeholder="e.g. morning, post-workout…"
            className="w-full rounded-lg border border-surface-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
          />
        </div>
      </div>

      {/* Measurement fields grouped */}
      <div className="space-y-4">
        {MEASUREMENT_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-surface-500">
              {group.label}
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {group.fields.map((field) => (
                <div key={field}>
                  <label
                    htmlFor={`meas-${field}`}
                    className="mb-1 block text-xs font-medium text-surface-600"
                  >
                    {MEASUREMENT_LABELS[field]}
                    <span className="ml-1 text-surface-500">({unit})</span>
                  </label>
                  <input
                    id={`meas-${field}`}
                    type="number"
                    value={values[field] ?? ""}
                    onChange={(e) => updateField(field, e.target.value)}
                    min="0.1"
                    step="0.1"
                    placeholder={placeholder}
                    className="w-full rounded-lg border border-surface-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2 pt-1">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-50 transition-colors"
        >
          {submitting ? "Saving…" : "Save measurements"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-xl px-4 py-2 text-sm text-surface-600 hover:bg-surface-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ onLog }: { onLog: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-surface-300 bg-white px-6 py-12 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-100">
        <RulerIcon />
      </div>
      <h3 className="text-sm font-medium text-surface-700">
        No measurements yet
      </h3>
      <p className="mt-1 text-sm text-surface-500">
        Log your first set to start tracking progress.
      </p>
      <button
        onClick={onLog}
        className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 transition-colors"
      >
        Log measurements
      </button>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function PlusIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
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

function RulerIcon() {
  return (
    <svg className="h-6 w-6 text-surface-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21.3 8.7 8.7 21.3c-1 1-2.5 1-3.4 0l-2.6-2.6c-1-1-1-2.5 0-3.4L15.3 2.7c1-1 2.5-1 3.4 0l2.6 2.6c1 1 1 2.5 0 3.4z" />
      <path d="m7.5 10.5 2 2" />
      <path d="m10.5 7.5 2 2" />
      <path d="m13.5 4.5 2 2" />
      <path d="m4.5 13.5 2 2" />
    </svg>
  );
}
