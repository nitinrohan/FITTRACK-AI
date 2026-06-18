/**
 * Dashboard API — typed wrapper for GET /api/v1/dashboard/summary.
 */

import { apiClient } from "@/lib/api-client";
import type { DashboardSummary } from "@/types/dashboard";

export const dashboardApi = {
  getSummary(): Promise<DashboardSummary> {
    return apiClient.get<DashboardSummary>("/api/v1/dashboard/summary");
  },
};
