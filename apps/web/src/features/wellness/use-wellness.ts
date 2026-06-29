'use client'

/**
 * useWellness - data hook for the wellness page.
 *
 * Manages three independent lists (sleep, steps, wellness) plus a
 * combined daily snapshot.  Each sub-domain is loaded independently so
 * one failing request doesn't blank the whole page.
 */

import { useCallback, useEffect, useState } from 'react'
import { sleepApi, stepsApi, wellnessApi } from '@/lib/wellness-api'
import type {
  DailyWellnessSnapshot,
  LogSleepRequest,
  LogStepsRequest,
  LogWellnessRequest,
  SleepLog,
  StepsLog,
  UpdateSleepRequest,
  UpdateStepsRequest,
  UpdateWellnessRequest,
  WellnessLog,
} from '@/types/wellness'

interface WellnessState {
  sleepLogs: SleepLog[]
  stepsLogs: StepsLog[]
  wellnessLogs: WellnessLog[]
  snapshot: DailyWellnessSnapshot | null
  isLoading: boolean
  error: string | null
}

export function useWellness(pageSize = 30) {
  const [state, setState] = useState<WellnessState>({
    sleepLogs: [],
    stepsLogs: [],
    wellnessLogs: [],
    snapshot: null,
    isLoading: true,
    error: null,
  })

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }))
    try {
      const [sleepRes, stepsRes, wellnessRes, snapshot] = await Promise.all([
        sleepApi.list({ page_size: pageSize }),
        stepsApi.list({ page_size: pageSize }),
        wellnessApi.list({ page_size: pageSize }),
        wellnessApi.dailySnapshot(),
      ])
      setState({
        sleepLogs: sleepRes.items,
        stepsLogs: stepsRes.items,
        wellnessLogs: wellnessRes.items,
        snapshot,
        isLoading: false,
        error: null,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load wellness data'
      setState((s) => ({ ...s, isLoading: false, error: msg }))
    }
  }, [pageSize])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // ── Sleep actions ────────────────────────────────────────────────────────────

  const logSleep = useCallback(
    async (payload: LogSleepRequest): Promise<SleepLog> => {
      const entry = await sleepApi.create(payload)
      await refresh()
      return entry
    },
    [refresh],
  )

  const updateSleep = useCallback(
    async (id: string, payload: UpdateSleepRequest): Promise<void> => {
      await sleepApi.update(id, payload)
      await refresh()
    },
    [refresh],
  )

  const deleteSleep = useCallback(
    async (id: string): Promise<void> => {
      await sleepApi.delete(id)
      await refresh()
    },
    [refresh],
  )

  // ── Steps actions ────────────────────────────────────────────────────────────

  const logSteps = useCallback(
    async (payload: LogStepsRequest): Promise<StepsLog> => {
      const entry = await stepsApi.create(payload)
      await refresh()
      return entry
    },
    [refresh],
  )

  const updateSteps = useCallback(
    async (id: string, payload: UpdateStepsRequest): Promise<void> => {
      await stepsApi.update(id, payload)
      await refresh()
    },
    [refresh],
  )

  const deleteSteps = useCallback(
    async (id: string): Promise<void> => {
      await stepsApi.delete(id)
      await refresh()
    },
    [refresh],
  )

  // ── Wellness actions ─────────────────────────────────────────────────────────

  const logWellness = useCallback(
    async (payload: LogWellnessRequest): Promise<WellnessLog> => {
      const entry = await wellnessApi.create(payload)
      await refresh()
      return entry
    },
    [refresh],
  )

  const updateWellness = useCallback(
    async (id: string, payload: UpdateWellnessRequest): Promise<void> => {
      await wellnessApi.update(id, payload)
      await refresh()
    },
    [refresh],
  )

  const deleteWellness = useCallback(
    async (id: string): Promise<void> => {
      await wellnessApi.delete(id)
      await refresh()
    },
    [refresh],
  )

  return {
    sleepLogs: state.sleepLogs,
    stepsLogs: state.stepsLogs,
    wellnessLogs: state.wellnessLogs,
    snapshot: state.snapshot,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    logSleep,
    updateSleep,
    deleteSleep,
    logSteps,
    updateSteps,
    deleteSteps,
    logWellness,
    updateWellness,
    deleteWellness,
  }
}
