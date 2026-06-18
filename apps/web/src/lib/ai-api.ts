/**
 * AI API — typed wrappers for /api/v1/ai/* endpoints.
 */

import { apiClient } from "@/lib/api-client";
import type { AcceptSummaryPayload, WeeklySummaryResponse } from "@/types/ai";

export const aiApi = {
  getWeeklySummary(): Promise<WeeklySummaryResponse> {
    return apiClient.post<WeeklySummaryResponse>("/api/v1/ai/weekly-summary");
  },

  recordDecision(payload: AcceptSummaryPayload): Promise<void> {
    return apiClient.post<void>("/api/v1/ai/weekly-summary/accept", payload);
  },
};
