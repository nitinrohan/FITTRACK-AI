/**
 * Habits API - typed wrappers around the FitTrack /api/v1/habits endpoints.
 *
 * The `today` query param carries the client's *local* calendar date so the
 * backend computes "completed today" and streaks against the user's day, not
 * the server's. All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from '@/lib/api-client'
import type {
  Completion,
  CreateHabitRequest,
  Habit,
  HabitCompletionsResponse,
  HabitListResponse,
  UpdateHabitRequest,
} from '@/types/habits'

/** Local calendar date as YYYY-MM-DD (not UTC - uses the browser's timezone). */
export function localToday(): string {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

export const habitsApi = {
  list(includeArchived = false): Promise<HabitListResponse> {
    const qs = new URLSearchParams({ today: localToday() })
    if (includeArchived) qs.set('include_archived', 'true')
    return apiClient.get<HabitListResponse>(`/api/v1/habits?${qs.toString()}`)
  },

  create(payload: CreateHabitRequest): Promise<Habit> {
    return apiClient.post<Habit>(`/api/v1/habits?today=${localToday()}`, payload)
  },

  update(id: string, payload: UpdateHabitRequest): Promise<Habit> {
    return apiClient.patch<Habit>(`/api/v1/habits/${id}?today=${localToday()}`, payload)
  },

  remove(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/habits/${id}`)
  },

  markComplete(id: string, date?: string): Promise<Completion> {
    return apiClient.post<Completion>(`/api/v1/habits/${id}/completions`, {
      date: date ?? localToday(),
    })
  },

  unmarkComplete(id: string, date: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/habits/${id}/completions/${date}`)
  },

  completions(id: string): Promise<HabitCompletionsResponse> {
    return apiClient.get<HabitCompletionsResponse>(`/api/v1/habits/${id}/completions`)
  },
}
