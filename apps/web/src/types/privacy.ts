/**
 * Types for the privacy endpoints (summary, export, account deletion).
 */

export interface PrivacySummary {
  goals: number;
  weight_entries: number;
  body_measurements: number;
  custom_exercises: number;
  workout_templates: number;
  workouts: number;
  custom_foods: number;
  food_logs: number;
  water_logs: number;
  sleep_logs: number;
  daily_steps: number;
  wellness_logs: number;
  habits: number;
}

/** The export is an open, domain-grouped snapshot; we only type its metadata. */
export interface DataExport {
  export_metadata: {
    format_version: string;
    generated_at: string;
    user_id: string;
    email: string;
  };
  [key: string]: unknown;
}

export interface AccountDeletedResponse {
  status: string;
  message: string;
}

/** Human-readable labels for the summary categories, in display order. */
export const SUMMARY_LABELS: { key: keyof PrivacySummary; label: string }[] = [
  { key: "goals", label: "Goals" },
  { key: "workouts", label: "Workouts" },
  { key: "workout_templates", label: "Workout templates" },
  { key: "weight_entries", label: "Weight entries" },
  { key: "body_measurements", label: "Body measurements" },
  { key: "food_logs", label: "Food logs" },
  { key: "custom_foods", label: "Custom foods" },
  { key: "water_logs", label: "Water logs" },
  { key: "sleep_logs", label: "Sleep logs" },
  { key: "daily_steps", label: "Daily steps" },
  { key: "wellness_logs", label: "Wellness check-ins" },
  { key: "habits", label: "Habits" },
  { key: "custom_exercises", label: "Custom exercises" },
];
