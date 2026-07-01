"use client";

/**
 * Active workout page - /dashboard/workouts/[id]
 *
 * Serves both in-progress logging and completed workout detail views.
 *
 * In-progress features:
 * - Add exercise by name / exercise ID
 * - Log sets per exercise (reps + weight_kg for strength; duration for timed)
 * - PR badge displayed inline when a set is a personal record
 * - Remove exercise from workout
 * - Complete workout button
 *
 * Completed view:
 * - Read-only summary: exercises, sets, PR flags, volume
 * - Back to history link
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { workoutsApi } from "@/lib/workouts-api";
import type { Workout, WorkoutExercise, WorkoutSet } from "@/types/workouts";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
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

// ── PR badge ──────────────────────────────────────────────────────────────────

function PRBadge() {
  return (
    <span
      aria-label="Personal record"
      title="Personal record"
      className="inline-block rounded-full bg-amber-50 px-1.5 py-0.5 text-xs font-bold text-amber-600"
    >
      PR
    </span>
  );
}

// ── Set row (logged set display) ──────────────────────────────────────────────

interface SetRowProps {
  set: WorkoutSet;
  inProgress: boolean;
  onDelete?: (setId: string) => void;
}

function SetRow({ set, inProgress, onDelete }: SetRowProps) {
  const parts: string[] = [];
  if (set.reps !== null) parts.push(`${set.reps} reps`);
  if (set.weight_kg !== null) parts.push(`${set.weight_kg} kg`);
  if (set.duration_seconds !== null) {
    const m = Math.floor(set.duration_seconds / 60);
    const s = set.duration_seconds % 60;
    parts.push(m > 0 ? `${m}m ${s}s` : `${s}s`);
  }
  if (set.distance_meters !== null) {
    parts.push(
      set.distance_meters >= 1000
        ? `${(set.distance_meters / 1000).toFixed(2)} km`
        : `${set.distance_meters} m`
    );
  }

  return (
    <div className="flex items-center justify-between gap-2 rounded-lg bg-surface-50 px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="w-5 text-right text-xs text-surface-500">
          {set.set_number}
        </span>
        <span className="text-surface-800">{parts.join(" · ")}</span>
        {set.is_pr && <PRBadge />}
        {set.rpe !== null && (
          <span className="text-xs text-surface-500">RPE {set.rpe}</span>
        )}
      </div>
      {inProgress && onDelete && (
        <button
          type="button"
          aria-label={`Delete set ${set.set_number}`}
          onClick={() => onDelete(set.id)}
          className="flex h-6 w-6 items-center justify-center rounded text-surface-300 hover:bg-red-50 hover:text-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-400"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}

// ── Log set form ──────────────────────────────────────────────────────────────

interface LogSetFormProps {
  exerciseId: string;
  nextSetNumber: number;
  onLog: (
    weId: string,
    reps: number | null,
    weightKg: number | null,
    durationSeconds: number | null
  ) => Promise<void>;
  isLogging: boolean;
}

function LogSetForm({
  exerciseId,
  nextSetNumber,
  onLog,
  isLogging,
}: LogSetFormProps) {
  const [reps, setReps] = useState("");
  const [weight, setWeight] = useState("");
  const [duration, setDuration] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsedReps = reps ? parseInt(reps, 10) : null;
    const parsedWeight = weight ? parseFloat(weight) : null;
    const parsedDuration = duration ? parseInt(duration, 10) : null;

    if (parsedReps === null && parsedWeight === null && parsedDuration === null) {
      setError("Enter at least reps, weight, or duration.");
      return;
    }
    setError(null);
    try {
      await onLog(exerciseId, parsedReps, parsedWeight, parsedDuration);
      setReps("");
      // Keep weight pre-filled for the next set (common UX pattern)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log set.");
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      aria-label={`Log set ${nextSetNumber}`}
    >
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label
            htmlFor={`reps-${exerciseId}`}
            className="mb-0.5 block text-xs text-surface-500"
          >
            Reps
          </label>
          <input
            id={`reps-${exerciseId}`}
            type="number"
            min={0}
            max={10000}
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            placeholder="-"
            className="w-20 rounded-lg border border-surface-200 bg-white px-2 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <div>
          <label
            htmlFor={`weight-${exerciseId}`}
            className="mb-0.5 block text-xs text-surface-500"
          >
            kg
          </label>
          <input
            id={`weight-${exerciseId}`}
            type="number"
            min={0}
            step={0.25}
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="-"
            className="w-24 rounded-lg border border-surface-200 bg-white px-2 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <div>
          <label
            htmlFor={`dur-${exerciseId}`}
            className="mb-0.5 block text-xs text-surface-500"
          >
            Sec
          </label>
          <input
            id={`dur-${exerciseId}`}
            type="number"
            min={0}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            placeholder="-"
            className="w-20 rounded-lg border border-surface-200 bg-white px-2 py-2 text-sm text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <Button
          type="submit"
          size="sm"
          isLoading={isLogging}
          className="self-end"
        >
          Log set {nextSetNumber}
        </Button>
      </div>
      {error && (
        <p
          role="alert"
          className="mt-1 text-xs text-red-600"
        >
          {error}
        </p>
      )}
    </form>
  );
}

// ── Exercise block ────────────────────────────────────────────────────────────

interface ExerciseBlockProps {
  ex: WorkoutExercise;
  inProgress: boolean;
  onLogSet: (
    weId: string,
    reps: number | null,
    weightKg: number | null,
    durationSeconds: number | null
  ) => Promise<void>;
  onDeleteSet: (setId: string) => void;
  onRemoveExercise: (weId: string) => void;
  isLogging: boolean;
}

function ExerciseBlock({
  ex,
  inProgress,
  onLogSet,
  onDeleteSet,
  onRemoveExercise,
  isLogging,
}: ExerciseBlockProps) {
  const categoryColour: Record<string, string> = {
    strength: "bg-red-50 text-red-700",
    cardio: "bg-sky-50 text-sky-700",
    flexibility: "bg-teal-50 text-teal-700",
    balance: "bg-violet-50 text-violet-700",
    sport: "bg-orange-50 text-orange-700",
  };

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4">
      {/* Exercise header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            {ex.exercise_category && (
              <span
                className={cn(
                  "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
                  categoryColour[ex.exercise_category] ?? "bg-surface-100 text-surface-600"
                )}
              >
                {ex.exercise_category}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-surface-900">
            {ex.exercise_name}
          </h3>
        </div>
        {inProgress && (
          <button
            type="button"
            aria-label={`Remove ${ex.exercise_name} from workout`}
            onClick={() => onRemoveExercise(ex.id)}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-surface-500 hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-400"
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
        )}
      </div>

      {/* Logged sets */}
      {ex.sets.length > 0 && (
        <div className="mb-3 space-y-1.5">
          {ex.sets.map((s) => (
            <SetRow
              key={s.id}
              set={s}
              inProgress={inProgress}
              onDelete={inProgress ? onDeleteSet : undefined}
            />
          ))}
        </div>
      )}

      {ex.sets.length === 0 && inProgress && (
        <p className="mb-3 text-xs text-surface-500">
          No sets logged yet. Add your first set below.
        </p>
      )}

      {/* Log set form - only for in-progress */}
      {inProgress && (
        <LogSetForm
          exerciseId={ex.id}
          nextSetNumber={ex.sets.length + 1}
          onLog={onLogSet}
          isLogging={isLogging}
        />
      )}
    </div>
  );
}

