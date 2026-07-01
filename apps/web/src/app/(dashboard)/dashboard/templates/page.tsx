"use client";

/**
 * Templates page - /dashboard/templates
 *
 * Lists all workout templates (user-created and system).
 * Features:
 * - Create template button → modal form
 * - Template cards: name, description, exercise count, system badge
 * - Edit and delete actions on user-owned templates
 * - Start workout from template shortcut
 * - Empty state with CTA
 * - Full loading and error states
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { TemplateForm } from "@/features/workouts/template-form";
import { useTemplates } from "@/features/workouts/use-templates";
import { workoutsApi } from "@/lib/workouts-api";
import type {
  CreateTemplatePayload,
  UpdateTemplatePayload,
  WorkoutTemplate,
} from "@/types/workouts";
import { cn } from "@/lib/utils";

// ── Template card ─────────────────────────────────────────────────────────────

interface TemplateCardProps {
  template: WorkoutTemplate;
  onEdit: (t: WorkoutTemplate) => void;
  onDelete: (t: WorkoutTemplate) => void;
  onStart: (t: WorkoutTemplate) => void;
  isStarting: boolean;
}

function TemplateCard({
  template,
  onEdit,
  onDelete,
  onStart,
  isStarting,
}: TemplateCardProps) {
  const exerciseCount = template.exercises.length;

  return (
    <Card>
      <CardBody className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              {template.is_system && (
                <span className="inline-block rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-surface-500">
                  System
                </span>
              )}
              <span className="text-xs text-surface-500">
                {exerciseCount} exercise{exerciseCount !== 1 ? "s" : ""}
              </span>
            </div>
            <h3 className="truncate text-sm font-semibold text-surface-900">
              {template.name}
            </h3>
            {template.description && (
              <p className="mt-0.5 line-clamp-2 text-xs text-surface-500">
                {template.description}
              </p>
            )}
          </div>

          {/* Actions - edit/delete only for user-owned */}
          {!template.is_system && (
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                aria-label={`Edit template: ${template.name}`}
                onClick={() => onEdit(template)}
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
                aria-label={`Delete template: ${template.name}`}
                onClick={() => onDelete(template)}
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
        </div>

        {/* Exercise preview */}
        {template.exercises.length > 0 && (
          <ul className="space-y-0.5" aria-label="Exercises in this template">
            {template.exercises.slice(0, 4).map((ex) => (
              <li key={ex.id} className="truncate text-xs text-surface-500">
                {ex.order_index + 1}. {ex.exercise_name}
                {ex.default_sets != null && ex.default_reps != null && (
                  <span className="ml-1 text-surface-500">
                    {ex.default_sets}×{ex.default_reps}
                    {ex.default_weight_kg != null &&
                      ` @ ${ex.default_weight_kg} kg`}
                  </span>
                )}
              </li>
            ))}
            {template.exercises.length > 4 && (
              <li className="text-xs text-surface-500">
                +{template.exercises.length - 4} more…
              </li>
            )}
          </ul>
        )}

        {/* Start workout CTA */}
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onStart(template)}
          isLoading={isStarting}
          className="w-full"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
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
      </CardBody>
    </Card>
  );
}

// ── Delete confirmation ───────────────────────────────────────────────────────

