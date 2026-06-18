"use client";

/**
 * useMeasurements — data hook for body measurements page.
 */

import { useCallback, useEffect, useState } from "react";
import { measurementsApi } from "@/lib/measurements-api";
import type {
  BodyMeasurement,
  CreateMeasurementPayload,
  MeasurementListResponse,
  UpdateMeasurementPayload,
} from "@/types/measurements";

interface UseMeasurementsState {
  data: MeasurementListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function useMeasurements(pageSize = 20) {
  const [state, setState] = useState<UseMeasurementsState>({
    data: null,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const data = await measurementsApi.list({ page_size: pageSize });
      setState({ data, isLoading: false, error: null });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load measurements";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, [pageSize]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logMeasurement = useCallback(
    async (payload: CreateMeasurementPayload): Promise<BodyMeasurement> => {
      const entry = await measurementsApi.create(payload);
      await refresh();
      return entry;
    },
    [refresh]
  );

  const updateMeasurement = useCallback(
    async (id: string, payload: UpdateMeasurementPayload): Promise<void> => {
      await measurementsApi.update(id, payload);
      await refresh();
    },
    [refresh]
  );

  const deleteMeasurement = useCallback(
    async (id: string): Promise<void> => {
      await measurementsApi.delete(id);
      await refresh();
    },
    [refresh]
  );

  return {
    entries: state.data?.entries ?? [],
    total: state.data?.total ?? 0,
    latest: state.data?.latest ?? null,
    hasNext: state.data?.has_next ?? false,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    logMeasurement,
    updateMeasurement,
    deleteMeasurement,
  };
}
