/**
 * Typed wrappers around /api/v1/users/* endpoints.
 * Components import these instead of calling apiClient directly.
 */

import { apiClient } from "@/lib/api-client";
import type { UserProfile, UserPreferences } from "@/types/auth";

export interface UpdateProfilePayload {
  display_name?: string | null;
  bio?: string | null;
  date_of_birth?: string | null;
  height_cm?: number | null;
  biological_sex?: "male" | "female" | "intersex" | "prefer_not_to_say" | null;
  experience_level?: "beginner" | "intermediate" | "advanced" | null;
  country_code?: string | null;
}

export interface UpdatePreferencesPayload {
  unit_system?: "metric" | "imperial";
  timezone?: string;
  language?: string;
  first_day_of_week?: 0 | 1 | 6;
  email_notifications_enabled?: boolean;
  ai_features_enabled?: boolean;
}

export interface OnboardingStepPayload {
  step: number;
  completed?: boolean;
  profile?: UpdateProfilePayload;
  preferences?: UpdatePreferencesPayload;
}

export interface OnboardingStatusResponse {
  onboarding_completed: boolean;
  onboarding_step: number;
}

export const usersApi = {
  updateProfile: (payload: UpdateProfilePayload) =>
    apiClient.put<UserProfile>("/api/v1/users/me/profile", payload),

  updatePreferences: (payload: UpdatePreferencesPayload) =>
    apiClient.put<UserPreferences>("/api/v1/users/me/preferences", payload),

  completeOnboardingStep: (payload: OnboardingStepPayload) =>
    apiClient.post<OnboardingStatusResponse>("/api/v1/users/me/onboarding", payload),
};
