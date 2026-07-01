/**
 * Habit domain types - mirror the FastAPI /api/v1/habits schemas.
 *
 * The stat fields (completed_today, current_streak, …) are derived by the
 * backend from completion history; they are read-only on the client.
 */

export interface Habit {
  id: string
  user_id: string
  name: string
  description: string | null
  color: string | null
  target_days_per_week: number
  is_archived: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
  // Derived stats
  completed_today: boolean
  current_streak: number
  longest_streak: number
  completions_this_week: number
  weekly_adherence_pct: number
}

export interface HabitListResponse {
  items: Habit[]
  total: number
  page: number
  page_size: number
}

export interface CreateHabitRequest {
  name: string
  description?: string | null
  color?: string | null
  target_days_per_week?: number
}

export interface UpdateHabitRequest {
  name?: string
  description?: string | null
  color?: string | null
  target_days_per_week?: number
  is_archived?: boolean
}

export interface Completion {
  id: string
  habit_id: string
  date: string
  created_at: string
}

export interface HabitCompletionsResponse {
  habit_id: string
  items: Completion[]
}
