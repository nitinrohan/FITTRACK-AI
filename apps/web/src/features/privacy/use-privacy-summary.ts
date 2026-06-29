"use client";

/**
 * usePrivacySummary - loads the per-category count of the user's records.
 */

import { useCallback, useEffect, useState } from "react";
import { privacyApi } from "@/lib/privacy-api";
import type { PrivacySummary } from "@/types/privacy";

export function usePrivacySummary() {
  const [summary, setSummary] = useState<PrivacySummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setSummary(await privacyApi.getSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load your data summary.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { summary, isLoading, error, reload: load };
}
