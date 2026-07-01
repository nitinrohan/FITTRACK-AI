/**
 * Progress API - typed wrapper around GET /api/v1/progress.
 */

import { apiClient } from "@/lib/api-client";
import type { ProgressResponse } from "@/types/progress";

export const progressApi = {
  get(days: number): Promise<ProgressResponse> {
    return apiClient.get<ProgressResponse>(`/api/v1/progress?days=${days}`);
  },
};
