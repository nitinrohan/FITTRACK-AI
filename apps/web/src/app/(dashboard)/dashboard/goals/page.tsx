"use client";

/**
 * Goals page — /dashboard/goals
 *
 * Lists all goals for the current user.  Features:
 * - Filter tabs: All / Active / Paused / Completed / Cancelled
 * - Create goal button → modal form
 * - Each goal card: type badge, title, progress bar, deadline, status
 * - Edit and delete actions per card
 * - Empty state when no goals exist in a filter
 * - Full loading and error states
 */

import { useState } from "react";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { GoalForm } from "@/features/goals/goal-form";
import { useGoals } from "@/features/goals/use-goals";
import {
  ALLOWED_STATUS_TRANSITIONS,
  GOAL_TYPE_LABELS,
  type Goal,
  type GoalStatus,
} from "@/types/goals";
import type { CreateGoalPayload, UpdateGoalPayload } from "@/types/goals";
import { cn } from "@/lib/utils";

// ── Filter tabs ──────────────────────────────────────────────────────────────

const FILTERS: { label: string; value: GoalStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Paused", value: "paused" },
  { label: "Completed", value: "completed" },
  { label: "Cancelled", value: "cancelled" },
];

// ── Status styling ────────────────────────────────────────────────────────────

const STATUS_PILL: Record<GoalStatus, string> = {
  active:
    "bg-emerald-50 text-emerald-700 border border-emerald-200",
  paused:
    "bg-amber-50 text-amber-700 border border-amber-200",
  completed:
    "bg-brand-50 text-brand-700 border border-brand-200",
  cancelled:
    "bg-surface-100 text-surface-500 border border-surface-200",
};

const STATUS_LABELS: Record<GoalStatus, string> = {
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
};

// ── Type badge colours ────────────────────────────────────────────────────────

