/**
 * TypeScript types for the FitTrack AI nutrition domain.
 *
 * Mirrors the Pydantic schemas in apps/api/app/schemas/nutrition.py
 */

// ── Shared ─────────────────────────────────────────────────────────────────────

export type MealType = "breakfast" | "lunch" | "dinner" | "snack" | "other";

export const MEAL_TYPE_LABELS: Record<MealType, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
  other: "Other",
};

export const MEAL_TYPE_ORDER: MealType[] = [
  "breakfast",
  "lunch",
  "dinner",
  "snack",
  "other",
];

// ── Food ───────────────────────────────────────────────────────────────────────

export interface Food {
  id: string;
  user_id: string | null;
  name: string;
  brand: string | null;
  description: string | null;
  calories_per_100g: number;
  protein_per_100g: number;
  carbs_per_100g: number;
  fat_per_100g: number;
  fiber_per_100g: number | null;
  sugar_per_100g: number | null;
  sodium_per_100g: number | null;
  serving_size_g: number | null;
  serving_unit: string | null;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface FoodListResponse {
  foods: Food[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateFoodPayload {
  name: string;
  brand?: string;
  description?: string;
  calories_per_100g: number;
  protein_per_100g?: number;
  carbs_per_100g?: number;
  fat_per_100g?: number;
  fiber_per_100g?: number;
  serving_size_g?: number;
  serving_unit?: string;
}

export interface MacroPortion {
  grams: number;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
}

/** AI macro estimate - a preview the user edits before saving. */
export interface MacroEstimate {
  ai_available: boolean;
  name: string | null;
  serving_size_g: number | null;
  serving_unit: string | null;
  calories_per_100g: number | null;
  protein_per_100g: number | null;
  carbs_per_100g: number | null;
  fat_per_100g: number | null;
  fiber_per_100g: number | null;
  portion: MacroPortion | null;
  confidence: string | null;
  is_estimate: boolean;
  disclaimer: string;
  message: string | null;
  provider: string | null;
  model_id: string | null;
  prompt_version: string | null;
  log_id: string | null;
}

// ── Multi-item meal estimate (several foods described at once) ─────────────────

export interface MealItemEstimate {
  name: string;
  quantity_g: number;
  serving_unit: string | null;
  calories_per_100g: number;
  protein_per_100g: number;
  carbs_per_100g: number;
  fat_per_100g: number;
  fiber_per_100g: number | null;
  confidence: string;
  portion: MacroPortion;
}

/** AI estimate for a whole meal description - a preview, editable per item. */
export interface MealEstimate {
  ai_available: boolean;
  items: MealItemEstimate[];
  totals: MacroPortion | null;
  is_estimate: boolean;
  disclaimer: string;
  message: string | null;
  provider: string | null;
  model_id: string | null;
  prompt_version: string | null;
  log_id: string | null;
}

export interface LogMealItemPayload {
  name: string;
  quantity_g: number;
  serving_unit?: string;
  calories_per_100g: number;
  protein_per_100g?: number;
  carbs_per_100g?: number;
  fat_per_100g?: number;
  fiber_per_100g?: number;
}

export interface LogMealPayload {
  logged_date: string; // YYYY-MM-DD
  meal_type?: MealType;
  items: LogMealItemPayload[];
  estimate_log_id?: string;
}

export interface LogMealResult {
  entries: FoodLogEntry[];
  totals: MacroTotals;
}

// ── Nutrition targets (user-configured daily goals) ─────────────────────────────

export interface NutritionTarget {
  calorie_target_kcal: number | null;
  protein_target_g: number | null;
  carbs_target_g: number | null;
  fat_target_g: number | null;
  fiber_target_g: number | null;
  is_set: boolean;
  updated_at: string | null;
}

export interface UpdateNutritionTargetPayload {
  calorie_target_kcal?: number | null;
  protein_target_g?: number | null;
  carbs_target_g?: number | null;
  fat_target_g?: number | null;
  fiber_target_g?: number | null;
}

// ── Daily nutrition insight (read-only AI comparison + suggestions) ────────────

export interface MacroComparison {
  metric: "calories" | "protein" | "carbs" | "fat" | "fiber";
  label: string;
  unit: string;
  current: number;
  target: number | null;
  percent_of_target: number | null;
  remaining: number | null;
}

export interface DailyInsight {
  date: string;
  day_totals: MacroTotals;
  targets: NutritionTarget;
  comparisons: MacroComparison[];
  meals_logged: string[];
  meals_remaining: string[];
  ai_available: boolean;
  highlights: string[];
  suggestions: string[];
  encouragement: string;
  disclaimer: string;
  message: string | null;
  provider: string | null;
  model_id: string | null;
  prompt_version: string | null;
  log_id: string | null;
  generated_at: string | null;
}

export interface UpdateFoodPayload {
  name?: string;
  brand?: string;
  description?: string;
  calories_per_100g?: number;
  protein_per_100g?: number;
  carbs_per_100g?: number;
  fat_per_100g?: number;
  fiber_per_100g?: number;
  serving_size_g?: number;
  serving_unit?: string;
}

// ── Food log ──────────────────────────────────────────────────────────────────

export interface FoodLogEntry {
  id: string;
  food_id: string;
  logged_date: string;
  meal_type: string;
  quantity_g: number;
  notes: string | null;
  // computed macros for this entry
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  // denormalised food info
  food_name: string;
  food_brand: string | null;
  created_at: string;
  updated_at: string;
}

export interface LogFoodPayload {
  food_id: string;
  logged_date: string; // YYYY-MM-DD
  meal_type?: MealType;
  quantity_g: number;
  notes?: string;
}

export interface UpdateFoodLogPayload {
  meal_type?: MealType;
  quantity_g?: number;
  notes?: string;
}

// ── Water log ─────────────────────────────────────────────────────────────────

export interface WaterLogEntry {
  id: string;
  logged_date: string;
  amount_ml: number;
  notes: string | null;
  created_at: string;
}

export interface LogWaterPayload {
  logged_date: string; // YYYY-MM-DD
  amount_ml: number;
  notes?: string;
}

export interface UpdateWaterLogPayload {
  amount_ml?: number;
  notes?: string;
}

// ── Daily summary ─────────────────────────────────────────────────────────────

export interface MacroTotals {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

export interface MealSection {
  meal_type: string;
  entries: FoodLogEntry[];
  totals: MacroTotals;
}

export interface DailyNutrition {
  date: string;
  meals: MealSection[];
  day_totals: MacroTotals;
  water_logs: WaterLogEntry[];
  water_total_ml: number;
}
