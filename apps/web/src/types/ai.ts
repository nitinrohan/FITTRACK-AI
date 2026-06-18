/**
 * TypeScript types for the FitTrack AI feature domain.
 * Mirrors apps/api/app/schemas/ai.py
 */

export interface WeeklyDataSnapshot {
  week_start: string;       // YYYY-MM-DD
  week_end: string;         // YYYY-MM-DD
  weight_entries: number;
  workouts_completed: number;
  food_log_days: number;
  water_log_days: number;
  active_goals: number;
}

export interface WeeklySummaryResponse {
  highlights: string[];
  suggestions: string[];
  encouragement: string;
  data_snapshot: WeeklyDataSnapshot;
  ai_available: boolean;
  provider: string | null;
  model_id: string | null;
  prompt_version: string | null;
  log_id: string | null;
}

export interface AcceptSummaryPayload {
  log_id: string;
  accepted: boolean;
}
