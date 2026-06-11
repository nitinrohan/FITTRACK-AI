"use client";

/**
 * Login page — /auth/login
 *
 * - React Hook Form + Zod validation.
 * - Calls auth context login() which POST /api/v1/auth/login.
 * - On success, redirects to /dashboard (or returnTo param).
 * - Displays inline API errors (wrong password, server error).
 * - Accessible: visible focus, error announcements, no autofocus on error.
 */

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { loginSchema, type LoginFormValues } from "@/schemas/auth";
import { useAuth } from "@/features/auth/use-auth";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") ?? "/dashboard";
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      // If the user hasn't finished onboarding, send them there first.
      // The auth context doesn't update until after this call resolves,
      // so we check by reading the /me response implicitly via the context
      // after re-render — but to be safe, we always check on the server
      // by redirecting to /dashboard which will itself redirect if needed.
      router.push(returnTo);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.isUnauthorized) {
          setServerError("Invalid email or password. Please try again.");
        } else {
          setServerError(
            err.message ?? "Something went wrong. Please try again."
          );
        }
      } else {
        setServerError("Unable to connect. Please check your connection and try again.");
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo / brand */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500">
            <svg
              className="h-7 w-7 text-white"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
              <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
              <line x1="6" y1="1" x2="6" y2="4" />
              <line x1="10" y1="1" x2="10" y2="4" />
              <line x1="14" y1="1" x2="14" y2="4" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-surface-900">Welcome back</h1>
          <p className="mt-1 text-sm text-surface-500">
            Sign in to your FitTrack account
          </p>
        </div>

        {/* Form card */}
        <div className="rounded-2xl border border-surface-200 bg-white p-6 shadow-sm">
          {/* Server error banner */}
          {serverError && (
            <div
              role="alert"
              className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {serverError}
            </div>
          )}

          <form
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            className="space-y-4"
          >
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register("email")}
            />

            <div className="space-y-1">
              <Input
                label="Password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                error={errors.password?.message}
                {...register("password")}
              />
              <div className="flex justify-end">
                {/* Placeholder — password reset is a future feature */}
                <span
                  className="text-xs text-surface-400"
                  aria-label="Password reset not yet available"
                >
                  Forgot password? (coming soon)
                </span>
              </div>
            </div>

            <Button
              type="submit"
              fullWidth
              isLoading={isSubmitting}
              className="mt-2"
            >
              Sign in
            </Button>
          </form>
        </div>

        {/* Switch to register */}
        <p className="mt-4 text-center text-sm text-surface-500">
          Don&apos;t have an account?{" "}
          <Link
            href="/auth/register"
            className="font-medium text-brand-600 hover:underline focus-visible:outline-brand-500"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
