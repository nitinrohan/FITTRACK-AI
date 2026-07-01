/**
 * Goals API - typed wrappers around the FitTrack FastAPI goals endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from "@/lib/api-client";
import type {
  CreateGoalPayload,
  Goal,
  GoalListResponse,
  UpdateGoalPayload,
} from "@/types/goals";

export interface ListGoalsParams {
  status?: string;
  goal_type?: string;
  page?: number;
  page_size?: number;
}

export const goalsApi = {
  list(params: ListGoalsParams = {}): Promise<GoalListResponse> {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.goal_type) qs.set("goal_type", params.goal_type);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));

    const query = qs.toString();
    return apiClient.get<GoalListResponse>(
      `/goals${query ? `?${query}` : ""}`
    );
  },

  get(id: string): Promise<Goal> {
    return apiClient.get<Goal>(`/goals/${id}`);
  },

  create(body: CreateGoalPayload): Promise<Goal> {
    return apiClient.post<Goal>("/goals", body);
  },

  update(id: string, body: UpdateGoalPayload): Promise<Goal> {
    return apiClient.put<Goal>(`/goals/${id}`, body);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/goals/${id}`);
  },
};
