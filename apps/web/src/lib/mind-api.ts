/**
 * Mind API - typed wrappers for the stress and mindfulness endpoints.
 */

import { apiClient } from "@/lib/api-client";
import type {
  MindfulnessDailySummary,
  MindfulnessLog,
  MindfulnessLogListResponse,
  MindfulnessSessionListResponse,
  StressDailySummary,
  StressListResponse,
  StressLog,
} from "@/types/mind";

export interface LogStressPayload {
  level: number;
  note?: string | null;
}

export interface LogMindfulnessPayload {
  duration_minutes: number;
  session_id?: string | null;
  note?: string | null;
}

export const stressApi = {
  summary(date: string, tz: string): Promise<StressDailySummary> {
    return apiClient.get<StressDailySummary>(
      `/api/v1/stress/summary?date=${date}&tz=${encodeURIComponent(tz)}`
    );
  },
  list(): Promise<StressListResponse> {
    return apiClient.get<StressListResponse>("/api/v1/stress?page_size=10");
  },
  log(payload: LogStressPayload): Promise<StressLog> {
    return apiClient.post<StressLog>("/api/v1/stress", payload);
  },
  remove(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/stress/${id}`);
  },
};

export const mindfulnessApi = {
  summary(date: string, tz: string): Promise<MindfulnessDailySummary> {
    return apiClient.get<MindfulnessDailySummary>(
      `/api/v1/mindfulness/summary?date=${date}&tz=${encodeURIComponent(tz)}`
    );
  },
  sessions(): Promise<MindfulnessSessionListResponse> {
    return apiClient.get<MindfulnessSessionListResponse>("/api/v1/mindfulness/sessions");
  },
  logs(): Promise<MindfulnessLogListResponse> {
    return apiClient.get<MindfulnessLogListResponse>("/api/v1/mindfulness/logs?page_size=10");
  },
  log(payload: LogMindfulnessPayload): Promise<MindfulnessLog> {
    return apiClient.post<MindfulnessLog>("/api/v1/mindfulness/logs", payload);
  },
  removeLog(id: string): Promise<void> {
    return apiClient.delete<void>(`/api/v1/mindfulness/logs/${id}`);
  },
};
