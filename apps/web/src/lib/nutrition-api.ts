/**
 * Nutrition API — typed wrappers around the FitTrack FastAPI nutrition endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from "@/lib/api-client";
import type {
  CreateFoodPayload,
  DailyNutrition,
  Food,
  FoodListResponse,
  FoodLogEntry,
  LogFoodPayload,
  LogWaterPayload,
  MacroEstimate,
  UpdateFoodLogPayload,
  UpdateFoodPayload,
  UpdateWaterLogPayload,
  WaterLogEntry,
} from "@/types/nutrition";

// ── Food library ──────────────────────────────────────────────────────────────

export const foodsApi = {
  search(params: { search?: string; page?: number; page_size?: number } = {}): Promise<FoodListResponse> {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return apiClient.get<FoodListResponse>(
      `/api/v1/foods${query ? `?${query}` : ""}`
    );
  },

  get(id: string): Promise<Food> {
    return apiClient.get<Food>(`/api/v1/foods/${id}`);
  },

  create(payload: CreateFoodPayload): Promise<Food> {
    return apiClient.post<Food>("/api/v1/foods", payload);
  },

  update(id: string, payload: UpdateFoodPayload): Promise<Food> {
    return apiClient.patch<Food>(`/api/v1/foods/${id}`, payload);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/foods/${id}`);
  },
};

// ── Nutrition log ─────────────────────────────────────────────────────────────

export const nutritionApi = {
  /** Get all food and water entries for a given date (YYYY-MM-DD). */
  getDaily(date: string): Promise<DailyNutrition> {
    return apiClient.get<DailyNutrition>(
      `/api/v1/nutrition/daily?date=${encodeURIComponent(date)}`
    );
  },

  /** Log a food entry for a meal. */
  logFood(payload: LogFoodPayload): Promise<FoodLogEntry> {
    return apiClient.post<FoodLogEntry>("/api/v1/nutrition/foods", payload);
  },

  /** Update an existing food log entry. */
  updateFoodLog(id: string, payload: UpdateFoodLogPayload): Promise<FoodLogEntry> {
    return apiClient.patch<FoodLogEntry>(`/api/v1/nutrition/foods/${id}`, payload);
  },

  /** Delete a food log entry. */
  deleteFoodLog(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/nutrition/foods/${id}`);
  },

  /** Log water intake. */
  logWater(payload: LogWaterPayload): Promise<WaterLogEntry> {
    return apiClient.post<WaterLogEntry>("/api/v1/nutrition/water", payload);
  },

  /** Update a water log entry. */
  updateWaterLog(id: string, payload: UpdateWaterLogPayload): Promise<WaterLogEntry> {
    return apiClient.patch<WaterLogEntry>(`/api/v1/nutrition/water/${id}`, payload);
  },

  /** Delete a water log entry. */
  deleteWaterLog(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/nutrition/water/${id}`);
  },

  /** Ask the AI to estimate macros for a free-text food description.
   *  Returns a preview only — nothing is saved. */
  estimateMacros(description: string): Promise<MacroEstimate> {
    return apiClient.post<MacroEstimate>("/api/v1/nutrition/estimate-macros", {
      description,
    });
  },

  /** Record whether the user accepted (saved) or dismissed an estimate. */
  recordMacroDecision(log_id: string, accepted: boolean): Promise<void> {
    return apiClient.post<void>("/api/v1/nutrition/estimate-macros/decision", {
      log_id,
      accepted,
    });
  },
};
