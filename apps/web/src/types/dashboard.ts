/**
 * TypeScript types for the FitTrack AI dashboard summary domain.
 * Mirrors apps/api/app/schemas/dashboard.py
 */

export interface WeightTrendPoint {
  date: string; // YYYY-MM-DD
  weight_kg: number;
}

export interface WeightTrendSection {
  points: WeightTrendPoint[];
  latest_kg: number | null;
  moving_avg_7d_kg: number | null;
  change_kg: number | null;
}

export interface WorkoutFrequencyPoint {
  date: string; // YYYY-MM-DD
  count: number;
}

export interface WorkoutFrequencySection {
  points: WorkoutFrequencyPoint[];
  total_28d: number;
  last_workout_date: string | null;
}

export interface TodayNutritionSection {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  water_ml: number;
}

export interface GoalSummaryItem {
  id: string;
  title: string;
  goal_type: string;
  progress_pct: number | null;
}

export interface GoalsSummarySection {
  goals: GoalSummaryItem[];
  count: number;
  avg_progress_pct: number | null;
}

export interface LatestMeasurementSection {
  date: string;
  recorded_count: number;
  waist_cm: number | null;
  chest_cm: number | null;
  hips_cm: number | null;
  neck_cm: number | null;
  left_arm_cm: number | null;
  right_arm_cm: number | null;
  left_thigh_cm: number | null;
  right_thigh_cm: number | null;
}

export interface DashboardSummary {
  weight_trend: WeightTrendSection | null;
  workout_frequency: WorkoutFrequencySection | null;
  today_nutrition: TodayNutritionSection | null;
  goals: GoalsSummarySection | null;
  latest_measurement: LatestMeasurementSection | null;
}
