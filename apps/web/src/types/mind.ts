/**
 * Types for the Stress and Mindfulness domains (the "Mind" page).
 */

export type StressBand = "low" | "moderate" | "high";

export interface StressLog {
  id: string;
  user_id: string;
  level: number;
  band: StressBand;
  recorded_at: string;
  source: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface StressListResponse {
  items: StressLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface StressDailySummary {
  date: string;
  count: number;
  highest: number | null;
  lowest: number | null;
  average: number | null;
  band: StressBand | null;
}

export type MindfulnessCategory = "breathing" | "meditation" | "sleep" | "focus";

export interface MindfulnessSession {
  id: string;
  user_id: string | null;
  title: string;
  category: string;
  duration_minutes: number;
  description: string | null;
  external_url: string | null;
  is_system: boolean;
}

export interface MindfulnessSessionListResponse {
  items: MindfulnessSession[];
  total: number;
}

export interface MindfulnessLog {
  id: string;
  user_id: string;
  session_id: string | null;
  session_title: string | null;
  duration_minutes: number;
  recorded_at: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface MindfulnessLogListResponse {
  items: MindfulnessLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface MindfulnessDailySummary {
  date: string;
  total_minutes: number;
  sessions_count: number;
  current_streak: number;
}

/** Display metadata for a stress band (label + Tailwind text colour). */
export const STRESS_BAND_META: Record<StressBand, { label: string; color: string }> = {
  low: { label: "Low", color: "text-brand-600" },
  moderate: { label: "Moderate", color: "text-amber-600" },
  high: { label: "High", color: "text-red-600" },
};
