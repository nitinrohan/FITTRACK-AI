"use client";

/**
 * Onboarding wizard - /onboarding
 *
 * Shown once to new users after registration (onboarding_completed = false).
 * Four steps:
 *   1. Display name
 *   2. Unit system (metric / imperial)
 *   3. Timezone
 *   4. Experience level
 *   → Complete screen → redirect to /dashboard
 *
 * Each "Next" press POSTs to /api/v1/users/me/onboarding with the
 * step number and the fields collected on that screen.  The final step
 * sets completed=true.  If the user refreshes mid-wizard their progress
 * is already saved so they land back on the correct step.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/use-auth";
import { usersApi } from "@/lib/users-api";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// ── Constants ─────────────────────────────────────────────────────────────────

const TOTAL_STEPS = 4;

// Common IANA timezones grouped for the picker.
const COMMON_TIMEZONES = [
  { label: "UTC", value: "UTC" },
  { label: "Americas", options: [
    { label: "New York (ET)", value: "America/New_York" },
    { label: "Chicago (CT)", value: "America/Chicago" },
    { label: "Denver (MT)", value: "America/Denver" },
    { label: "Los Angeles (PT)", value: "America/Los_Angeles" },
    { label: "Anchorage (AKT)", value: "America/Anchorage" },
    { label: "Honolulu (HT)", value: "Pacific/Honolulu" },
    { label: "São Paulo", value: "America/Sao_Paulo" },
    { label: "Toronto", value: "America/Toronto" },
    { label: "Vancouver", value: "America/Vancouver" },
  ]},
  { label: "Europe", options: [
    { label: "London (GMT/BST)", value: "Europe/London" },
    { label: "Paris (CET)", value: "Europe/Paris" },
    { label: "Berlin (CET)", value: "Europe/Berlin" },
    { label: "Madrid", value: "Europe/Madrid" },
    { label: "Rome", value: "Europe/Rome" },
    { label: "Amsterdam", value: "Europe/Amsterdam" },
    { label: "Stockholm", value: "Europe/Stockholm" },
    { label: "Warsaw", value: "Europe/Warsaw" },
    { label: "Helsinki", value: "Europe/Helsinki" },
    { label: "Moscow", value: "Europe/Moscow" },
    { label: "Istanbul", value: "Europe/Istanbul" },
  ]},
  { label: "Asia & Pacific", options: [
    { label: "Dubai (GST)", value: "Asia/Dubai" },
    { label: "Kolkata (IST)", value: "Asia/Kolkata" },
    { label: "Dhaka", value: "Asia/Dhaka" },
    { label: "Bangkok", value: "Asia/Bangkok" },
    { label: "Singapore", value: "Asia/Singapore" },
    { label: "Shanghai", value: "Asia/Shanghai" },
    { label: "Tokyo (JST)", value: "Asia/Tokyo" },
    { label: "Seoul", value: "Asia/Seoul" },
    { label: "Sydney", value: "Australia/Sydney" },
    { label: "Melbourne", value: "Australia/Melbourne" },
    { label: "Auckland", value: "Pacific/Auckland" },
  ]},
  { label: "Africa", options: [
    { label: "Cairo (EET)", value: "Africa/Cairo" },
    { label: "Lagos (WAT)", value: "Africa/Lagos" },
    { label: "Nairobi (EAT)", value: "Africa/Nairobi" },
    { label: "Johannesburg (SAST)", value: "Africa/Johannesburg" },
  ]},
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface WizardState {
  displayName: string;
  unitSystem: "metric" | "imperial";
  timezone: string;
  experienceLevel: "beginner" | "intermediate" | "advanced" | "";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();

  const initialStep = user?.profile?.onboarding_step ?? 0;
  const [step, setStep] = useState<number>(
    user?.profile?.onboarding_completed ? TOTAL_STEPS + 1 : initialStep
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<WizardState>({
    displayName: user?.profile?.display_name ?? "",
    unitSystem: (user?.preferences?.unit_system as "metric" | "imperial") ?? "metric",
    timezone: user?.preferences?.timezone ?? guessTimezone(),
    experienceLevel:
      (user?.profile?.experience_level as WizardState["experienceLevel"]) ?? "",
  });

  // ── Helpers ────────────────────────────────────────────────────────────────

  function update<K extends keyof WizardState>(key: K, value: WizardState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setError(null);
  }

  async function advance(isLast = false) {
    setIsSubmitting(true);
    setError(null);
    const nextStep = step + 1;

    try {
      await usersApi.completeOnboardingStep({
        step: nextStep,
        completed: isLast,
        profile: buildProfilePayload(step),
        preferences: buildPrefsPayload(step),
      });
      setStep(nextStep);
      if (isLast) {
        // Refresh auth context so needsOnboarding becomes false before
        // the dashboard layout mounts - prevents the redirect loop.
        await refreshUser();
        router.push("/dashboard");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message ?? "Something went wrong. Please try again.");
      } else {
        setError("Connection error. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function buildProfilePayload(currentStep: number) {
    if (currentStep === 0) return { display_name: form.displayName || null };
    if (currentStep === 3) return { experience_level: form.experienceLevel || null };
    return undefined;
  }

  function buildPrefsPayload(currentStep: number) {
    if (currentStep === 1) return { unit_system: form.unitSystem };
    if (currentStep === 2) return { timezone: form.timezone };
    return undefined;
  }

  // ── Progress bar ───────────────────────────────────────────────────────────

  const progress = Math.round((step / TOTAL_STEPS) * 100);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex min-h-screen flex-col bg-surface-50">
      {/* Header */}
      <header className="border-b border-surface-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500">
            <svg className="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
              <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
              <line x1="6" y1="1" x2="6" y2="4" />
              <line x1="10" y1="1" x2="10" y2="4" />
              <line x1="14" y1="1" x2="14" y2="4" />
            </svg>
          </div>
          <span className="font-semibold text-surface-900">FitTrack AI</span>
          {step < TOTAL_STEPS && (
            <span className="ml-auto text-xs text-surface-400">
              Step {step + 1} of {TOTAL_STEPS}
            </span>
          )}
        </div>
      </header>

      {/* Progress bar */}
      {step < TOTAL_STEPS && (
        <div className="h-1 bg-surface-200" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Onboarding progress">
          <div
            className="h-full bg-brand-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Step content */}
      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          {error && (
            <div role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {step === 0 && (
            <StepName
              value={form.displayName}
              onChange={(v) => update("displayName", v)}
              onNext={() => advance()}
              isSubmitting={isSubmitting}
            />
          )}
          {step === 1 && (
            <StepUnits
              value={form.unitSystem}
              onChange={(v) => update("unitSystem", v)}
              onNext={() => advance()}
              isSubmitting={isSubmitting}
            />
          )}
          {step === 2 && (
            <StepTimezone
              value={form.timezone}
              onChange={(v) => update("timezone", v)}
              onNext={() => advance()}
              isSubmitting={isSubmitting}
            />
          )}
          {step === 3 && (
            <StepExperience
              value={form.experienceLevel}
              onChange={(v) => update("experienceLevel", v)}
              onNext={() => advance(true)}
              isSubmitting={isSubmitting}
            />
          )}
          {step >= TOTAL_STEPS && <StepDone />}
        </div>
      </main>
    </div>
  );
}

// ── Step 1: Name ──────────────────────────────────────────────────────────────

function StepName({
  value,
  onChange,
  onNext,
  isSubmitting,
}: {
  value: string;
  onChange: (v: string) => void;
  onNext: () => void;
  isSubmitting: boolean;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Welcome to FitTrack!</h1>
        <p className="mt-2 text-surface-500">
          Let&apos;s set up your account. This only takes a minute.
        </p>
      </div>

      <Input
        label="What should we call you?"
        type="text"
        autoComplete="given-name"
        placeholder="Your name (optional)"
        hint="This is how you'll be greeted in the app."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus
      />

      <Button fullWidth isLoading={isSubmitting} onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}

// ── Step 2: Units ─────────────────────────────────────────────────────────────

function StepUnits({
  value,
  onChange,
  onNext,
  isSubmitting,
}: {
  value: "metric" | "imperial";
  onChange: (v: "metric" | "imperial") => void;
  onNext: () => void;
  isSubmitting: boolean;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Which units do you prefer?</h1>
        <p className="mt-2 text-surface-500">
          You can change this any time in your settings.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Unit system">
        {(
          [
            { id: "metric", label: "Metric", sub: "kg, cm, km" },
            { id: "imperial", label: "Imperial", sub: "lb, in, mi" },
          ] as const
        ).map((opt) => (
          <button
            key={opt.id}
            type="button"
            role="radio"
            aria-checked={value === opt.id}
            onClick={() => onChange(opt.id)}
            className={`rounded-xl border-2 px-4 py-5 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
              value === opt.id
                ? "border-brand-500 bg-brand-50"
                : "border-surface-200 bg-white hover:border-surface-300"
            }`}
          >
            <div className="font-semibold text-surface-900">{opt.label}</div>
            <div className="mt-0.5 text-sm text-surface-500">{opt.sub}</div>
          </button>
        ))}
      </div>

      <Button fullWidth isLoading={isSubmitting} onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}

// ── Step 3: Timezone ──────────────────────────────────────────────────────────

function StepTimezone({
  value,
  onChange,
  onNext,
  isSubmitting,
}: {
  value: string;
  onChange: (v: string) => void;
  onNext: () => void;
  isSubmitting: boolean;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">What&apos;s your timezone?</h1>
        <p className="mt-2 text-surface-500">
          Used to show workout times and streaks correctly.
        </p>
      </div>

      <div className="space-y-1">
        <label htmlFor="timezone" className="block text-sm font-medium text-surface-700">
          Timezone
        </label>
        <select
          id="timezone"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="block w-full min-h-touch rounded-lg border border-surface-200 bg-white px-3 py-2.5 text-sm text-surface-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        >
          {COMMON_TIMEZONES.map((group) =>
            "options" in group && group.options ? (
              <optgroup key={group.label} label={group.label}>
                {group.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </optgroup>
            ) : (
              <option key={group.value} value={group.value}>
                {group.label}
              </option>
            )
          )}
        </select>
      </div>

      <Button fullWidth isLoading={isSubmitting} onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}

// ── Step 4: Experience level ──────────────────────────────────────────────────

const EXPERIENCE_OPTIONS = [
  {
    id: "beginner" as const,
    label: "Beginner",
    description: "New to structured exercise or getting back into it.",
  },
  {
    id: "intermediate" as const,
    label: "Intermediate",
    description: "Training consistently for 6+ months.",
  },
  {
    id: "advanced" as const,
    label: "Advanced",
    description: "Several years of structured training.",
  },
];

function StepExperience({
  value,
  onChange,
  onNext,
  isSubmitting,
}: {
  value: string;
  onChange: (v: "beginner" | "intermediate" | "advanced" | "") => void;
  onNext: () => void;
  isSubmitting: boolean;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900">Your experience level?</h1>
        <p className="mt-2 text-surface-500">
          Helps us tailor suggestions. You can change this later.
        </p>
      </div>

      <div className="space-y-3" role="radiogroup" aria-label="Experience level">
        {EXPERIENCE_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            role="radio"
            aria-checked={value === opt.id}
            onClick={() => onChange(opt.id)}
            className={`w-full rounded-xl border-2 px-4 py-4 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
              value === opt.id
                ? "border-brand-500 bg-brand-50"
                : "border-surface-200 bg-white hover:border-surface-300"
            }`}
          >
            <div className="font-semibold text-surface-900">{opt.label}</div>
            <div className="mt-0.5 text-sm text-surface-500">{opt.description}</div>
          </button>
        ))}
      </div>

      <Button
        fullWidth
        isLoading={isSubmitting}
        onClick={onNext}
        disabled={!value}
      >
        Finish setup
      </Button>
      {!value && (
        <p className="text-center text-xs text-surface-400">
          Select an option above to continue
        </p>
      )}
    </div>
  );
}

// ── Completion ────────────────────────────────────────────────────────────────

function StepDone() {
  const router = useRouter();
  return (
    <div className="space-y-6 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-100">
        <svg className="h-8 w-8 text-brand-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div>
        <h1 className="text-2xl font-bold text-surface-900">You&apos;re all set!</h1>
        <p className="mt-2 text-surface-500">
          Your account is ready. Let&apos;s start tracking.
        </p>
      </div>
      <Button fullWidth onClick={() => router.push("/dashboard")}>
        Go to dashboard
      </Button>
    </div>
  );
}

// ── Utility ───────────────────────────────────────────────────────────────────

function guessTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone ?? "UTC";
  } catch {
    return "UTC";
  }
}
