"use client";

/**
 * TemplateForm - modal dialog for creating or editing a workout template.
 *
 * For the MVP the exercise list is managed by the user entering exercise IDs
 * or names. In a future phase an exercise picker with search will replace this.
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type {
  CreateTemplatePayload,
  UpdateTemplatePayload,
  WorkoutTemplate,
} from "@/types/workouts";

interface TemplateFormProps {
  open: boolean;
  onClose: () => void;
  /** Present when editing; absent when creating */
  template?: WorkoutTemplate;
  onSubmit: (payload: CreateTemplatePayload | UpdateTemplatePayload) => Promise<void>;
}

export function TemplateForm({
  open,
  onClose,
  template,
  onSubmit,
}: TemplateFormProps) {
  const isEditing = Boolean(template);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate fields when opening in edit mode
  useEffect(() => {
    if (open) {
      setName(template?.name ?? "");
      setDescription(template?.description ?? "");
      setError(null);
    }
  }, [open, template]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name is required.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const payload: CreateTemplatePayload | UpdateTemplatePayload = {
        name: trimmed,
        description: description.trim() || null,
      };
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="template-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        aria-hidden="true"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative mx-4 w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2
          id="template-dialog-title"
          className="mb-5 text-lg font-semibold text-surface-900"
        >
          {isEditing ? "Edit template" : "New template"}
        </h2>

        <form onSubmit={(e) => void handleSubmit(e)} noValidate>
          <div className="space-y-4">
            {/* Name */}
            <div>
              <Input
                id="template-name"
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Upper Body Push"
                maxLength={120}
                required
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="template-desc"
                className="mb-1 block text-sm font-medium text-surface-700"
              >
                Description
                <span className="ml-1 text-xs font-normal text-surface-400">
                  (optional)
                </span>
              </label>
              <textarea
                id="template-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What's this template for?"
                maxLength={1000}
                rows={3}
                className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
              />
            </div>

            {/* Exercise list note */}
            <p className="rounded-lg bg-surface-50 px-3 py-2 text-xs text-surface-500">
              Exercises can be added after creating the template, or when you
              start a workout. You can start an ad-hoc workout from the Workouts
              page and add exercises as you go.
            </p>
          </div>

          {error && (
            <p
              role="alert"
              className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {error}
            </p>
          )}

          <div className="mt-6 flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              {isEditing ? "Save changes" : "Create template"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
