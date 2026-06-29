/**
 * Weight API - typed wrappers around the FitTrack FastAPI weight endpoints.
 */

import { apiClient } from "@/lib/api-client";
import type {
  LogWeightPayload,
  UpdateWeightPayload,
  WeightEntry,
  WeightListResponse,
} from "@/types/weight";

export interface ListWeightParams {
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export const weightApi = {
  list(params: ListWeightParams = {}): Promise<WeightListResponse> {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set("date_from", params.date_from);
    if (params.date_to) qs.set("date_to", params.date_to);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return apiClient.get<WeightListResponse>(`/weight${query ? `?${query}` : ""}`);
  },

  get(id: string): Promise<WeightEntry> {
    return apiClient.get<WeightEntry>(`/weight/${id}`);
  },

  log(body: LogWeightPayload): Promise<WeightEntry> {
    return apiClient.post<WeightEntry>("/weight", body);
  },

  update(id: string, body: UpdateWeightPayload): Promise<WeightEntry> {
    return apiClient.put<WeightEntry>(`/weight/${id}`, body);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/weight/${id}`);
  },
};
