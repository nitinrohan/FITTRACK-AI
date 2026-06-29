/**
 * Progress domain types - mirror apps/api/app/schemas/progress.py
 */

export interface ProgressPoint {
  date: string; // YYYY-MM-DD
  value: number;
}

export interface MetricSeries {
  metric: "weight" | "workouts" | "calories";
  label: string;
  unit: string;
  points: ProgressPoint[];
  count: number;
  total: number;
  minimum: number | null;
  maximum: number | null;
  average: number | null;
  first: number | null;
  latest: number | null;
  change: number | null;
}

export interface ProgressResponse {
  range_days: number;
  start_date: string;
  end_date: string;
  weight: MetricSeries | null;
  workouts: MetricSeries | null;
  calories: MetricSeries | null;
}
