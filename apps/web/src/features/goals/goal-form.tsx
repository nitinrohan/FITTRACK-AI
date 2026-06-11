/**
 * GoalForm — modal form for creating and editing goals.
 *
 * Supports two modes:
 *   - Create: no `goal` prop, submits CreateGoalPayload.
 *   - Edit:   `goal` prop pre-populates all fields; shows status selector
 *             limited to valid transitions from the current status.
 */

"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createGoalSchema,
  updateGoalSchema,
  type CreateGoalFormData,
  type UpdateGoalFormData,
} from "@/schemas/goals";
import {
  ALLOWED_STATUS_TRANSITIONS,
  GOAL_TYPE_LABELS,
  GOAL_TYPES,
  type Goal,
  type GoalStatus,
} from "@/types/goals";
import type { CreateGoalPayload, UpdateGoalPayload } from "@/types/goals";

interface GoalFormProps {
  open: boolean;
  onClose: () => void;
  goal?: Goal; // edit mode when provided
  onSubmit: (
    payload: CreateGoalPayload | UpdateGoalPayload
  ) => Promise<void>;
}

const STATUS_LABELS: Record<GoalStatus, string> = {
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function GoalForm({ open, onClose, goal, onSubmit }: GoalFormProps) {
  const isEdit = !!goal;

  // Use a union form — edit schema is a superset of create (adds status)
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateGoalFormData | UpdateGoalFormData>({
    resolver: zodResolver(isEdit ? updateGoalSchema : createGoalSchema),
  });

  // Populate form when opening in edit mode or reset when creating
  useEffect(() => {
    if (!open) return;
    if (goal) {
      reset({
        goal_type: goal.goal_type,
        title: goal.title,
        description: goal.description ?? "",
        starting_value:
          goal.starting_value !== null
            ? (goal.starting_value as unknown as undefined)
            : undefined,
        target_value:
          goal.target_value !== null
            ? (goal.target_value as unknown as undefined)
            : undefined,
        current_value:
          goal.current_value !== null
            ? (goal.current_value as unknown as undefined)
            : undefined,
        target_unit: goal.target_unit ?? "",
        deadline: goal.deadline ?? "",
        ...(isEdit ? { status: goal.status } : {}),
      });
    } else {
      reset({
        goal_type: "custom",
        title: "",
        description: "",
        starting_value: undefined,
        target_value: undefined,
        current_value: undefined,
        target_unit: "",
        deadline: "",
      });
    }
  }, [open, goal, isEdit, reset]);

  const selectedType = watch("goal_type");
  const showNumericFields = [
    "weight_loss",
    "weight_gain",
    "body_fat",
    "strength",
    "endurance",
    "custom",
  ].includes(selectedType ?? "");

  // Status options in edit mode: current + allowed transitions
  const statusOptions: GoalStatus[] = goal
    ? [goal.status, ...ALLOWED_STATUS_TRANSITIONS[goal.status]]
    : [];

  async function onValid(data: CreateGoalFormData | UpdateGoalFormData) {
    const d = data as Record<string, unknown>;

    const payload: CreateGoalPayload | UpdateGoalPayload = {
      goal_type: d.goal_type as CreateGoalPayload["goal_type"],
      title: d.title as string,
      ...(d.description ? { description: d.description as string } : {}),
      ...(d.starting_value !== undefined
        ? { starting_value: d.starting_value as number }
        : {}),
      ...(d.target_value !== undefined
        ? { target_value: d.target_value as number }
        : {}),
      ...(d.current_value !== undefined
        ? { current_value: d.current_value as number }
        : {}),
      ...(d.target_unit ? { target_unit: d.target_unit as string } : {}),
      ...(d.deadline ? { deadline: d.deadline as string } : {}),
    };

    if (isEdit && d.status && goal && d.status !== goal.status) {
      (payload as UpdateGoalPayload).status = d.status as GoalStatus;
    }

    await onSubmit(payload);
    onClose();
  }

  const errs = errors as Record<string, { message?: string }>;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit goal" : "New goal"}
      description={
        isEdit
          ? "Update your goal details or change its status."
          : "Define what you want to achieve."
      }
    >
      <form onSubmit={handleSubmit(onValid)} noValidate className="space-y-4">
        {/* Goal type */}
        <div>
          <label
            htmlFor="gf-type"
            className="mb-1 block text-sm font-medium text-surface-700"
          >
            Goal type <span aria-hidden="true">*</span>
          </label>
          <select
            id="gf-type"
            {...register("goal_type")}
            className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2.5 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {GOAL_TYPES.map((t) => (
              <option key={t} value={t}>
                {GOAL_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
          {errs.goal_type && (
            <p role="alert" className="mt-1 text-xs text-red-600">
              {errs.goal_type.message}
            </p>
          )}
        </div>

        {/* Title */}
        <Input
          id="gf-title"
          label="Title"
          type="text"
          required
          placeholder="e.g. Lose 5 kg by summer"
          error={errs.title?.message}
          {...register("title")}
        />

        {/* Description */}
        <div>
          <label
            htmlFor="gf-desc"
            className="mb-1 block text-sm font-medium text-surface-700"
          >
            Description{" "}
            <span className="font-normal text-surface-400">(optional)</span>
          </label>
          <textarea
            id="gf-desc"
            rows={2}
            placeholder="Add some context…"
            {...register("description")}
            className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2 text-sm text-surface-900 placeholder:text-surface-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
          />
          {errs.description && (
            <p role="alert" className="mt-1 text-xs text-red-600">
              {errs.description.message}
            </p>
          )}
        </div>

        {/* Numeric tracking */}
        {showNumericFields && (
          <fieldset className="rounded-lg border border-surface-100 p-4">
            <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-surface-500">
              Progress tracking{" "}
              <span className="normal-case text-surface-400">(optional)</span>
            </legend>

            <div className="mt-3 grid grid-cols-3 gap-3">
              <Input
                id="gf-starting"
                label="Starting"
                type="number"
                step="any"
                min="0"
                placeholder="0"
                error={errs.starting_value?.message}
                {...register("starting_value")}
              />
              <Input
                id="gf-target"
                label="Target"
                type="number"
                step="any"
                min="0"
                placeholder="0"
                error={errs.target_value?.message}
                {...register("target_value")}
              />
              <Input
                id="gf-current"
                label="Current"
                type="number"
                step="any"
                min="0"
                placeholder="0"
                error={errs.current_value?.message}
                {...register("current_value")}
              />
            </div>

            <div className="mt-3">
              <Input
                id="gf-unit"
                label="Unit"
                type="text"
                placeholder="e.g. kg, lbs, %, reps"
                error={errs.target_unit?.message}
                {...register("target_unit")}
              />
            </div>
          </fieldset>
        )}

        {/* Deadline */}
        <Input
          id="gf-deadline"
          label="Deadline (optional)"
          type="date"
          error={errs.deadline?.message}
          {...register("deadline")}
        />

        {/* Status — edit mode only */}
        {isEdit && goal && statusOptions.length > 0 && (
          <div>
            <label
              htmlFor="gf-status"
              className="mb-1 block text-sm font-medium text-surface-700"
            >
              Status
            </label>
            <select
              id="gf-status"
              {...register("status" as keyof (CreateGoalFormData | UpdateGoalFormData))}
              className="w-full rounded-lg border border-surface-200 bg-white px-3 py-2.5 text-sm text-surface-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} type="button">
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {isEdit ? "Save changes" : "Create goal"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
