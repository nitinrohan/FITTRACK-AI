"use client";

/**
 * Dashboard page — /dashboard
 *
 * Shows:
 * - Welcome greeting
 * - Active goals summary widget (count + average progress ring)
 * - Latest weight widget (current + 7-day avg + trend arrow)
 * - Quick-action buttons
 * - Coming-soon cards for unbuilt features
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useAuth } from "@/features/auth/use-auth";
import { goalsApi } from "@/lib/goals-api";
import { weightApi } from "@/lib/weight-api";
import type { GoalListResponse } from "@/types/goals";
import type { WeightListResponse } from "@/types/weight";

// ── Mini progress ring ────────────────────────────────────────────────────────

function ProgressRing({
  pct,
  size = 56,
  stroke = 5,
  className,
}: {
  pct: number;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  const r = (size - stroke * 2) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const cx = size / 2;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      aria-hidden="true"
    >
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-surface-100"
      />
      <circle
        cx={cx}
        cy={cx}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeDasharray={`${circ} ${circ}`}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-brand-500 transition-all duration-700"
        transform={`rotate(-90 ${cx} ${cx})`}
      />
    </svg>
  );
}

// ── Widget: Goals ─────────────────────────────────────────────────────────────

function GoalsWidget() {
  const [data, setData] = useState<GoalListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    goalsApi
      .list({ status: "active", page_size: 50 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const activeGoals = data?.goals ?? [];
  const avgProgress =
    activeGoals.length > 0
      ? activeGoals.reduce((sum, g) => sum + (g.progress_pct ?? 0), 0) /
        activeGoals.length
      : 0;
  const avgPct = Math.round(avgProgress);

  return (
    <Card>
      <CardBody>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-surface-500">
              Active goals
            </p>
            {loading ? (
              <LoadingSpinner size="sm" label="Loading goals…" />
            ) : (
              <>
                <p className="mt-1 text-3xl font-bold text-surface-900">
                  {activeGoals.length}
                </p>
                {activeGoals.length > 0 && (
                  <p className="mt-0.5 text-xs text-surface-500">
                    {avgPct}% avg progress
                  </p>
                )}
              </>
            )}
          </div>
          {!loading && activeGoals.length > 0 && (
            <ProgressRing
              pct={avgPct}
              size={56}
              stroke={5}
              className="shrink-0"
            />
          )}
          {!loading && activeGoals.length === 0 && (
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-400">
              <svg
                viewBox="0 0 24 24"
                className="h-7 w-7"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4" />
              </svg>
            </div>
          )}
        </div>

        <Link
          href="/dashboard/goals"
          className="mt-4 block text-xs font-medium text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
        >
          {activeGoals.length === 0 ? "Set your first goal →" : "View all goals →"}
        </Link>
      </CardBody>
    </Card>
  );
}

// ── Widget: Weight ────────────────────────────────────────────────────────────

function WeightWidget() {
  const [data, setData] = useState<WeightListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    weightApi
      .list({ page_size: 7 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const stats = data?.stats;
  const hasData = (stats?.count ?? 0) > 0;
  const trend =
    stats?.change_kg !== null && stats?.change_kg !== undefined
      ? stats.change_kg < -0.1
        ? "down"
        : stats.change_kg > 0.1
          ? "up"
          : "stable"
      : null;

  const trendIcon =
    trend === "down" ? (
      <span className="text-emerald-600" aria-label="trending down">↓</span>
    ) : trend === "up" ? (
      <span className="text-red-500" aria-label="trending up">↑</span>
    ) : trend === "stable" ? (
      <span className="text-surface-400" aria-label="stable">→</span>
    ) : null;

  return (
    <Card>
      <CardBody>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-surface-500">
              Latest weight
            </p>
            {loading ? (
              <LoadingSpinner size="sm" label="Loading weight…" />
            ) : hasData ? (
              <>
                <p className="mt-1 flex items-baseline gap-1 text-3xl font-bold text-surface-900">
                  {stats!.latest_kg!.toFixed(1)}
                  <span className="text-base font-medium text-surface-400">kg</span>
                  <span className="text-xl">{trendIcon}</span>
                </p>
                {stats?.moving_avg_7d_kg !== null && (
                  <p className="mt-0.5 text-xs text-surface-500">
                    7-day avg: {stats!.moving_avg_7d_kg!.toFixed(1)} kg
                  </p>
                )}
              </>
            ) : (
              <p className="mt-1 text-sm text-surface-400">No entries yet</p>
            )}
          </div>

          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-sky-50 text-sky-400">
            <svg
              viewBox="0 0 24 24"
              className="h-7 w-7"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </div>
        </div>

        <Link
          href="/dashboard/weight"
          className="mt-4 block text-xs font-medium text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 rounded"
        >
          {hasData ? "View weight history →" : "Start tracking →"}
        </Link>
      </CardBody>
    </Card>
  );
}

// ── Quick actions ─────────────────────────────────────────────────────────────

function QuickActions() {
  return (
    <div className="flex flex-wrap gap-2">
      <Link href="/dashboard/weight">
        <Button variant="secondary" size="sm">
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Log weight
        </Button>
      </Link>
      <Link href="/dashboard/goals">
        <Button variant="secondary" size="sm">
          <svg
            viewBox="0 0 24 24"
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New goal
        </Button>
      </Link>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const greeting = user?.profile?.display_name
    ? `Welcome back, ${user.profile.display_name}!`
    : "Welcome back!";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900">{greeting}</h1>
          <p className="mt-0.5 text-sm text-surface-500">
            Here&rsquo;s how you&rsquo;re doing today.
          </p>
        </div>
      </div>

      {/* Quick actions */}
      <QuickActions />

      {/* Live widgets */}
      <div className="grid gap-4 sm:grid-cols-2">
        <GoalsWidget />
        <WeightWidget />
      </div>

      {/* Coming-soon features */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-surface-500">
          Coming soon
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {COMING_SOON.map((item) => (
            <div
              key={item.label}
              className="rounded-xl border border-surface-200 bg-white p-5 opacity-60"
              aria-label={`${item.label} — coming soon`}
            >
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-surface-50 text-surface-400">
                {item.icon}
              </div>
              <h3 className="font-semibold text-surface-700">{item.label}</h3>
              <p className="mt-1 text-sm text-surface-400">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const COMING_SOON = [
  {
    label: "Workouts",
    description: "Log sets, reps, and track personal records.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m-7.5-7.5v15" />
      </svg>
    ),
  },
  {
    label: "Nutrition",
    description: "Track calories, macros, meals, and water.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-6-6h12" />
      </svg>
    ),
  },
  {
    label: "Habits",
    description: "Build consistent daily habits.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
  },
  {
    label: "Body measurements",
    description: "Log detailed body measurements over time.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M3 6h18M3 18h18" />
      </svg>
    ),
  },
  {
    label: "AI insights",
    description: "Weekly summaries and smart recommendations.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    label: "Sleep & wellness",
    description: "Log sleep, steps, and daily wellness check-ins.",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    ),
  },
];
