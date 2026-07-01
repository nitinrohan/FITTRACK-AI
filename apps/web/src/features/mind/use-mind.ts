"use client";

/**
 * useMind - loads stress and mindfulness data for the Mind page.
 *
 * Groups the several read endpoints behind one loader so the page has a single
 * loading / error surface and one reload() after any mutation.
 */

import { useCallback, useEffect, useState } from "react";
import { mindfulnessApi, stressApi } from "@/lib/mind-api";
import type {
  MindfulnessDailySummary,
  MindfulnessLog,
  MindfulnessSession,
  StressDailySummary,
  StressLog,
} from "@/types/mind";

function todayISO(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

function browserTimezone(fallback: string): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || fallback;
  } catch {
    return fallback;
  }
}

export interface MindData {
  stressSummary: StressDailySummary | null;
  stressLogs: StressLog[];
  mindSummary: MindfulnessDailySummary | null;
  sessions: MindfulnessSession[];
  mindLogs: MindfulnessLog[];
}

export function useMind(preferredTz?: string | null) {
  const tz = browserTimezone(preferredTz ?? "UTC");
  const [data, setData] = useState<MindData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const date = todayISO();
      const [stressSummary, stressList, mindSummary, sessions, mindLogs] =
        await Promise.all([
          stressApi.summary(date, tz),
          stressApi.list(),
          mindfulnessApi.summary(date, tz),
          mindfulnessApi.sessions(),
          mindfulnessApi.logs(),
        ]);
      setData({
        stressSummary,
        stressLogs: stressList.items,
        mindSummary,
        sessions: sessions.items,
        mindLogs: mindLogs.items,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load your wellbeing data.");
    } finally {
      setIsLoading(false);
    }
  }, [tz]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error, reload: load };
}
