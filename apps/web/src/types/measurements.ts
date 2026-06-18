/**
 * TypeScript types for the FitTrack AI body measurements domain.
 *
 * Mirrors the Pydantic schemas in apps/api/app/schemas/measurement.py
 * All values stored and returned in centimetres; the UI converts to inches.
 */

// ── Shared field names ────────────────────────────────────────────────────────

export type MeasurementFieldKey =
  | "waist_cm"
  | "chest_cm"
  | "hips_cm"
  | "shoulders_cm"
  | "abdomen_cm"
  | "left_arm_cm"
  | "right_arm_cm"
  | "left_forearm_cm"
  | "right_forearm_cm"
  | "left_thigh_cm"
  | "right_thigh_cm"
  | "left_calf_cm"
  | "right_calf_cm"
  | "neck_cm";

export const MEASUREMENT_FIELD_KEYS: MeasurementFieldKey[] = [
  "waist_cm",
  "chest_cm",
  "hips_cm",
  "shoulders_cm",
  "abdomen_cm",
  "left_arm_cm",
  "right_arm_cm",
  "left_forearm_cm",
  "right_forearm_cm",
  "left_thigh_cm",
  "right_thigh_cm",
  "left_calf_cm",
  "right_calf_cm",
  "neck_cm",
];

export const MEASUREMENT_LABELS: Record<MeasurementFieldKey, string> = {
  waist_cm: "Waist",
  chest_cm: "Chest",
  hips_cm: "Hips",
  shoulders_cm: "Shoulders",
  abdomen_cm: "Abdomen",
  left_arm_cm: "Left arm",
  right_arm_cm: "Right arm",
  left_forearm_cm: "Left forearm",
  right_forearm_cm: "Right forearm",
  left_thigh_cm: "Left thigh",
  right_thigh_cm: "Right thigh",
  left_calf_cm: "Left calf",
  right_calf_cm: "Right calf",
  neck_cm: "Neck",
};

/** Fields grouped for display in sections. */
export const MEASUREMENT_GROUPS: { label: string; fields: MeasurementFieldKey[] }[] = [
  { label: "Trunk", fields: ["waist_cm", "abdomen_cm", "chest_cm", "hips_cm", "shoulders_cm"] },
  { label: "Arms", fields: ["left_arm_cm", "right_arm_cm", "left_forearm_cm", "right_forearm_cm"] },
  { label: "Legs", fields: ["left_thigh_cm", "right_thigh_cm", "left_calf_cm", "right_calf_cm"] },
  { label: "Other", fields: ["neck_cm"] },
];

// ── Measurement entry ─────────────────────────────────────────────────────────

export type MeasurementFields = Partial<Record<MeasurementFieldKey, number | null>>;

export interface BodyMeasurement extends MeasurementFields {
  id: string;
  user_id: string;
  measured_at: string; // YYYY-MM-DD
  notes: string | null;
  recorded_count: number;
  created_at: string;
  updated_at: string;
}

// ── API payloads ──────────────────────────────────────────────────────────────

export interface CreateMeasurementPayload extends MeasurementFields {
  measured_at?: string;
  notes?: string;
}

export interface UpdateMeasurementPayload extends MeasurementFields {
  measured_at?: string;
  notes?: string;
}

// ── API responses ─────────────────────────────────────────────────────────────

export interface MeasurementListResponse {
  entries: BodyMeasurement[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  latest: BodyMeasurement | null;
}

// ── Unit helpers ──────────────────────────────────────────────────────────────

export type DisplayUnit = "cm" | "in";

/** Convert centimetres to inches, 1 decimal place. */
export function cmToInches(cm: number): number {
  return Math.round((cm / 2.54) * 10) / 10;
}

/** Format a measurement value for display. */
export function formatMeasurement(cm: number, unit: DisplayUnit): string {
  if (unit === "in") return `${cmToInches(cm)} in`;
  return `${Math.round(cm * 10) / 10} cm`;
}
