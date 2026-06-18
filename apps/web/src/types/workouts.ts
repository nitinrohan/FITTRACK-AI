/**
 * TypeScript types for the workouts domain.
 * Mirror the Pydantic schemas from the FastAPI backend.
 */

// ── Template types ─────────────────────────────────────────────────────────────

export interface TemplateExercise {
  id: string;
  exercise_id: string;
  order_index: number;
  default_sets: number | null;
  default_reps: number | null;
  default_weight_kg: number | null;
  default_duration_seconds: number | null;
  default_distance_meters: number | null;
  notes: string | null;
  exercise_name: string;
  exercise_category: string | null;
}

export interface WorkoutTemplate {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  exercises: TemplateExercise[];
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  templates: WorkoutTemplate[];
  total: number;
}

export interface TemplateExerciseIn {
  exercise_id: string;
  order_index?: number;
  default_sets?: number | null;
  default_reps?: number | null;
  default_weight_kg?: number | null;
  default_duration_seconds?: number | null;
  default_distance_meters?: number | null;
  notes?: string | null;
}

export interface CreateTemplatePayload {
  name: string;
  description?: string | null;
  exercises?: TemplateExerciseIn[];
}

export interface UpdateTemplatePayload {
  name?: string;
  description?: string | null;
  exercises?: TemplateExerciseIn[] | null;
}

// ── Set types ─────────────────────────────────────────────────────────────────

export interface WorkoutSet {
  id: string;
  set_number: number;
  reps: number | null;
  weight_kg: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  rpe: number | null;
  is_pr: boolean;
  completed_at: string | null;
}

export interface LogSetPayload {
  set_number: number;
  reps?: number | null;
  weight_kg?: number | null;
  duration_seconds?: number | null;
  distance_meters?: number | null;
  rpe?: number | null;
}

// ── WorkoutExercise types ──────────────────────────────────────────────────────

export interface WorkoutExercise {
  id: string;
  exercise_id: string;
  order_index: number;
  notes: string | null;
  exercise_name: string;
  exercise_category: string | null;
  sets: WorkoutSet[];
}

export interface AddExercisePayload {
  exercise_id: string;
  order_index?: number;
  notes?: string | null;
}

// ── Workout types ─────────────────────────────────────────────────────────────

export interface Workout {
  id: string;
  name: string;
  notes: string | null;
  template_id: string | null;
  template_name: string | null;
  started_at: string;
  completed_at: string | null;
  total_volume_kg: number | null;
  duration_seconds: number | null;
  exercises: WorkoutExercise[];
  created_at: string;
}

export interface WorkoutSummary {
  id: string;
  name: string;
  template_id: string | null;
  template_name: string | null;
  started_at: string;
  completed_at: string | null;
  total_volume_kg: number | null;
  duration_seconds: number | null;
  exercise_count: number;
  set_count: number;
}

export interface WorkoutListResponse {
  workouts: WorkoutSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface StartWorkoutPayload {
  template_id?: string | null;
  name?: string | null;
  notes?: string | null;
}

export interface CompleteWorkoutPayload {
  notes?: string | null;
}
