'use client'

/**
 * useHabits - data hook for the habits page.
 *
 * Loads the habit list (active by default) and exposes actions for creating,
 * editing, archiving, deleting, and toggling today's completion. Each action
 * refreshes the list so derived stats (streaks, adherence) stay current.
 */

import { useCallback, useEffect, useState } from 'react'
import { habitsApi, localToday } from '@/lib/habits-api'
import type { CreateHabitRequest, Habit, UpdateHabitRequest } from '@/types/habits'

interface HabitsState {
  habits: Habit[]
  isLoading: boolean
  error: string | null
}

export function useHabits(includeArchived = false) {
  const [state, setState] = useState<HabitsState>({
    habits: [],
    isLoading: true,
    error: null,
  })

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }))
    try {
      const res = await habitsApi.list(includeArchived)
      setState({ habits: res.items, isLoading: false, error: null })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load habits'
      setState((s) => ({ ...s, isLoading: false, error: msg }))
    }
  }, [includeArchived])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const createHabit = useCallback(
    async (payload: CreateHabitRequest) => {
      await habitsApi.create(payload)
      await refresh()
    },
    [refresh],
  )

  const updateHabit = useCallback(
    async (id: string, payload: UpdateHabitRequest) => {
      await habitsApi.update(id, payload)
      await refresh()
    },
    [refresh],
  )

  const removeHabit = useCallback(
    async (id: string) => {
      await habitsApi.remove(id)
      await refresh()
    },
    [refresh],
  )

  const setArchived = useCallback(
    async (id: string, archived: boolean) => {
      await habitsApi.update(id, { is_archived: archived })
      await refresh()
    },
    [refresh],
  )

  /** Toggle today's completion based on the habit's current state. */
  const toggleToday = useCallback(
    async (habit: Habit) => {
      if (habit.completed_today) {
        await habitsApi.unmarkComplete(habit.id, localToday())
      } else {
        await habitsApi.markComplete(habit.id)
      }
      await refresh()
    },
    [refresh],
  )

  return {
    habits: state.habits,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    createHabit,
    updateHabit,
    removeHabit,
    setArchived,
    toggleToday,
  }
}
