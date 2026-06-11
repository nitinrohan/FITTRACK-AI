/**
 * TypeScript types for the goals domain.
 * Mirror the GoalResponse and list schema from the FastAPI backend.
 */

export const GOAL_TYPES = [
  "weight_loss",
  "weight_gain",
  "body_fat",
  "strength",
  "endurance",
  "habit",
  "custom",
] as const;

export type GoalType = (typeof GOAL_TYPES)[number];

export const GOAL_TYPE_LABELS: Record<GoalType, string> = {
  weight_loss: "Weight Loss",
  weight_gain: "Weight Gain",
  body_fat: "Body Fat",
  strength: "Strength",
  endurance: "Endurance",
  habit: "Habit",
  custom: "Custom",
};

export const GOAL_STATUSES = [
  "active",
  "paused",
  "completed",
  "cancelled",
] as const;

export type GoalStatus = (typeof GOAL_STATUSES)[number];

/** Allowed transitions from a given status. */
export const ALLOWED_STATUS_TRANSITIONS: Record<GoalStatus, GoalStatus[]> = {
  active: ["paused", "completed", "cancelled"],
  paused: ["active", "cancelled"],
  completed: [],
  cancelled: [],
};

export interface Goal {
  id: string;
  user_id: string;
  goal_type: GoalType;
  title: string;
  description: string | null;
  starting_value: number | null;
  target_value: number | null;
  current_value: number | null;
  target_unit: string | null;
  deadline: string | null; // ISO date string, e.g. "2025-12-31"
  status: GoalStatus;
  completed_at: string | null;
  is_public: boolean;
  progress_pct: number | null; // computed by the backend, 0-100 or null
  created_at: string;
  updated_at: string;
}

export interface GoalListResponse {
  goals: Goal[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface CreateGoalPayload {
  goal_type: GoalType;
  title: string;
  description?: string;
  starting_value?: number;
  target_value?: number;
  current_value?: number;
  target_unit?: string;
  deadline?: string;
}

export interface UpdateGoalPayload {
  title?: string;
  description?: string | null;
  goal_type?: GoalType;
  starting_value?: number | null;
  target_value?: number | null;
  current_value?: number | null;
  target_unit?: string | null;
  deadline?: string | null;
  status?: GoalStatus;
}
