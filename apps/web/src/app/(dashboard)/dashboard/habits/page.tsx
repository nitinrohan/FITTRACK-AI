'use client'

/**
 * Habits page — create habits, check them off for today, and track streaks.
 *
 * Tone: encouraging and non-judgemental. Streaks are shown as positive
 * progress, never as pressure; missing a day does not shame the user.
 */

import { useId, useState } from 'react'
import { useHabits } from '@/features/habits/use-habits'
import type { CreateHabitRequest, Habit } from '@/types/habits'

// ── Accent palette (on-brand, subtle) ───────────────────────────────────────────

const COLORS: { label: string; value: string }[] = [
  { label: 'Green', value: '#22c55e' },
  { label: 'Sky', value: '#0ea5e9' },
  { label: 'Amber', value: '#f59e0b' },
  { label: 'Rose', value: '#f43f5e' },
  { label: 'Violet', value: '#8b5cf6' },
]

const DEFAULT_COLOR = '#22c55e'

// ── Page ─────────────────────────────────────────────────────────────────────

export default function HabitsPage() {
  const [showArchived, setShowArchived] = useState(false)
  const {
    habits,
    isLoading,
    error,
    refresh,
    createHabit,
    updateHabit,
    removeHabit,
    setArchived,
    toggleToday,
  } = useHabits(showArchived)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Habit | null>(null)

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(habit: Habit) {
    setEditing(habit)
    setFormOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50">Habits</h1>
          <p className="mt-0.5 text-sm text-surface-500 dark:text-surface-400">
            Build small daily habits and watch your streaks grow.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
        >
          <span aria-hidden="true" className="text-base leading-none">
            +
          </span>
          New habit
        </button>
      </div>

      {/* Active / archived toggle */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-pressed={!showArchived}
          onClick={() => setShowArchived(false)}
          className={toggleClass(!showArchived)}
        >
          Active
        </button>
        <button
          type="button"
          aria-pressed={showArchived}
          onClick={() => setShowArchived(true)}
          className={toggleClass(showArchived)}
        >
          Archived
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={() => refresh()}
            className="shrink-0 rounded-lg border border-red-300 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div role="status" className="py-16 text-center text-sm text-surface-500 dark:text-surface-400">
          Loading habits…
        </div>
      ) : habits.length === 0 ? (
        <EmptyState archived={showArchived} onCreate={openCreate} />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {habits.map((habit) => (
            <li key={habit.id}>
              <HabitCard
                habit={habit}
                onToggle={() => toggleToday(habit)}
                onEdit={() => openEdit(habit)}
                onArchive={() => setArchived(habit.id, !habit.is_archived)}
                onDelete={async () => {
                  if (
                    window.confirm(
                      `Delete "${habit.name}"? This also removes its history and can't be undone.`,
                    )
                  ) {
                    await removeHabit(habit.id)
                  }
                }}
              />
            </li>
          ))}
        </ul>
      )}

      {formOpen && (
        <HabitFormModal
          habit={editing}
          onClose={() => setFormOpen(false)}
          onSubmit={async (payload) => {
            if (editing) {
              await updateHabit(editing.id, payload)
            } else {
              await createHabit(payload)
            }
            setFormOpen(false)
          }}
        />
      )}
    </div>
  )
}

function toggleClass(active: boolean): string {
  return [
    'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500',
    active
      ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300'
      : 'text-surface-500 hover:text-surface-700 dark:text-surface-400 dark:hover:text-surface-200',
  ].join(' ')
}

// ── Habit card ───────────────────────────────────────────────────────────────

