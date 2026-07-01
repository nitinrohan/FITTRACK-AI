import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Welcome",
};

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-surface-50 to-surface-100 p-6">
      <div className="w-full max-w-md space-y-8 text-center">
        {/* Logo mark */}
        <div
          className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500"
          aria-hidden="true"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-9 w-9 text-white"
            aria-hidden="true"
          >
            <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
            <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
            <line x1="6" y1="1" x2="6" y2="4" />
            <line x1="10" y1="1" x2="10" y2="4" />
            <line x1="14" y1="1" x2="14" y2="4" />
          </svg>
        </div>

        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-surface-900">
            FitTrack AI
          </h1>
          <p className="text-lg text-surface-500">
            Your personal fitness companion
          </p>
        </div>

        <p className="text-surface-600">
          Track workouts, nutrition, measurements, and habits with AI-powered
          insights to help you stay consistent and reach your goals.
        </p>

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/auth/register"
            className="inline-flex min-h-touch items-center justify-center rounded-lg bg-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
          >
            Get started - it&apos;s free
          </Link>
          <Link
            href="/auth/login"
            className="inline-flex min-h-touch items-center justify-center rounded-lg border border-surface-200 bg-white px-6 py-3 text-sm font-semibold text-surface-700 shadow-sm transition-colors hover:bg-surface-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
          >
            Sign in
          </Link>
        </div>

        {/* Phase indicator - remove once MVP screens are built */}
        <p className="text-xs text-surface-400" aria-label="Development phase">
          Phase 1 - Foundation
        </p>
      </div>
    </main>
  );
}