interface DeleteConfirmProps {
  template: WorkoutTemplate | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirm({
  template,
  isLoading,
  onConfirm,
  onCancel,
}: DeleteConfirmProps) {
  if (!template) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-template-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-black/40"
        aria-hidden="true"
        onClick={onCancel}
      />
      <div className="relative mx-4 w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <h2
          id="delete-template-title"
          className="text-base font-semibold text-surface-900"
        >
          Delete template?
        </h2>
        <p className="mt-2 text-sm text-surface-600">
          <span className="font-medium">&ldquo;{template.name}&rdquo;</span>{" "}
          will be permanently deleted. Workouts you already logged from this
          template are not affected.
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

export default function TemplatesPage() {
  const router = useRouter();

  const [formOpen, setFormOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<WorkoutTemplate | null>(null);
  const [deletingTemplate, setDeletingTemplate] = useState<WorkoutTemplate | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  const {
    templates,
    total,
    isLoading,
    error,
    createTemplate,
    updateTemplate,
    deleteTemplate,
  } = useTemplates();

  // Separate user-created and system templates
  const userTemplates = templates.filter((t) => !t.is_system);
  const systemTemplates = templates.filter((t) => t.is_system);

  function openCreate() {
    setEditingTemplate(null);
    setSubmitError(null);
    setFormOpen(true);
  }

  function openEdit(t: WorkoutTemplate) {
    setEditingTemplate(t);
    setSubmitError(null);
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditingTemplate(null);
  }

  async function handleSubmit(
    payload: CreateTemplatePayload | UpdateTemplatePayload
  ): Promise<void> {
    setSubmitError(null);
    if (editingTemplate) {
      await updateTemplate(editingTemplate.id, payload as UpdateTemplatePayload);
    } else {
      await createTemplate(payload as CreateTemplatePayload);
    }
  }

  async function handleDelete() {
    if (!deletingTemplate) return;
    setIsDeleting(true);
    try {
      await deleteTemplate(deletingTemplate.id);
    } finally {
      setIsDeleting(false);
      setDeletingTemplate(null);
    }
  }

  async function handleStart(t: WorkoutTemplate) {
    setStartError(null);
    setStartingId(t.id);
    try {
      const workout = await workoutsApi.start({
        template_id: t.id,
        name: t.name,
      });
      router.push(`/dashboard/workouts/${workout.id}`);
    } catch (err) {
      setStartError(
        err instanceof Error ? err.message : "Could not start workout."
      );
      setStartingId(null);
    }
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Templates</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Build reusable workout plans to log sessions faster.
          </p>
        </div>
        <Button onClick={openCreate} aria-label="Create new template">
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          New template
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

      {/* Submit error */}
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
          <LoadingSpinner size="lg" label="Loading templates…" />
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
      {!isLoading && !error && total === 0 && (
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
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-surface-700">
            No templates yet
          </h2>
          <p className="mt-1 max-w-xs text-sm text-surface-500">
            Create a template to save your favourite workout structure. You can
            also start an ad-hoc workout without a template.
          </p>
          <Button className="mt-6" onClick={openCreate}>
            Create your first template
          </Button>
        </div>
      )}

      {/* User templates */}
      {!isLoading && !error && userTemplates.length > 0 && (
        <section aria-labelledby="user-templates-heading" className="mb-8">
          <h2
            id="user-templates-heading"
            className="mb-3 text-sm font-medium text-surface-500"
          >
            Your templates
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {userTemplates.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                onEdit={openEdit}
                onDelete={setDeletingTemplate}
                onStart={handleStart}
                isStarting={startingId === t.id}
              />
            ))}
          </div>
        </section>
      )}

      {/* System templates */}
      {!isLoading && !error && systemTemplates.length > 0 && (
        <section aria-labelledby="system-templates-heading">
          <h2
            id="system-templates-heading"
            className={cn(
              "mb-3 text-sm font-medium text-surface-500",
              userTemplates.length > 0 && "mt-2"
            )}
          >
            Starter templates
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {systemTemplates.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                onEdit={openEdit}
                onDelete={setDeletingTemplate}
                onStart={handleStart}
                isStarting={startingId === t.id}
              />
            ))}
          </div>
        </section>
      )}

      {/* Create / Edit form modal */}
      <TemplateForm
        open={formOpen}
        onClose={closeForm}
        template={editingTemplate ?? undefined}
        onSubmit={handleSubmit}
      />

      {/* Delete confirmation */}
      <DeleteConfirm
        template={deletingTemplate}
        isLoading={isDeleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingTemplate(null)}
      />
    </div>
  );
}