function HabitCard({
  habit,
  onToggle,
  onEdit,
  onArchive,
  onDelete,
}: {
  habit: Habit
  onToggle: () => Promise<void>
  onEdit: () => void
  onArchive: () => Promise<void>
  onDelete: () => Promise<void>
}) {
  const [busy, setBusy] = useState(false)
  const accent = habit.color ?? DEFAULT_COLOR
  const pct = Math.min(
    100,
    Math.round((habit.completions_this_week / Math.max(1, habit.target_days_per_week)) * 100),
  )

  async function handleToggle() {
    setBusy(true)
    try {
      await onToggle()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col gap-3 rounded-xl border border-surface-200 bg-white p-4 dark:border-surface-700 dark:bg-surface-800">
      <div className="flex items-start gap-3">
        {!habit.is_archived && (
          <button
            type="button"
            onClick={handleToggle}
            disabled={busy}
            aria-pressed={habit.completed_today}
            aria-label={
              habit.completed_today
                ? `Mark "${habit.name}" not done for today`
                : `Mark "${habit.name}" done for today`
            }
            className={[
              'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 transition-colors disabled:opacity-50',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500',
              habit.completed_today
                ? 'border-brand-500 bg-brand-500 text-white'
                : 'border-surface-300 text-transparent hover:border-brand-400 dark:border-surface-600',
            ].join(' ')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} className="h-4 w-4" aria-hidden="true">
              <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden="true" />
            <h2 className="truncate font-semibold text-surface-900 dark:text-surface-50">{habit.name}</h2>
          </div>
          {habit.description && (
            <p className="mt-0.5 line-clamp-2 text-xs text-surface-500 dark:text-surface-400">
              {habit.description}
            </p>
          )}
        </div>
      </div>

      {/* Streak + week progress */}
      <div className="mt-auto space-y-2">
        <div className="flex items-center justify-between text-xs text-surface-500 dark:text-surface-400">
          <span>
            <span className="font-semibold text-surface-900 dark:text-surface-50">
              {habit.current_streak}
            </span>{' '}
            day{habit.current_streak === 1 ? '' : 's'} streak
          </span>
          <span>
            {habit.completions_this_week}/{habit.target_days_per_week} this week
          </span>
        </div>
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-surface-100 dark:bg-surface-700"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${habit.name}: ${pct}% of weekly target`}
        >
          <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
        </div>
        {habit.longest_streak > 0 && (
          <p className="text-[11px] text-surface-400 dark:text-surface-500">
            Best streak: {habit.longest_streak} day{habit.longest_streak === 1 ? '' : 's'}
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 border-t border-surface-100 pt-2 text-xs dark:border-surface-700">
        <button
          type="button"
          onClick={onEdit}
          className="rounded text-surface-500 hover:text-surface-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-400 dark:hover:text-surface-100"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onArchive()}
          className="rounded text-surface-500 hover:text-surface-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:text-surface-400 dark:hover:text-surface-100"
        >
          {habit.is_archived ? 'Unarchive' : 'Archive'}
        </button>
        <button
          type="button"
          onClick={() => onDelete()}
          className="ml-auto rounded text-red-600 hover:text-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 dark:text-red-400"
        >
          Delete
        </button>
      </div>
    </div>
  )
}

// ── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ archived, onCreate }: { archived: boolean; onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-surface-300 py-16 text-center dark:border-surface-700">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 dark:bg-brand-950">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6 text-brand-600 dark:text-brand-400" aria-hidden="true">
          <path d="M9 11l3 3L22 4" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <p className="mt-3 font-semibold text-surface-900 dark:text-surface-50">
        {archived ? 'No archived habits' : 'No habits yet'}
      </p>
      <p className="mt-1 max-w-xs text-sm text-surface-500 dark:text-surface-400">
        {archived
          ? 'Habits you archive will appear here, with their history kept.'
          : 'Start with one small thing you want to do regularly.'}
      </p>
      {!archived && (
        <button
          type="button"
          onClick={onCreate}
          className="mt-4 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
        >
          Create your first habit
        </button>
      )}
    </div>
  )
}

// ── Create / edit modal ──────────────────────────────────────────────────────

function HabitFormModal({
  habit,
  onClose,
  onSubmit,
}: {
  habit: Habit | null
  onClose: () => void
  onSubmit: (payload: CreateHabitRequest) => Promise<void>
}) {
  const fid = useId()
  const [name, setName] = useState(habit?.name ?? '')
  const [target, setTarget] = useState(habit?.target_days_per_week ?? 7)
  const [description, setDescription] = useState(habit?.description ?? '')
  const [color, setColor] = useState(habit?.color ?? DEFAULT_COLOR)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim()) {
      setError('Please give your habit a name.')
      return
    }
    setSaving(true)
    try {
      const payload: CreateHabitRequest = {
        name: name.trim(),
        target_days_per_week: target,
        color,
      }
      if (description.trim()) payload.description = description.trim()
      await onSubmit(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save habit')
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-surface-900/40 p-0 dark:bg-black/60 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${fid}-title`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-full max-w-md rounded-t-2xl bg-white p-5 shadow-xl dark:bg-surface-800 sm:rounded-2xl">
        <h2 id={`${fid}-title`} className="text-lg font-semibold text-surface-900 dark:text-surface-50">
          {habit ? 'Edit habit' : 'New habit'}
        </h2>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor={`${fid}-name`} className="block text-sm font-medium text-surface-700 dark:text-surface-200">
              Name
            </label>
            <input
              id={`${fid}-name`}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              aria-required="true"
              maxLength={100}
              placeholder="e.g. Drink 2L of water"
              className="mt-1 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
            />
          </div>

          <div>
            <label htmlFor={`${fid}-target`} className="block text-sm font-medium text-surface-700 dark:text-surface-200">
              Target days per week
            </label>
            <select
              id={`${fid}-target`}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
            >
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>
                  {n} {n === 1 ? 'day' : 'days'} / week
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="block text-sm font-medium text-surface-700 dark:text-surface-200">Colour</span>
            <div className="mt-1.5 flex flex-wrap gap-2" role="group" aria-label="Habit colour">
              {COLORS.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  aria-pressed={color === c.value}
                  aria-label={c.label}
                  onClick={() => setColor(c.value)}
                  className={[
                    'h-7 w-7 rounded-full transition-transform focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500',
                    color === c.value ? 'ring-2 ring-surface-900 ring-offset-2 dark:ring-surface-100 dark:ring-offset-surface-800' : '',
                  ].join(' ')}
                  style={{ backgroundColor: c.value }}
                />
              ))}
            </div>
          </div>

          <div>
            <label htmlFor={`${fid}-desc`} className="block text-sm font-medium text-surface-700 dark:text-surface-200">
              Notes <span className="font-normal text-surface-400">(optional)</span>
            </label>
            <input
              id={`${fid}-desc`}
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              placeholder="Why does this habit matter to you?"
              className="mt-1 w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-900 placeholder:text-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-50"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
            >
              {saving ? 'Saving…' : habit ? 'Save changes' : 'Create habit'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-surface-300 px-4 py-2 text-sm text-surface-700 hover:bg-surface-50 dark:border-surface-600 dark:text-surface-200 dark:hover:bg-surface-700"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
