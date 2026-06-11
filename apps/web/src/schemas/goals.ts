/**
 * Zod validation schemas for Goal forms.
 *
 * Numeric fields from HTML inputs arrive as strings; z.preprocess handles
 * the empty-string → undefined coercion before number validation runs.
 */

import { z } from "zod";
import { GOAL_TYPES } from "@/types/goals";

function coerceOptionalNumber(val: unknown): number | undefined {
  if (val === "" || val === null || val === undefined) return undefined;
  const n = Number(val);
  return isNaN(n) ? undefined : n;
}

const optionalNumber = z.preprocess(
  coerceOptionalNumber,
  z.number().min(0, "Must be ≥ 0").optional()
);

const numericFields = {
  starting_value: optionalNumber,
  target_value: optionalNumber,
  current_value: optionalNumber,
  target_unit: z
    .string()
    .max(32, "Max 32 characters")
    .optional()
    .or(z.literal("")),
};

export const createGoalSchema = z
  .object({
    goal_type: z.enum(GOAL_TYPES, {
      required_error: "Please select a goal type",
    }),
    title: z
      .string()
      .min(1, "Title is required")
      .max(200, "Max 200 characters"),
    description: z
      .string()
      .max(1000, "Max 1000 characters")
      .optional()
      .or(z.literal("")),
    ...numericFields,
    deadline: z.string().optional().or(z.literal("")),
  })
  .refine(
    (data) => {
      const hasNumeric =
        data.starting_value !== undefined ||
        data.target_value !== undefined ||
        data.current_value !== undefined;
      if (hasNumeric && !data.target_unit) return false;
      return true;
    },
    {
      message: "Unit is required when any value is provided",
      path: ["target_unit"],
    }
  );

export type CreateGoalFormData = z.infer<typeof createGoalSchema>;

/** Update schema: same fields but all optional, plus status. */
export const updateGoalSchema = z.object({
  goal_type: z.enum(GOAL_TYPES).optional(),
  title: z.string().min(1).max(200).optional(),
  description: z.string().max(1000).optional().or(z.literal("")),
  ...numericFields,
  deadline: z.string().optional().or(z.literal("")),
  status: z
    .enum(["active", "paused", "completed", "cancelled"] as const)
    .optional(),
});

export type UpdateGoalFormData = z.infer<typeof updateGoalSchema>;
