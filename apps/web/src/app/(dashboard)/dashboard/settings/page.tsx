"use client";

/**
 * /dashboard/settings - Privacy & account controls (Phase 14).
 *
 * Sections:
 *   - Your data: per-category record counts (loading / empty / error states)
 *   - Export: download a complete JSON copy of your data
 *   - AI features: opt in / out of sending data to an AI model
 *   - Danger zone: permanently delete the account (password + typed confirmation)
 *
 * All actions are the caller's own; the backend enforces ownership and
 * re-verifies the password before deletion.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog } from "@/components/ui/dialog";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useAuth } from "@/features/auth/use-auth";
import { usePrivacySummary } from "@/features/privacy/use-privacy-summary";
import { privacyApi } from "@/lib/privacy-api";
import { usersApi } from "@/lib/users-api";
import { ApiError } from "@/lib/api-client";
import { SUMMARY_LABELS } from "@/types/privacy";

const DELETE_CONFIRM_PHRASE = "DELETE";

/** A labelled on/off control for a single boolean preference. */
function ToggleRow({
  title,
  description,
  enabled,
  isSaving,
  onToggle,
}: {
  title: string;
  description: string;
  enabled: boolean;
  isSaving: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-surface-200 px-4 py-3">
      <div>
        <p className="text-sm font-medium text-surface-900">{title}</p>
        <p className="text-xs text-surface-500">{description}</p>
      </div>
      <Button
        variant={enabled ? "secondary" : "primary"}
        size="sm"
        onClick={onToggle}
        isLoading={isSaving}
        aria-pressed={enabled}
      >
        {enabled ? "Turn off" : "Turn on"}
      </Button>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout, refreshUser } = useAuth();
  const { summary, isLoading, error, reload } = usePrivacySummary();

  // ── Export state ──────────────────────────────────────────────────────────
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportedAt, setExportedAt] = useState<string | null>(null);

  // ── Preference toggles (AI + notifications) ───────────────────────────────
  const aiEnabled = user?.preferences?.ai_features_enabled ?? false;
  const [isSavingAi, setIsSavingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const emailEnabled = user?.preferences?.email_notifications_enabled ?? false;
  const [isSavingEmail, setIsSavingEmail] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);

  // ── Delete state ──────────────────────────────────────────────────────────
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const totalRecords =
    summary != null ? Object.values(summary).reduce((a, b) => a + b, 0) : 0;

  async function handleExport() {
    setIsExporting(true);
    setExportError(null);
    try {
      const data = await privacyApi.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const stamp = new Date().toISOString().split("T")[0];
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `fittrack-export-${stamp}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportedAt(new Date().toLocaleString());
    } catch (err) {
      setExportError(
        err instanceof Error ? err.message : "Could not generate your export. Please try again."
      );
    } finally {
      setIsExporting(false);
    }
  }

  async function handleToggleAi() {
    setIsSavingAi(true);
    setAiError(null);
    try {
      await usersApi.updatePreferences({ ai_features_enabled: !aiEnabled });
      await refreshUser();
    } catch (err) {
      setAiError(
        err instanceof Error ? err.message : "Could not update this setting. Please try again."
      );
    } finally {
      setIsSavingAi(false);
    }
  }

  async function handleToggleEmail() {
    setIsSavingEmail(true);
    setEmailError(null);
    try {
      await usersApi.updatePreferences({ email_notifications_enabled: !emailEnabled });
      await refreshUser();
    } catch (err) {
      setEmailError(
        err instanceof Error ? err.message : "Could not update this setting. Please try again."
      );
    } finally {
      setIsSavingEmail(false);
    }
  }

  function closeDelete() {
    setShowDelete(false);
    setPassword("");
    setConfirmPhrase("");
    setDeleteError(null);
  }

  async function handleDelete() {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await privacyApi.deleteAccount(password);
      await logout();
      router.push("/auth/login");
    } catch (err) {
      if (err instanceof ApiError && err.isUnauthorized) {
        setDeleteError("Password is incorrect.");
      } else {
        setDeleteError(
          err instanceof Error ? err.message : "Could not delete your account. Please try again."
        );
      }
      setIsDeleting(false);
    }
  }

  const canDelete =
    password.length > 0 && confirmPhrase.trim() === DELETE_CONFIRM_PHRASE && !isDeleting;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 py-2">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-surface-900">Settings &amp; privacy</h1>
        <p className="text-sm text-surface-500">
          Review what FitTrack stores about you, download a copy, control AI features, or delete
          your account.
        </p>
      </header>

      {/* ── Your data ─────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Your data</CardTitle>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="flex items-center gap-3 py-6 text-sm text-surface-500">
              <LoadingSpinner />
              <span>Loading your data summary…</span>
            </div>
          ) : error ? (
            <div role="alert" className="space-y-3 py-2">
              <p className="text-sm text-red-600">{error}</p>
              <Button variant="secondary" size="sm" onClick={() => void reload()}>
                Retry
              </Button>
            </div>
          ) : summary && totalRecords === 0 ? (
            <p className="py-2 text-sm text-surface-500">
              You haven&apos;t logged any data yet. Once you start tracking, your records will be
              summarised here.
            </p>
          ) : summary ? (
            <>
              <p className="mb-3 text-sm text-surface-600">
                FitTrack currently stores{" "}
                <span className="font-semibold text-surface-900">{totalRecords}</span> records you
                own, across these categories:
              </p>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
                {SUMMARY_LABELS.map(({ key, label }) => (
                  <div key={key} className="flex items-baseline justify-between gap-2">
                    <dt className="text-sm text-surface-600">{label}</dt>
                    <dd className="text-sm font-medium tabular-nums text-surface-900">
                      {summary[key]}
                    </dd>
                  </div>
                ))}
              </dl>
            </>
          ) : null}
        </CardBody>
      </Card>

      {/* ── Export ────────────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Export your data</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-surface-600">
            Download a complete copy of your FitTrack data as a JSON file. It includes your
            profile, goals, workouts, nutrition, measurements, wellness and habit records.
          </p>
          {exportError && (
            <p role="alert" className="text-sm text-red-600">
              {exportError}
            </p>
          )}
          {exportedAt && !exportError && (
            <p role="status" className="text-sm text-brand-600">
              Export downloaded at {exportedAt}.
            </p>
          )}
          <Button onClick={() => void handleExport()} isLoading={isExporting}>
            {isExporting ? "Preparing export…" : "Download my data (JSON)"}
          </Button>
        </CardBody>
      </Card>

      {/* ── AI features ───────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>AI features</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-surface-600">
            When enabled, FitTrack may send your fitness data to an AI model to generate summaries
            and suggestions. All calculations stay in the app, and AI never changes your data
            without your approval. The tracker works fully whether this is on or off.
          </p>
          {aiError && (
            <p role="alert" className="text-sm text-red-600">
              {aiError}
            </p>
          )}
          <ToggleRow
            title={`AI features are ${aiEnabled ? "on" : "off"}`}
            description={
              aiEnabled
                ? "Your data may be sent to an AI model for summaries and suggestions."
                : "No data is sent to any AI model."
            }
            enabled={aiEnabled}
            isSaving={isSavingAi}
            onToggle={() => void handleToggleAi()}
          />
        </CardBody>
      </Card>

      {/* ── Notifications ─────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-surface-600">
            Choose whether FitTrack may email you (for example, weekly summaries). This does not
            affect security-related messages such as password resets.
          </p>
          {emailError && (
            <p role="alert" className="text-sm text-red-600">
              {emailError}
            </p>
          )}
          <ToggleRow
            title={`Email notifications are ${emailEnabled ? "on" : "off"}`}
            description={
              emailEnabled
                ? "FitTrack may send you product and summary emails."
                : "FitTrack will not send you product or summary emails."
            }
            enabled={emailEnabled}
            isSaving={isSavingEmail}
            onToggle={() => void handleToggleEmail()}
          />
        </CardBody>
      </Card>

      {/* ── Danger zone ───────────────────────────────────────────────────── */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-700">Delete account</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-surface-600">
            Permanently delete your account and all {totalRecords > 0 ? totalRecords : ""} of your
            records. This cannot be undone. We recommend exporting your data first.
          </p>
          <p className="text-xs text-surface-500">
            Want to remove just some entries instead? You can delete individual records from each
            tracking page (weight, workouts, nutrition, and so on).
          </p>
          <Button variant="destructive" onClick={() => setShowDelete(true)}>
            Delete my account…
          </Button>
        </CardBody>
      </Card>

      <Dialog
        open={showDelete}
        onClose={closeDelete}
        title="Delete your account?"
        description="This permanently removes your account and every record you own. This action cannot be undone."
      >
        <div className="space-y-4">
          <Input
            label="Confirm your password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Input
            label={`Type ${DELETE_CONFIRM_PHRASE} to confirm`}
            value={confirmPhrase}
            onChange={(e) => setConfirmPhrase(e.target.value)}
            hint="This extra step prevents accidental deletion."
          />
          {deleteError && (
            <p role="alert" className="text-sm text-red-600">
              {deleteError}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={closeDelete} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleDelete()}
              isLoading={isDeleting}
              disabled={!canDelete}
            >
              Permanently delete
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
