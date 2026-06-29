/**
 * Wellness API - typed wrappers around the FitTrack FastAPI
 * /api/v1/sleep, /api/v1/steps, and /api/v1/wellness endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from '@/lib/api-client'
import type {
  DailyWellnessSnapshot,
  LogSleepRequest,
  LogStepsRequest,
  LogWellnessRequest,
  SleepListResponse,
  SleepLog,
  StepsListResponse,
  StepsLog,
  UpdateSleepRequest,
  UpdateStepsRequest,
  UpdateWellnessRequest,
  WellnessListResponse,
  WellnessLog,
} from '@/types/wellness'

type DateRangeParams = {
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

function buildDateRangeQs(params: DateRangeParams): string {
  const qs = new URLSearchParams()
  if (params.date_from) qs.set('date_from', params.date_from)
  if (params.date_to) qs.set('date_to', params.date_to)
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  const s = qs.toString()
  return s ? `?${s}` : ''
}

// ── Sleep ──────────────────────────────────────────────────────────────────────

export const sleepApi = {
  list(params: DateRangeParams = {}): Promise<SleepListResponse> {
    return apiClient.get<SleepListResponse>(`/api/v1/sleep${buildDateRangeQs(params)}`)
  },

  get(id: string): Promise<SleepLog> {
    return apiClient.get<SleepLog>(`/api/v1/sleep/${id}`)
  },

  create(payload: LogSleepRequest): Promise<SleepLog> {
    return apiClient.post<SleepLog>('/api/v1/sleep', payload)
  },

  update(id: string, payload: UpdateSleepRequest): Promise<SleepLog> {
    return apiClient.patch<SleepLog>(`/api/v1/sleep/${id}`, payload)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/sleep/${id}`)
  },
}

// ── Steps ──────────────────────────────────────────────────────────────────────

export const stepsApi = {
  list(params: DateRangeParams = {}): Promise<StepsListResponse> {
    return apiClient.get<StepsListResponse>(`/api/v1/steps${buildDateRangeQs(params)}`)
  },

  get(id: string): Promise<StepsLog> {
    return apiClient.get<StepsLog>(`/api/v1/steps/${id}`)
  },

  create(payload: LogStepsRequest): Promise<StepsLog> {
    return apiClient.post<StepsLog>('/api/v1/steps', payload)
  },

  update(id: string, payload: UpdateStepsRequest): Promise<StepsLog> {
    return apiClient.patch<StepsLog>(`/api/v1/steps/${id}`, payload)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/steps/${id}`)
  },
}

// ── Wellness ───────────────────────────────────────────────────────────────────

export const wellnessApi = {
  list(params: DateRangeParams = {}): Promise<WellnessListResponse> {
    return apiClient.get<WellnessListResponse>(`/api/v1/wellness${buildDateRangeQs(params)}`)
  },

  get(id: string): Promise<WellnessLog> {
    return apiClient.get<WellnessLog>(`/api/v1/wellness/${id}`)
  },

  create(payload: LogWellnessRequest): Promise<WellnessLog> {
    return apiClient.post<WellnessLog>('/api/v1/wellness', payload)
  },

  update(id: string, payload: UpdateWellnessRequest): Promise<WellnessLog> {
    return apiClient.patch<WellnessLog>(`/api/v1/wellness/${id}`, payload)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/wellness/${id}`)
  },

  /** Fetch the combined daily snapshot (sleep + steps + wellness + water). */
  dailySnapshot(date?: string): Promise<DailyWellnessSnapshot> {
    const qs = date ? `?date=${date}` : ''
    return apiClient.get<DailyWellnessSnapshot>(`/api/v1/wellness/daily${qs}`)
  },
}
