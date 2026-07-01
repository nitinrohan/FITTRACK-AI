/**
 * Recipes API - typed wrappers around the FitTrack FastAPI recipes endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from "@/lib/api-client";
import type {
  CreateRecipePayload,
  LogRecipePayload,
  LogRecipeResult,
  Recipe,
  RecipeListResponse,
  UpdateRecipePayload,
} from "@/types/recipe";

export const recipesApi = {
  list(params: { search?: string; page?: number; page_size?: number } = {}): Promise<RecipeListResponse> {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return apiClient.get<RecipeListResponse>(`/api/v1/recipes${query ? `?${query}` : ""}`);
  },

  get(id: string): Promise<Recipe> {
    return apiClient.get<Recipe>(`/api/v1/recipes/${id}`);
  },

  create(payload: CreateRecipePayload): Promise<Recipe> {
    return apiClient.post<Recipe>("/api/v1/recipes", payload);
  },

  update(id: string, payload: UpdateRecipePayload): Promise<Recipe> {
    return apiClient.patch<Recipe>(`/api/v1/recipes/${id}`, payload);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/recipes/${id}`);
  },

  /** Re-log a saved recipe as real food-log entries. scale_factor 1.0 =
   *  log exactly as saved (e.g. 0.5 logs half the saved quantities). */
  log(id: string, payload: LogRecipePayload): Promise<LogRecipeResult> {
    return apiClient.post<LogRecipeResult>(`/api/v1/recipes/${id}/log`, payload);
  },
};