const TYPE_COLOURS: Record<string, string> = {
  weight_loss: "bg-violet-50 text-violet-700",
  weight_gain: "bg-sky-50 text-sky-700",
  body_fat: "bg-orange-50 text-orange-700",
  strength: "bg-red-50 text-red-700",
  endurance: "bg-cyan-50 text-cyan-700",
  habit: "bg-teal-50 text-teal-700",
  custom: "bg-surface-100 text-surface-600",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDeadline(deadline: string | null): string | null {
  if (!deadline) return null;
  const d = new Date(`${deadline}T00:00:00`);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isDeadlinePast(deadline: string | null): boolean {
  if (!deadline) return false;
  return new Date(`${deadline}T23:59:59`) < new Date();
}

// ── Goal card ─────────────────────────────────────────────────────────────────

interface GoalCardProps {
  goal: Goal;
  onEdit: (goal: Goal) => void;
  onDelete: (goal: Goal) => void;
}

function GoalCard({ goal, onEdit, onDelete }: GoalCardProps) {
  const deadline = formatDeadline(goal.deadline);
  const deadlinePast =
    goal.status === "active" && isDeadlinePast(goal.deadline);
  const isTerminal =
    ALLOWED_STATUS_TRANSITIONS[goal.status].length === 0;

  return (
    <Card>
      <CardBody className="space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              <span
                className={cn(
                  "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
                  TYPE_COLOURS[goal.goal_type] ?? TYPE_COLOURS.custom
                )}
              >
                {GOAL_TYPE_LABELS[goal.goal_type]}
              </span>
              <span
                className={cn(
                  "inline-block rounded-full px-2 py-0.5 text-xs font-medium",
                  STATUS_PILL[goal.status]
                )}
              >
                {STATUS_LABELS[goal.status]}
              </span>
            </div>
            <h3 className="truncate text-sm font-semibold text-surface-900">
              {goal.title}
            </h3>
            {goal.description && (
              <p className="mt-0.5 line-clamp-2 text-xs text-surface-500">
                {goal.description}
              </p>
            )}
          </div>

          {/* Actions */}
          {!isTerminal && (
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                aria-label={`Edit goal: ${goal.title}`}
                onClick={() => onEdit(goal)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-surface-500 hover:bg-surface-100 hover:text-surface-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
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
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                  />
                </svg>
              </button>
              <button
                type="button"
                aria-label={`Delete goal: ${goal.title}`}
                onClick={() => onDelete(goal)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-surface-500 hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500"
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
          )}
          {/* Edit only for terminal goals (no delete for completed) */}
          {isTerminal && goal.status !== "cancelled" && (
            <button
              type="button"
              aria-label={`View goal: ${goal.title}`}
              onClick={() => onEdit(goal)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-surface-500 hover:bg-surface-100 hover:text-surface-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
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
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
            </button>
          )}
        </div>

        {/* Progress bar — only when numeric tracking is set up */}
        {goal.progress_pct !== null && (
          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-surface-500">
              <span>
                {goal.current_value !== null && goal.target_unit
                  ? `${goal.current_value} ${goal.target_unit}`
                  : "Progress"}
              </span>
              <span className="font-medium text-surface-700">
                {goal.progress_pct}%
              </span>
              {goal.target_value !== null && goal.target_unit && (
                <span>
                  {goal.target_value} {goal.target_unit}
                </span>
              )}
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-surface-100"
              role="progressbar"
              aria-valuenow={goal.progress_pct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${goal.title}: ${goal.progress_pct}% complete`}
            >
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  goal.status === "completed"
                    ? "bg-emerald-500"
                    : "bg-brand-500"
                )}
                style={{ width: `${goal.progress_pct}%` }}
              />
            </div>
          </div>
        )}

        {/* Deadline */}
        {deadline && (
          <p
            className={cn(
              "text-xs",
              deadlinePast ? "font-medium text-red-600" : "text-surface-500"
            )}
          >
            {deadlinePast ? "⚠ Deadline passed: " : "Due: "}
            {deadline}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

// ── Delete confirmation dialog ────────────────────────────────────────────────

interface DeleteConfirmProps {
  goal: Goal | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirm({
  goal,
  isLoading,
  onConfirm,
  onCancel,
}: DeleteConfirmProps) {
  if (!goal) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-black/40"
        aria-hidden="true"
        onClick={onCancel}
      />
      <div className="relative mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2 id="delete-dialog-title" className="text-base font-semibold text-surface-900">
          Delete goal?
        </h2>
        <p className="mt-2 text-sm text-surface-600">
          <span className="font-medium">&ldquo;{goal.title}&rdquo;</span> will
          be permanently deleted. This cannot be undone.
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

export default function GoalsPage() {
  const [activeFilter, setActiveFilter] = useState<GoalStatus | "all">("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<Goal | null>(null);
  const [deletingGoal, setDeletingGoal] = useState<Goal | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { goals, total, isLoading, error, createGoal, updateGoal, deleteGoal } =
    useGoals(activeFilter);

  function openCreate() {
    setEditingGoal(null);
    setSubmitError(null);
    setFormOpen(true);
  }

  function openEdit(goal: Goal) {
    setEditingGoal(goal);
    setSubmitError(null);
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditingGoal(null);
  }

  async function handleSubmit(
    payload: CreateGoalPayload | UpdateGoalPayload
  ): Promise<void> {
    setSubmitError(null);
    try {
      if (editingGoal) {
        await updateGoal(editingGoal.id, payload as UpdateGoalPayload);
      } else {
        await createGoal(payload as CreateGoalPayload);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setSubmitError(msg);
      throw err; // re-throw so GoalForm keeps form open
    }
  }

  async function handleDelete() {
    if (!deletingGoal) return;
    setIsDeleting(true);
    try {
      await deleteGoal(deletingGoal.id);
    } catch {
      // silently ignore for now — could surface as a toast in Phase 5
    } finally {
      setIsDeleting(false);
      setDeletingGoal(null);
    }
  }

  // Accessible summary of current results
  const listSummary =
    !isLoading && !error
      ? `${total} goal${total !== 1 ? "s" : ""}${activeFilter !== "all" ? ` (${activeFilter})` : ""}`
      : "";

  return (
    <div>
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Goals</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Set and track your fitness targets.
          </p>
        </div>
        <Button onClick={openCreate} aria-label="Create new goal">
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New goal
        </Button>
      </div>

      {/* Filter tabs */}
      <div
        role="tablist"
        aria-label="Filter goals by status"
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

      {/* Accessible list summary */}
      {listSummary && (
        <p className="mb-3 text-xs text-surface-500" aria-live="polite">
          {listSummary}
        </p>
      )}

      {/* Form submission error (banner above the list) */}
      {submitError && (
        <div
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {submitError}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" label="Loading goals…" />
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
      {!isLoading && !error && goals.length === 0 && (
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
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-surface-700">
            {activeFilter === "all"
              ? "No goals yet"
              : `No ${activeFilter} goals`}
          </h2>
          <p className="mt-1 max-w-xs text-sm text-surface-500">
            {activeFilter === "all"
              ? "Create your first goal to start tracking progress toward your fitness targets."
              : `You don't have any ${activeFilter} goals right now.`}
          </p>
          {activeFilter === "all" && (
            <Button className="mt-6" onClick={openCreate}>
              Create your first goal
            </Button>
          )}
        </div>
      )}

      {/* Goal cards */}
      {!isLoading && !error && goals.length > 0 && (
        <div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="Goals list"
        >
          {goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onEdit={openEdit}
              onDelete={setDeletingGoal}
            />
          ))}
        </div>
      )}

      {/* Create / Edit form modal */}
      <GoalForm
        open={formOpen}
        onClose={closeForm}
        goal={editingGoal ?? undefined}
        onSubmit={handleSubmit}
      />

      {/* Delete confirmation */}
      <DeleteConfirm
        goal={deletingGoal}
        isLoading={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => setDeletingGoal(null)}
      />
    </div>
  );
}
