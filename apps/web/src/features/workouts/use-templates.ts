"use client";

/**
 * useTemplates - data hook for workout templates.
 */

import { useCallback, useEffect, useState } from "react";
import { templatesApi } from "@/lib/workouts-api";
import type {
  CreateTemplatePayload,
  UpdateTemplatePayload,
  WorkoutTemplate,
} from "@/types/workouts";

interface UseTemplatesState {
  templates: WorkoutTemplate[];
  total: number;
  isLoading: boolean;
  error: string | null;
}

export function useTemplates() {
  const [state, setState] = useState<UseTemplatesState>({
    templates: [],
    total: 0,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const data = await templatesApi.list({ page_size: 100 });
      setState({
        templates: data.templates,
        total: data.total,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load templates";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createTemplate = useCallback(
    async (payload: CreateTemplatePayload): Promise<WorkoutTemplate> => {
      const tpl = await templatesApi.create(payload);
      await refresh();
      return tpl;
    },
    [refresh]
  );

  const updateTemplate = useCallback(
    async (id: string, payload: UpdateTemplatePayload): Promise<WorkoutTemplate> => {
      const tpl = await templatesApi.update(id, payload);
      await refresh();
      return tpl;
    },
    [refresh]
  );

  const deleteTemplate = useCallback(
    async (id: string): Promise<void> => {
      await templatesApi.delete(id);
      await refresh();
    },
    [refresh]
  );

  return {
    templates: state.templates,
    total: state.total,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    createTemplate,
    updateTemplate,
    deleteTemplate,
  };
}
