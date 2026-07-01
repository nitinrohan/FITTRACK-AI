"use client";

/**
 * useRecipes - data hook for the recipes list/CRUD/log flow.
 */

import { useCallback, useEffect, useState } from "react";
import { recipesApi } from "@/lib/recipe-api";
import type {
  CreateRecipePayload,
  LogRecipePayload,
  Recipe,
  UpdateRecipePayload,
} from "@/types/recipe";

interface UseRecipesState {
  recipes: Recipe[];
  total: number;
  isLoading: boolean;
  error: string | null;
}

export function useRecipes(search: string = "") {
  const [state, setState] = useState<UseRecipesState>({
    recipes: [],
    total: 0,
    isLoading: true,
    error: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const data = await recipesApi.list({ search: search || undefined, page_size: 100 });
      setState({ recipes: data.recipes, total: data.total, isLoading: false, error: null });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load recipes";
      setState((s) => ({ ...s, isLoading: false, error: msg }));
    }
  }, [search]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (payload: CreateRecipePayload): Promise<Recipe> => {
      const recipe = await recipesApi.create(payload);
      await refresh();
      return recipe;
    },
    [refresh]
  );

  const update = useCallback(
    async (id: string, payload: UpdateRecipePayload): Promise<void> => {
      await recipesApi.update(id, payload);
      await refresh();
    },
    [refresh]
  );

  const remove = useCallback(
    async (id: string): Promise<void> => {
      await recipesApi.delete(id);
      await refresh();
    },
    [refresh]
  );

  const logRecipe = useCallback(
    async (id: string, payload: LogRecipePayload) => {
      return recipesApi.log(id, payload);
    },
    []
  );

  return {
    recipes: state.recipes,
    total: state.total,
    isLoading: state.isLoading,
    error: state.error,
    refresh,
    create,
    update,
    remove,
    logRecipe,
  };
}