// ── Add exercise panel ────────────────────────────────────────────────────────

interface AddExercisePanelProps {
  onAdd: (exerciseId: string) => Promise<void>;
  isAdding: boolean;
}

function AddExercisePanel({ onAdd, isAdding }: AddExercisePanelProps) {
  const [exerciseId, setExerciseId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = exerciseId.trim();
    if (!trimmed) {
      setError("Enter an exercise ID.");
      return;
    }
    setError(null);
    try {
      await onAdd(trimmed);
      setExerciseId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add exercise.");
    }
  }

  return (
    <div className="rounded-xl border border-dashed border-surface-200 p-4">
      <h3 className="mb-3 text-sm font-medium text-surface-700">
        Add exercise
      </h3>
      <p className="mb-3 text-xs text-surface-500">
        Enter the exercise ID from the exercise library. A full exercise search
        picker will be available in a future update.
      </p>
      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="flex items-end gap-2"
      >
        <div className="flex-1">
          <label
            htmlFor="add-exercise-id"
            className="mb-0.5 block text-xs text-surface-500"
          >
            Exercise ID (UUID)
          </label>
          <input
            id="add-exercise-id"
            value={exerciseId}
            onChange={(e) => setExerciseId(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 font-mono text-xs text-surface-900 placeholder-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
          />
        </div>
        <Button type="submit" size="sm" isLoading={isAdding} className="self-end">
          Add
        </Button>
      </form>
      {error && (
        <p role="alert" className="mt-1 text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WorkoutDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const workoutId = params.id;

  const [workout, setWorkout] = useState<Workout | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLogging, setIsLogging] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [isCompleting, setIsCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);

  // Elapsed time display for in-progress workouts
  const [elapsed, setElapsed] = useState("0m");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadWorkout = useCallback(async () => {
    try {
      const data = await workoutsApi.get(workoutId);
      setWorkout(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load workout.");
    } finally {
      setIsLoading(false);
    }
  }, [workoutId]);

  useEffect(() => {
    void loadWorkout();
  }, [loadWorkout]);

  // Elapsed time ticker for in-progress workouts
  useEffect(() => {
    if (!workout || workout.completed_at !== null) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    const start = new Date(workout.started_at).getTime();
    function tick() {
      const diff = Math.floor((Date.now() - start) / 1000);
      const m = Math.floor(diff / 60);
      const h = Math.floor(m / 60);
      setElapsed(h > 0 ? `${h}h ${m % 60}m` : `${m}m`);
    }
    tick();
    timerRef.current = setInterval(tick, 30_000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [workout]);

  async function handleLogSet(
    weId: string,
    reps: number | null,
    weightKg: number | null,
    durationSeconds: number | null
  ) {
    const ex = workout?.exercises.find((e) => e.id === weId);
    const nextSet = (ex?.sets.length ?? 0) + 1;
    setIsLogging(true);
    try {
      await workoutsApi.logSet(weId, {
        set_number: nextSet,
        reps,
        weight_kg: weightKg,
        duration_seconds: durationSeconds,
      });
      await loadWorkout();
    } finally {
      setIsLogging(false);
    }
  }

  async function handleDeleteSet(setId: string) {
    await workoutsApi.deleteSet(setId);
    await loadWorkout();
  }

  async function handleAddExercise(exerciseId: string) {
    setIsAdding(true);
    try {
      const nextOrder = workout?.exercises.length ?? 0;
      await workoutsApi.addExercise(workoutId, {
        exercise_id: exerciseId,
        order_index: nextOrder,
      });
      await loadWorkout();
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveExercise(weId: string) {
    await workoutsApi.removeExercise(weId);
    await loadWorkout();
  }

  async function handleComplete() {
    setCompleteError(null);
    setIsCompleting(true);
    try {
      await workoutsApi.complete(workoutId);
      await loadWorkout();
    } catch (err) {
      setCompleteError(
        err instanceof Error ? err.message : "Could not complete workout."
      );
    } finally {
      setIsCompleting(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <LoadingSpinner size="lg" label="Loading workout…" />
      </div>
    );
  }

  if (error || !workout) {
    return (
      <div>
        <Link
          href="/dashboard/workouts"
          className="mb-4 inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to workouts
        </Link>
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error ?? "Workout not found."}
        </div>
      </div>
    );
  }

  const inProgress = workout.completed_at === null;

  return (
    <div className="max-w-2xl">
      {/* Back link */}
      <Link
        href="/dashboard/workouts"
        className="mb-4 inline-flex items-center gap-1 text-sm text-brand-600 hover:underline"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to workouts
      </Link>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            {inProgress ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                <span
                  className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"
                  aria-hidden="true"
                />
                In progress · {elapsed}
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
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">{workout.name}</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            {formatDate(workout.started_at)}
          </p>
        </div>

        {/* Complete button */}
        {inProgress && (
          <Button
            onClick={() => void handleComplete()}
            isLoading={isCompleting}
            className="shrink-0"
          >
            Finish workout
          </Button>
        )}
      </div>

      {/* Complete error */}
      {completeError && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {completeError}
        </div>
      )}

      {/* Summary stats (completed only) */}
      {!inProgress && (
        <dl className="mb-6 grid grid-cols-3 gap-3 rounded-xl border border-surface-200 bg-surface-50 p-4">
          <div className="text-center">
            <dt className="text-xs text-surface-500">Duration</dt>
            <dd className="mt-0.5 text-lg font-bold text-surface-800">
              {formatDuration(workout.duration_seconds)}
            </dd>
          </div>
          <div className="text-center">
            <dt className="text-xs text-surface-500">Exercises</dt>
            <dd className="mt-0.5 text-lg font-bold text-surface-800">
              {workout.exercises.length}
            </dd>
          </div>
          <div className="text-center">
            <dt className="text-xs text-surface-500">Volume</dt>
            <dd className="mt-0.5 text-lg font-bold text-surface-800">
              {formatVolume(workout.total_volume_kg)}
            </dd>
          </div>
        </dl>
      )}

      {/* Exercises */}
      {workout.exercises.length === 0 && inProgress && (
        <p className="mb-4 text-sm text-surface-500">
          No exercises added yet. Use the form below to add your first exercise.
        </p>
      )}

      <div className="space-y-4">
        {workout.exercises.map((ex) => (
          <ExerciseBlock
            key={ex.id}
            ex={ex}
            inProgress={inProgress}
            onLogSet={handleLogSet}
            onDeleteSet={(setId) => void handleDeleteSet(setId)}
            onRemoveExercise={(weId) => void handleRemoveExercise(weId)}
            isLogging={isLogging}
          />
        ))}
      </div>

      {/* Add exercise - in-progress only */}
      {inProgress && (
        <div className="mt-4">
          <AddExercisePanel onAdd={handleAddExercise} isAdding={isAdding} />
        </div>
      )}

      {/* Done CTA for completed workouts */}
      {!inProgress && (
        <div className="mt-8 text-center">
          <Button
            variant="secondary"
            onClick={() => router.push("/dashboard/workouts")}
          >
            Back to workout history
          </Button>
        </div>
      )}
    </div>
  );
}
