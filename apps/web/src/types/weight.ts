/**
 * TypeScript types for the weight-tracking domain.
 */

export type WeightDisplayUnit = "kg" | "lbs";

export interface WeightEntry {
  id: string;
  user_id: string;
  weight_kg: number;
  display_unit: WeightDisplayUnit;
  body_fat_pct: number | null;
  muscle_mass_kg: number | null;
  measured_at: string; // ISO date string "YYYY-MM-DD"
  notes: string | null;
  weight_lbs: number | null;  // computed by backend
  bmi: number | null;         // computed by backend (estimate, requires height)
  created_at: string;
  updated_at: string;
}

export interface WeightListStats {
  count: number;
  latest_kg: number | null;
  earliest_kg: number | null;
  change_kg: number | null;
  min_kg: number | null;
  max_kg: number | null;
  moving_avg_7d_kg: number | null;
}

export interface WeightListResponse {
  entries: WeightEntry[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  stats: WeightListStats;
}

export interface LogWeightPayload {
  weight: number;
  display_unit: WeightDisplayUnit;
  body_fat_pct?: number;
  muscle_mass_kg?: number;
  measured_at: string;
  notes?: string;
}

export interface UpdateWeightPayload {
  weight?: number;
  display_unit?: WeightDisplayUnit;
  body_fat_pct?: number | null;
  muscle_mass_kg?: number | null;
  measured_at?: string;
  notes?: string | null;
}
