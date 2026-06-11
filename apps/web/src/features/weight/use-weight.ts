"use client";

import { useCallback, useEffect, useState } from "react";
import { weightApi } from "@/lib/weight-api";
import type {
  LogWeightPayload,
  UpdateWeightPayload,
  WeightEntry,
  WeightListResponse,
  WeightListStats,
} from "@/types/weight";

const EMPTY_STATS: WeightListStats = {
  count: 0,
  latest_kg: null,
  earliest_kg: null,
  change_kg: null,
  min_kg: null,
  max_kg: null,
  moving_avg_7d_kg: null,
};

interface UseWeightState {
  entries: WeightEntry[];
  total: number;
  stats: WeightListStats;
  isLoading: boolean;
  error: string | null;
}

export function useWeight(pageSize = 30) {
  const [state, setState] = useState<UseWeightState>({
    entries: [],
    total: 0,
    stats: EMPTY_STATS,
    isLoading: true,
    error: null,
  });

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const data: WeightListResponse = await weightApi.list({ page_size: pageSize });
      setState({
        entries: data.entries,
        total: data.total,
        stats: data.stats,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load weight history",
      }));
    }
  }, [pageSize]);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  const logWeight = useCallback(
    async (payload: LogWeightPayload): Promise<WeightEntry> => {
      const entry = await weightApi.log(payload);
      await fetch();
      return entry;
    },
    [fetch]
  );

  const updateEntry = useCallback(
    async (id: string, payload: UpdateWeightPayload): Promise<WeightEntry> => {
      const entry = await weightApi.update(id, payload);
      await fetch();
      return entry;
    },
    [fetch]
  );

  const deleteEntry = useCallback(
    async (id: string): Promise<void> => {
      await weightApi.delete(id);
      await fetch();
    },
    [fetch]
  );

  return {
    entries: state.entries,
    total: state.total,
    stats: state.stats,
    isLoading: state.isLoading,
    error: state.error,
    refresh: fetch,
    logWeight,
    updateEntry,
    deleteEntry,
  };
}
