"use client";

/**
 * AuthContext — provides the current user and auth actions to the component tree.
 *
 * Design:
 * - Fetches /api/v1/auth/me on mount to restore session from the HTTP-only cookie.
 * - Exposes login(), register(), logout() so components never call the API directly.
 * - On 401 from /me, treats the user as unauthenticated (cookie expired or absent).
 * - Uses React context + useReducer for predictable state transitions.
 *
 * Usage:
 *   Wrap your layout (or a route group) with <AuthProvider>.
 *   Components call useAuth() to get { user, isLoading, login, register, logout }.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
} from "react";

import { ApiError, apiClient } from "@/lib/api-client";
import type { AuthResponse, User } from "@/types/auth";

// ── State & actions ──────────────────────────────────────────────────────────

interface AuthState {
  user: User | null;
  /** True during the initial /me check and any auth action. */
  isLoading: boolean;
  /** True once the initial /me check has completed (regardless of result). */
  isInitialized: boolean;
}

type AuthAction =
  | { type: "LOADING" }
  | { type: "SET_USER"; user: User }
  | { type: "CLEAR_USER" }
  | { type: "INITIALIZED" };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "LOADING":
      return { ...state, isLoading: true };
    case "SET_USER":
      return { user: action.user, isLoading: false, isInitialized: true };
    case "CLEAR_USER":
      return { user: null, isLoading: false, isInitialized: true };
    case "INITIALIZED":
      return { ...state, isLoading: false, isInitialized: true };
    default:
      return state;
  }
}

// ── Context shape ─────────────────────────────────────────────────────────────

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-fetch /auth/me and update the user in context. */
  refreshUser: () => Promise<void>;
  /** True when the user is authenticated but hasn't completed onboarding. */
  needsOnboarding: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    isLoading: true,
    isInitialized: false,
  });

  // On mount, try to restore the session from the existing cookie.
  useEffect(() => {
    let cancelled = false;

    apiClient
      .get<User>("/api/v1/auth/me")
      .then((user) => {
        if (!cancelled) dispatch({ type: "SET_USER", user });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // 401 = no valid session — expected when unauthenticated.
        if (err instanceof ApiError && err.isUnauthorized) {
          dispatch({ type: "CLEAR_USER" });
        } else {
          // Network error or unexpected — still mark initialized so the UI
          // can render (the user will see an unauthenticated state).
          console.error("[AuthContext] Failed to restore session:", err);
          dispatch({ type: "CLEAR_USER" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    dispatch({ type: "LOADING" });
    const data = await apiClient.post<AuthResponse>("/api/v1/auth/login", {
      email,
      password,
    });
    dispatch({ type: "SET_USER", user: data.user });
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      dispatch({ type: "LOADING" });
      const data = await apiClient.post<AuthResponse>(
        "/api/v1/auth/register",
        {
          email,
          password,
          display_name: displayName ?? null,
        }
      );
      dispatch({ type: "SET_USER", user: data.user });
    },
    []
  );

  const refreshUser = useCallback(async () => {
    try {
      const user = await apiClient.get<User>("/api/v1/auth/me");
      dispatch({ type: "SET_USER", user });
    } catch {
      // If refresh fails, leave state unchanged.
    }
  }, []);

  const logout = useCallback(async () => {
    dispatch({ type: "LOADING" });
    try {
      await apiClient.post("/api/v1/auth/logout", undefined);
    } catch {
      // Ignore server errors on logout — clear local state regardless.
    }
    dispatch({ type: "CLEAR_USER" });
  }, []);

  const needsOnboarding =
    state.isInitialized &&
    state.user !== null &&
    state.user.profile?.onboarding_completed === false;

  const value: AuthContextValue = {
    ...state,
    login,
    register,
    logout,
    refreshUser,
    needsOnboarding,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
