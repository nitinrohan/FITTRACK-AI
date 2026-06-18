"use client";

/**
 * useNutrition — data hook for the daily nutrition log page.
 *
 * Fetches the DailyNutrition summary for a given date and exposes helpers
 * for logging food, updating/deleting log entries, and logging water.
 */

import { useCallback, useEffect, useState } from "react";
import { foodsApi, nutritionApi } from "@/lib/nutrition-api";
import type {
  DailyNutrition,
  Food,
  FoodListResponse,
  LogFoodPayload,
  LogWaterPayload,
  MealType,
  UpdateFoodLogPayload,
  UpdateWaterLogPayload,
} from "@/types/nutrition";

interface UseNutritionState {
  daily: DailyNutrition | null;
  isLoading: boolean;
  error: string | null;
}

export function useNutrition(date: string) {
  const [state, setState] = useState<UseNutritionState>({
    daily: null,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const data = await nutritionApi.getDaily(date);
      setState({ daily: data, isLoading: false, error: null });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load nutrition data";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, [date]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logFood = useCallback(
    async (payload: LogFoodPayload): Promise<void> => {
      await nutritionApi.logFood(payload);
      await refresh();
    },
    [refresh]
  );

  const updateFoodLog = useCallback(
    async (id: string, payload: UpdateFoodLogPayload): Promise<void> => {
      await nutritionApi.updateFoodLog(id, payload);
      await refresh();
    },
    [refresh]
  );

  const deleteFoodLog = useCallback(
    async (id: string): Promise<void> => {
      await nutritionApi.deleteFoodLog(id);
      await refresh();
    },
    [refresh]
  );

  const logWater = useCallback(
    async (payload: LogWaterPayload): Promise<void> => {
      await nutritionApi.logWater(payload);
      await refresh();
    },
    [refresh]
  );

  const updateWaterLog = useCallback(
    async (id: string, payload: UpdateWaterLogPayload): Promise<void> => {
      await nutritionApi.updateWaterLog(id, payload);
      await refresh();
    },
    [refresh]
  );

  const deleteWaterLog = useCallback(
    async (id: string): Promise<void> => {
      await nutritionApi.deleteWaterLog(id);
      await refresh();
    },
    [refresh]
  );

  return {
    daily: state.daily,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    logFood,
    updateFoodLog,
    deleteFoodLog,
    logWater,
    updateWaterLog,
    deleteWaterLog,
  };
}

// ── Food search hook ──────────────────────────────────────────────────────────

interface UseFoodSearchState {
  results: Food[];
  total: number;
  isSearching: boolean;
  searchError: string | null;
}

export function useFoodSearch() {
  const [state, setState] = useState<UseFoodSearchState>({
    results: [],
    total: 0,
    isSearching: false,
    searchError: null,
  });

  const search = useCallback(async (query: string): Promise<void> => {
    if (!query.trim()) {
      setState({ results: [], total: 0, isSearching: false, searchError: null });
      return;
    }
    setState((s) => ({ ...s, isSearching: true, searchError: null }));
    try {
      const data: FoodListResponse = await foodsApi.search({
        search: query,
        page_size: 20,
      });
      setState({
        results: data.foods,
        total: data.total,
        isSearching: false,
        searchError: null,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setState((s) => ({ ...s, isSearching: false, searchError: msg }));
    }
  }, []);

  const clear = useCallback(() => {
    setState({ results: [], total: 0, isSearching: false, searchError: null });
  }, []);

  return { ...state, search, clear };
}

export type { MealType };
