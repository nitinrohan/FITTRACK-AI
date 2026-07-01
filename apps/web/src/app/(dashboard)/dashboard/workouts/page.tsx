"use client";

/**
 * Workouts page - /dashboard/workouts
 *
 * Shows workout history and in-progress workouts.
 * Features:
 * - Start ad-hoc workout button
 * - Filter tabs: All / In Progress / Completed
 * - Workout summary cards with resume/view links
 * - Delete action with confirmation
 * - Empty state with CTA
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useWorkouts, type WorkoutFilter } from "@/features/workouts/use-workouts";
import { workoutsApi } from "@/lib/workouts-api";
import type { WorkoutSummary } from "@/types/workouts";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "-";
  const m = Math.floor(seconds / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

function formatVolume(kg: number | null): string {
  if (kg === null) return "-";
  return `${kg.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg`;
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

const FILTERS: { label: string; value: WorkoutFilter }[] = [
  { label: "All", value: "all" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
];

// ── Workout card ──────────────────────────────────────────────────────────────

interface WorkoutCardProps {
  workout: WorkoutSummary;
  onDelete: (w: WorkoutSummary) => void;
}

function WorkoutCard({ workout, onDelete }: WorkoutCardProps) {
  const inProgress = workout.completed_at === null;

  return (
    <Card>
      <CardBody className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              {inProgress ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" aria-hidden="true" />
                  In progress
                </span>
              ) : (
                <span className="inline-block rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                  Completed
                </span>
              )}
              {workout.template_name && (
                <span className="inline-block rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                  {workout.template_name}
                </span>
              )}
            </div>
            <h3 className="truncate text-sm font-semibold text-surface-900">
              {workout.name}
            </h3>
            <p className="text-xs text-surface-500">
              {formatDate(workout.started_at)}
            </p>
          </div>

          {/* Delete action */}
          <button
            type="button"
            aria-label={`Delete workout: ${workout.name}`}
            onClick={() => onDelete(workout)}
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
        </div>

        {/* Stats row */}
        <dl className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-surface-50 px-2 py-1.5">
            <dt className="text-xs text-surface-500">Exercises</dt>
            <dd className="text-sm font-semibold text-surface-800">
              {workout.exercise_count}
            </dd>
          </div>
          <div className="rounded-lg bg-surface-50 px-2 py-1.5">
            <dt className="text-xs text-surface-500">Sets</dt>
            <dd className="text-sm font-semibold text-surface-800">
              {workout.set_count}
            </dd>
          </div>
          <div className="rounded-lg bg-surface-50 px-2 py-1.5">
            <dt className="text-xs text-surface-500">Duration</dt>
            <dd className="text-sm font-semibold text-surface-800">
              {formatDuration(workout.duration_seconds)}
            </dd>
          </div>
        </dl>

        {/* Volume */}
        {workout.total_volume_kg !== null && (
          <p className="text-xs text-surface-500">
            Total volume:{" "}
            <span className="font-medium text-surface-700">
              {formatVolume(workout.total_volume_kg)}
            </span>
          </p>
        )}

        {/* CTA */}
        <Link
          href={`/dashboard/workouts/${workout.id}`}
          className={cn(
            "block w-full rounded-lg px-3 py-2 text-center text-sm font-medium transition-colors",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
            inProgress
              ? "bg-brand-500 text-white hover:bg-brand-600"
              : "border border-surface-200 bg-surface-50 text-surface-700 hover:bg-surface-100"
          )}
        >
          {inProgress ? "Resume workout" : "View details"}
        </Link>
      </CardBody>
    </Card>
  );
}

// ── Delete confirmation ───────────────────────────────────────────────────────

