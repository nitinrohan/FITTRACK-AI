/**
 * useGoals - data hook for the goals list page.
 *
 * Fetches goals and exposes CRUD helpers.  Components call these helpers
 * to avoid direct API imports.  Errors are surfaced as strings so the
 * UI can display them without inspecting ApiError internals.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { goalsApi } from "@/lib/goals-api";
import type { Goal, GoalStatus } from "@/types/goals";
import type { CreateGoalPayload, UpdateGoalPayload } from "@/types/goals";

interface UseGoalsState {
  goals: Goal[];
  total: number;
  isLoading: boolean;
  error: string | null;
}

export function useGoals(statusFilter?: GoalStatus | "all") {
  const [state, setState] = useState<UseGoalsState>({
    goals: [],
    total: 0,
    isLoading: true,
    error: null,
  });

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const params =
        statusFilter && statusFilter !== "all"
          ? { status: statusFilter, page_size: 50 }
          : { page_size: 50 };
      const data = await goalsApi.list(params);
      setState({ goals: data.goals, total: data.total, isLoading: false, error: null });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load goals";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, [statusFilter]);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  const createGoal = useCallback(
    async (payload: CreateGoalPayload): Promise<Goal> => {
      const goal = await goalsApi.create(payload);
      await fetch();
      return goal;
    },
    [fetch]
  );

  const updateGoal = useCallback(
    async (id: string, payload: UpdateGoalPayload): Promise<Goal> => {
      const goal = await goalsApi.update(id, payload);
      await fetch();
      return goal;
    },
    [fetch]
  );

  const deleteGoal = useCallback(
    async (id: string): Promise<void> => {
      await goalsApi.delete(id);
      await fetch();
    },
    [fetch]
  );

  return {
    goals: state.goals,
    total: state.total,
    isLoading: state.isLoading,
    error: state.error,
    refresh: fetch,
    createGoal,
    updateGoal,
    deleteGoal,
  };
}
