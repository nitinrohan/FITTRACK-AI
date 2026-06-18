"use client";

/**
 * useWorkouts — data hook for workout history and in-progress workouts.
 */

import { useCallback, useEffect, useState } from "react";
import { workoutsApi } from "@/lib/workouts-api";
import type { WorkoutSummary } from "@/types/workouts";

interface UseWorkoutsState {
  workouts: WorkoutSummary[];
  total: number;
  isLoading: boolean;
  error: string | null;
}

export type WorkoutFilter = "all" | "in_progress" | "completed";

export function useWorkouts(filter: WorkoutFilter = "all") {
  const [state, setState] = useState<UseWorkoutsState>({
    workouts: [],
    total: 0,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const params =
        filter !== "all"
          ? { status: filter as "in_progress" | "completed", page_size: 50 }
          : { page_size: 50 };
      const data = await workoutsApi.list(params);
      setState({
        workouts: data.workouts,
        total: data.total,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load workouts";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, [filter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const deleteWorkout = useCallback(
    async (id: string): Promise<void> => {
      await workoutsApi.delete(id);
      await refresh();
    },
    [refresh]
  );

  return {
    workouts: state.workouts,
    total: state.total,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    deleteWorkout,
  };
}