interface DeleteConfirmProps {
  workout: WorkoutSummary | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirm({
  workout,
  isLoading,
  onConfirm,
  onCancel,
}: DeleteConfirmProps) {
  if (!workout) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-workout-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-black/40"
        aria-hidden="true"
        onClick={onCancel}
      />
      <div className="relative mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2
          id="delete-workout-title"
          className="text-base font-semibold text-surface-900"
        >
          Delete workout?
        </h2>
        <p className="mt-2 text-sm text-surface-600">
          <span className="font-medium">&ldquo;{workout.name}&rdquo;</span> and
          all its logged sets will be permanently deleted. This cannot be undone.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            isLoading={isLoading}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WorkoutsPage() {
  const router = useRouter();
  const [activeFilter, setActiveFilter] = useState<WorkoutFilter>("all");
  const [deletingWorkout, setDeletingWorkout] = useState<WorkoutSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const { workouts, total, isLoading, error, deleteWorkout } =
    useWorkouts(activeFilter);

  async function handleStartAdHoc() {
    setStartError(null);
    setIsStarting(true);
    try {
      const workout = await workoutsApi.start({ name: "Workout" });
      router.push(`/dashboard/workouts/${workout.id}`);
    } catch (err) {
      setStartError(
        err instanceof Error ? err.message : "Could not start workout."
      );
      setIsStarting(false);
    }
  }

  async function handleDelete() {
    if (!deletingWorkout) return;
    setIsDeleting(true);
    try {
      await deleteWorkout(deletingWorkout.id);
    } finally {
      setIsDeleting(false);
      setDeletingWorkout(null);
    }
  }

  const listSummary =
    !isLoading && !error
      ? `${total} workout${total !== 1 ? "s" : ""}${activeFilter !== "all" ? ` (${activeFilter.replace("_", " ")})` : ""}`
      : "";

  return (
    <div>
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Workouts</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Log sessions and track your training history.
          </p>
        </div>
        <Button
          onClick={() => void handleStartAdHoc()}
          isLoading={isStarting}
          aria-label="Start a new workout"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <polygon
              strokeLinecap="round"
              strokeLinejoin="round"
              points="5 3 19 12 5 21 5 3"
            />
          </svg>
          Start workout
        </Button>
      </div>

      {/* Start error */}
      {startError && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {startError}
        </div>
      )}

      {/* Filter tabs */}
      <div
        role="tablist"
        aria-label="Filter workouts"
        className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-surface-200 bg-surface-50 p-1 dark:border-surface-700 dark:bg-surface-800"
      >
        {FILTERS.map(({ label, value }) => (
          <button
            key={value}
            role="tab"
            aria-selected={activeFilter === value}
            onClick={() => setActiveFilter(value)}
            className={cn(
              "flex-1 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500",
              activeFilter === value
                ? "bg-white text-surface-900 shadow-sm dark:bg-surface-700 dark:text-surface-50"
                : "text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* List summary */}
      {listSummary && (
        <p className="mb-3 text-xs text-surface-500" aria-live="polite">
          {listSummary}
        </p>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading workouts…" />
        </div>
      )}

      {/* Error */}
      {!isLoading && error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && workouts.length === 0 && (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-surface-200 py-16 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-400">
            <svg
              viewBox="0 0 24 24"
              className="h-7 w-7"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-surface-700">
            {activeFilter === "all"
              ? "No workouts logged yet"
              : `No ${activeFilter.replace("_", " ")} workouts`}
          </h2>
          <p className="mt-1 max-w-xs text-sm text-surface-500">
            {activeFilter === "all"
              ? "Start your first workout or pick a template to get going."
              : `You don't have any ${activeFilter.replace("_", " ")} workouts right now.`}
          </p>
          {activeFilter === "all" && (
            <Button
              className="mt-6"
              onClick={() => void handleStartAdHoc()}
              isLoading={isStarting}
            >
              Start your first workout
            </Button>
          )}
        </div>
      )}

      {/* Workout cards */}
      {!isLoading && !error && workouts.length > 0 && (
        <div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="Workouts list"
        >
          {workouts.map((w) => (
            <WorkoutCard
              key={w.id}
              workout={w}
              onDelete={setDeletingWorkout}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      <DeleteConfirm
        workout={deletingWorkout}
        isLoading={isDeleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingWorkout(null)}
      />
    </div>
  );
}
