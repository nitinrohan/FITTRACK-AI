"use client";

/**
 * useProgress - loads progress series for a selectable day range.
 */

import { useCallback, useEffect, useState } from "react";
import { progressApi } from "@/lib/progress-api";
import type { ProgressResponse } from "@/types/progress";

export function useProgress(initialDays = 30) {
  const [days, setDays] = useState(initialDays);
  const [data, setData] = useState<ProgressResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (rangeDays: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await progressApi.get(rangeDays);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load progress.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(days);
  }, [load, days]);

  return {
    data,
    isLoading,
    error,
    days,
    setDays,
    reload: () => load(days),
  };
}
