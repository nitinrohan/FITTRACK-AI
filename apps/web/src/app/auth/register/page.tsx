"use client";

/**
 * Register page - /auth/register
 *
 * - React Hook Form + Zod: email, password (min 8), confirm password, display name.
 * - Calls auth context register() which POST /api/v1/auth/register.
 * - On success, redirects to /dashboard.
 * - Displays inline API errors (email taken, server error).
 * - Password requirements are shown as a hint so users know what to expect.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { registerSchema, type RegisterFormValues } from "@/schemas/auth";
import { useAuth } from "@/features/auth/use-auth";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      displayName: "",
    },
  });

  async function onSubmit(values: RegisterFormValues) {
    setServerError(null);
    try {
      await registerUser(
        values.email,
        values.password,
        values.displayName?.trim() || undefined
      );
      // New users always go through onboarding before the dashboard.
      router.push("/onboarding");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.statusCode === 409) {
          setServerError(
            "An account with that email already exists. Try signing in instead."
          );
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
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4 py-8">
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
          <h1 className="text-2xl font-bold text-surface-900">Create your account</h1>
          <p className="mt-1 text-sm text-surface-500">
            Start tracking your fitness journey
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
              label="Name"
              type="text"
              autoComplete="name"
              placeholder="Your name (optional)"
              hint="This is how you'll be greeted in the app."
              error={errors.displayName?.message}
              {...register("displayName")}
            />

            <Input
              label="Email"
              type="email"
              autoComplete="email"
              inputMode="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              required
              {...register("email")}
            />

            <Input
              label="Password"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              hint="At least 8 characters."
              error={errors.password?.message}
              required
              {...register("password")}
            />

            <Input
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              error={errors.confirmPassword?.message}
              required
              {...register("confirmPassword")}
            />

            <Button
              type="submit"
              fullWidth
              isLoading={isSubmitting}
              className="mt-2"
            >
              Create account
            </Button>
          </form>
        </div>

        {/* Privacy note */}
        <p className="mt-3 text-center text-xs text-surface-400">
          Your fitness data is private by default and never shared.
        </p>

        {/* Switch to login */}
        <p className="mt-4 text-center text-sm text-surface-500">
          Already have an account?{" "}
          <Link
            href="/auth/login"
            className="font-medium text-brand-600 hover:underline focus-visible:outline-brand-500"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
