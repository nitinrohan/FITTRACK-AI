/**
 * Shared TypeScript types for authentication and user data.
 * Mirrors the shapes returned by the backend API.
 */

export interface UserProfile {
  display_name: string | null;
  avatar_url: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
  experience_level: string | null;
  country_code: string | null;
}

export interface UserPreferences {
  unit_system: "metric" | "imperial";
  timezone: string;
  language: string;
  first_day_of_week: number;
  email_notifications_enabled: boolean;
  ai_features_enabled: boolean;
}

export interface User {
  id: string;
  email: string;
  is_verified: boolean;
  role: string;
  created_at: string;
  profile: UserProfile | null;
  preferences: UserPreferences | null;
}

export interface AuthResponse {
  user: User;
  message: string;
}
