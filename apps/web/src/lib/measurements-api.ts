/**
 * Measurements API - typed wrappers around the FitTrack FastAPI
 * /api/v1/measurements endpoints.
 *
 * All functions throw ApiError on non-2xx responses.
 */

import { apiClient } from "@/lib/api-client";
import type {
  BodyMeasurement,
  CreateMeasurementPayload,
  MeasurementListResponse,
  UpdateMeasurementPayload,
} from "@/types/measurements";

export const measurementsApi = {
  list(params: {
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<MeasurementListResponse> {
    const qs = new URLSearchParams();
    if (params.date_from) qs.set("date_from", params.date_from);
    if (params.date_to) qs.set("date_to", params.date_to);
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    const query = qs.toString();
    return apiClient.get<MeasurementListResponse>(
      `/api/v1/measurements${query ? `?${query}` : ""}`
    );
  },

  get(id: string): Promise<BodyMeasurement> {
    return apiClient.get<BodyMeasurement>(`/api/v1/measurements/${id}`);
  },

  create(payload: CreateMeasurementPayload): Promise<BodyMeasurement> {
    return apiClient.post<BodyMeasurement>("/api/v1/measurements", payload);
  },

  update(id: string, payload: UpdateMeasurementPayload): Promise<BodyMeasurement> {
    return apiClient.patch<BodyMeasurement>(`/api/v1/measurements/${id}`, payload);
  },

  delete(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/measurements/${id}`);
  },
};
