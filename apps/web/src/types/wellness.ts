// Wellness domain types - sleep, steps, and wellness check-in.

// ── Sleep ─────────────────────────────────────────────────────────────────────

export interface SleepLog {
  id: string
  user_id: string
  date: string // YYYY-MM-DD
  bedtime: string | null // ISO datetime
  wake_time: string | null // ISO datetime
  duration_minutes: number | null
  quality: number | null // 1-5
  notes: string | null
  created_at: string
  updated_at: string
}

export interface LogSleepRequest {
  date: string
  bedtime?: string | null
  wake_time?: string | null
  duration_minutes?: number | null
  quality?: number | null
  notes?: string | null
}

export interface UpdateSleepRequest {
  date?: string
  bedtime?: string | null
  wake_time?: string | null
  duration_minutes?: number | null
  quality?: number | null
  notes?: string | null
}

export interface SleepListResponse {
  items: SleepLog[]
  total: number
  page: number
  page_size: number
}

// ── Steps ─────────────────────────────────────────────────────────────────────

export interface StepsLog {
  id: string
  user_id: string
  date: string
  steps: number
  active_minutes: number | null
  distance_m: number | null
  calories_burned: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface LogStepsRequest {
  date: string
  steps: number
  active_minutes?: number | null
  distance_m?: number | null
  calories_burned?: number | null
  notes?: string | null
}

export interface UpdateStepsRequest {
  date?: string
  steps?: number
  active_minutes?: number | null
  distance_m?: number | null
  calories_burned?: number | null
  notes?: string | null
}

export interface StepsListResponse {
  items: StepsLog[]
  total: number
  page: number
  page_size: number
}

// ── Wellness check-in ─────────────────────────────────────────────────────────

export interface WellnessLog {
  id: string
  user_id: string
  date: string
  mood: number | null // 1-5
  energy: number | null // 1-5
  stress: number | null // 1-5
  notes: string | null
  created_at: string
  updated_at: string
}

export interface LogWellnessRequest {
  date: string
  mood?: number | null
  energy?: number | null
  stress?: number | null
  notes?: string | null
}

export interface UpdateWellnessRequest {
  date?: string
  mood?: number | null
  energy?: number | null
  stress?: number | null
  notes?: string | null
}

export interface WellnessListResponse {
  items: WellnessLog[]
  total: number
  page: number
  page_size: number
}

// ── Daily snapshot ────────────────────────────────────────────────────────────

export interface DailyWellnessSnapshot {
  date: string
  sleep: SleepLog | null
  steps: StepsLog | null
  wellness: WellnessLog | null
  water_total_ml: number
}

// ── Display helpers ───────────────────────────────────────────────────────────

/** Convert duration in minutes to "Xh Ym" string. */
export function formatSleepDuration(minutes: number | null): string {
  if (minutes === null) return '-'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}h`
  return `${h}h ${m}m`
}

/** Convert metres to km with 1 decimal place. */
export function formatDistanceKm(metres: number | null): string {
  if (metres === null) return '-'
  return `${(metres / 1000).toFixed(1)} km`
}

/** Label for 1-5 mood/energy rating. */
export const MOOD_LABELS: Record<number, string> = {
  1: 'Very Low',
  2: 'Low',
  3: 'Okay',
  4: 'Good',
  5: 'Great',
}

/** Label for 1-5 stress rating (inverted - 1 = very calm). */
export const STRESS_LABELS: Record<number, string> = {
  1: 'Very Calm',
  2: 'Calm',
  3: 'Moderate',
  4: 'Stressed',
  5: 'Very Stressed',
}

export const ENERGY_LABELS: Record<number, string> = {
  1: 'Exhausted',
  2: 'Tired',
  3: 'Okay',
  4: 'Energised',
  5: 'High Energy',
}
