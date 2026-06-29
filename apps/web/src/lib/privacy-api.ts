/**
 * Privacy API - typed wrappers around /api/v1/privacy/*.
 */

import { apiClient } from "@/lib/api-client";
import type {
  AccountDeletedResponse,
  DataExport,
  PrivacySummary,
} from "@/types/privacy";

export const privacyApi = {
  getSummary(): Promise<PrivacySummary> {
    return apiClient.get<PrivacySummary>("/api/v1/privacy/summary");
  },

  exportData(): Promise<DataExport> {
    return apiClient.get<DataExport>("/api/v1/privacy/export");
  },

  deleteAccount(password: string): Promise<AccountDeletedResponse> {
    return apiClient.delete<AccountDeletedResponse>("/api/v1/privacy/account", {
      body: JSON.stringify({ password }),
    });
  },
};
