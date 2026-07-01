"use client";

/**
 * /dashboard/mind - Stress & Mindfulness.
 *
 * Two sections on one page:
 *   - Stress: today's gauge (average + Low/Moderate/High band), highest /
 *     lowest / average, a 0-100 "Log stress" slider, and recent readings.
 *   - Mindfulness: today's minutes + streak, a curated session library, and
 *     recent mindful-minute logs.
 *
 * Stress is self-reported and is presented supportively - never as a medical
 * assessment. All actions reload the page's data on success.
 */

import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useAuth } from "@/features/auth/use-auth";
import { useMind } from "@/features/mind/use-mind";
import { stressApi, mindfulnessApi } from "@/lib/mind-api";
import { STRESS_BAND_META, type StressBand } from "@/types/mind";

function bandFor(level: number): StressBand {
  if (level <= 33) return "low";
  if (level <= 66) return "moderate";
  return "high";
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function MindPage() {
  const { user } = useAuth();
  const { data, isLoading, error, reload } = useMind(user?.preferences?.timezone);

  const [level, setLevel] = useState(40);
  const [isLoggingStress, setIsLoggingStress] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>, id?: string) {
    setActionError(null);
    if (id) setBusyId(id);
    try {
      await fn();
      await reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusyId(null);
    }
  }

  async function logStress() {
    setIsLoggingStress(true);
    try {
      await stressApi.log({ level });
      await reload();
      setActionError(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not log your stress. Please try again.");
    } finally {
      setIsLoggingStress(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <LoadingSpinner size="lg" label="Loading your wellbeing data…" />
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-3xl space-y-3 py-10 text-center">
        <p className="text-sm text-red-600">{error}</p>
        <Button variant="secondary" onClick={() => void reload()}>
          Retry
        </Button>
      </div>
    );
  }

  const s = data?.stressSummary ?? null;
  const m = data?.mindSummary ?? null;
  const previewBand = bandFor(level);

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8 py-2">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-surface-900">Mind</h1>
        <p className="text-sm text-surface-500">
          Track how you&apos;re feeling and take a moment for yourself. These figures are
          self-reported and are not a medical assessment.
        </p>
      </header>

      {actionError && (
        <p role="alert" className="text-sm text-red-600">
          {actionError}
        </p>
      )}

      {/* ── Stress ────────────────────────────────────────────────────────── */}
      <section className="space-y-4" aria-labelledby="stress-heading">
        <h2 id="stress-heading" className="text-lg font-semibold text-surface-900">
          Stress
        </h2>

        <Card>
          <CardHeader>
            <CardTitle>Today</CardTitle>
          </CardHeader>
          <CardBody>
            {s && s.count > 0 && s.average !== null && s.band ? (
              <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
                <StressGauge level={s.average} band={s.band} />
                <div className="grid flex-1 grid-cols-3 gap-3 text-center">
                  <Stat label="Highest" value={s.highest} color="text-red-600" />
                  <Stat label="Lowest" value={s.lowest} color="text-brand-600" />
                  <Stat label="Average" value={s.average} color="text-surface-900" />
                  <div className="col-span-3 text-xs text-surface-500">
                    {s.count} reading{s.count === 1 ? "" : "s"} today
                  </div>
                </div>
              </div>
            ) : (
              <p className="py-2 text-sm text-surface-500">
                No stress readings yet today. Log one below to see your daily range.
              </p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Log your stress</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <label htmlFor="stress-level" className="block text-sm font-medium text-surface-700">
                How stressed do you feel right now?
              </label>
              <input
                id="stress-level"
                type="range"
                min={0}
                max={100}
                step={1}
                value={level}
                onChange={(e) => setLevel(Number(e.target.value))}
                aria-describedby="stress-level-value"
                className="mt-3 w-full accent-brand-500"
              />
              <div
                id="stress-level-value"
                className="mt-1 flex items-center justify-between text-sm"
              >
                <span className="text-surface-500">Calm</span>
                <span className="font-semibold text-surface-900">
                  {level} -{" "}
                  <span className={STRESS_BAND_META[previewBand].color}>
                    {STRESS_BAND_META[previewBand].label}
                  </span>
                </span>
                <span className="text-surface-500">High</span>
              </div>
            </div>
            {previewBand === "high" && (
              <p className="rounded-lg bg-surface-50 px-3 py-2 text-xs text-surface-600">
                That sounds like a lot right now. A short breathing session below might help - and if
                stress feels persistent or overwhelming, consider reaching out to someone you trust
                or a professional.
              </p>
            )}
            <Button onClick={() => void logStress()} isLoading={isLoggingStress}>
              Log stress
            </Button>
          </CardBody>
        </Card>

        {data && data.stressLogs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Recent readings</CardTitle>
            </CardHeader>
            <CardBody>
              <ul className="divide-y divide-surface-100">
                {data.stressLogs.map((logItem) => (
                  <li key={logItem.id} className="flex items-center justify-between gap-3 py-2">
                    <div className="flex items-center gap-3">
                      <span className={`text-sm font-semibold ${STRESS_BAND_META[logItem.band].color}`}>
                        {logItem.level}
                      </span>
                      <span className="text-xs text-surface-500">
                        {STRESS_BAND_META[logItem.band].label} · {formatTime(logItem.recorded_at)}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      isLoading={busyId === logItem.id}
                      onClick={() => void run(() => stressApi.remove(logItem.id), logItem.id)}
                      aria-label={`Delete reading of ${logItem.level}`}
                    >
                      Delete
                    </Button>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        )}
      </section>

      {/* ── Mindfulness ───────────────────────────────────────────────────── */}
      <section className="space-y-4" aria-labelledby="mind-heading">
        <h2 id="mind-heading" className="text-lg font-semibold text-surface-900">
          Mindfulness
        </h2>

        <Card>
          <CardHeader>
            <CardTitle>Today</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-3 gap-3 text-center">
              <Stat label="Minutes" value={m?.total_minutes ?? 0} color="text-brand-600" />
              <Stat label="Sessions" value={m?.sessions_count ?? 0} color="text-surface-900" />
              <Stat label="Day streak" value={m?.current_streak ?? 0} color="text-surface-900" />
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sessions</CardTitle>
          </CardHeader>
          <CardBody>
            {data && data.sessions.length > 0 ? (
              <ul className="grid gap-3 sm:grid-cols-2">
                {data.sessions.map((session) => (
                  <li
                    key={session.id}
                    className="flex flex-col gap-2 rounded-lg border border-surface-200 p-4"
                  >
                    <div>
                      <p className="text-sm font-medium text-surface-900">{session.title}</p>
                      <p className="text-xs capitalize text-surface-500">
                        {session.category} · {session.duration_minutes} min
                      </p>
                    </div>
                    {session.description && (
                      <p className="text-xs text-surface-600">{session.description}</p>
                    )}
                    <div className="mt-auto flex items-center gap-2 pt-1">
                      <Button
                        size="sm"
                        isLoading={busyId === session.id}
                        onClick={() =>
                          void run(
                            () =>
                              mindfulnessApi.log({
                                duration_minutes: session.duration_minutes,
                                session_id: session.id,
                              }),
                            session.id
                          )
                        }
                      >
                        Log {session.duration_minutes} min
                      </Button>
                      {session.external_url ? (
                        <a
                          href={session.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs font-medium text-brand-600 underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
                        >
                          Open track
                        </a>
                      ) : (
                        <span className="text-xs text-surface-400">Link coming soon</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-2 text-sm text-surface-500">No sessions available yet.</p>
            )}
          </CardBody>
        </Card>

        {data && data.mindLogs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Recent sessions</CardTitle>
            </CardHeader>
            <CardBody>
              <ul className="divide-y divide-surface-100">
                {data.mindLogs.map((logItem) => (
                  <li key={logItem.id} className="flex items-center justify-between gap-3 py-2">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-brand-600">
                        {logItem.duration_minutes} min
                      </span>
                      <span className="text-xs text-surface-500">
                        {logItem.session_title ?? "Mindful minutes"} · {formatTime(logItem.recorded_at)}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      isLoading={busyId === logItem.id}
                      onClick={() => void run(() => mindfulnessApi.removeLog(logItem.id), logItem.id)}
                      aria-label={`Delete ${logItem.duration_minutes} minute log`}
                    >
                      Delete
                    </Button>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        )}
      </section>
    </div>
  );
}

// ── Small presentational helpers ──────────────────────────────────────────────

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number | null;
  color: string;
}) {
  return (
    <div>
      <p className={`text-2xl font-semibold tabular-nums ${color}`}>{value ?? "-"}</p>
      <p className="text-xs text-surface-500">{label}</p>
    </div>
  );
}

/** A semicircular gauge for the day's average stress. SVG is decorative; the
 * value and band are also announced via the aria-label and shown as text. */
function StressGauge({ level, band }: { level: number; band: StressBand }) {
  const meta = STRESS_BAND_META[band];
  const radius = 52;
  const circumference = Math.PI * radius; // semicircle
  const progress = Math.min(100, Math.max(0, level)) / 100;
  const dash = circumference * progress;
  const strokeColor =
    band === "low" ? "#16a34a" : band === "moderate" ? "#d97706" : "#dc2626";

  return (
    <div
      className="flex flex-col items-center"
      role="img"
      aria-label={`Average stress today ${level} out of 100, ${meta.label}`}
    >
      <svg viewBox="0 0 120 70" className="h-[70px] w-[120px]" aria-hidden="true">
        <path
          d="M 8 64 A 52 52 0 0 1 112 64"
          fill="none"
          stroke="currentColor"
          className="text-surface-200"
          strokeWidth={10}
          strokeLinecap="round"
        />
        <path
          d="M 8 64 A 52 52 0 0 1 112 64"
          fill="none"
          stroke={strokeColor}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
      </svg>
      <div className="-mt-2 text-center">
        <p className="text-2xl font-semibold tabular-nums text-surface-900">{level}</p>
        <p className={`text-xs font-medium ${meta.color}`}>{meta.label}</p>
      </div>
    </div>
  );
}
