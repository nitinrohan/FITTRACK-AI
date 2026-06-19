'use client'

import { useState } from 'react'
import { useWellness } from '@/features/wellness/use-wellness'
import type {
  LogSleepRequest,
  LogStepsRequest,
  LogWellnessRequest,
  SleepLog,
  StepsLog,
  WellnessLog,
} from '@/types/wellness'
import {
  ENERGY_LABELS,
  MOOD_LABELS,
  STRESS_LABELS,
  formatDistanceKm,
  formatSleepDuration,
} from '@/types/wellness'

// ── Helpers ───────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function RatingDots({ value, max = 5 }: { value: number | null; max?: number }) {
  if (value === null) return <span className="text-gray-400 text-sm">-</span>
  return (
    <span className="flex gap-1">
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${i < value ? 'bg-indigo-500' : 'bg-gray-200'}`}
        />
      ))}
    </span>
  )
}

function RatingPicker({
  value,
  onChange,
  labels,
}: {
  value: number | null
  onChange: (v: number) => void
  labels: Record<number, string>
}) {
  return (
    <div className="flex gap-2 flex-wrap">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={`px-3 py-1 rounded-full text-sm border transition-colors ${
            value === n
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-700 border-gray-300 hover:border-indigo-400'
          }`}
        >
          {n} · {labels[n]}
        </button>
      ))}
    </div>
  )
}

// ── Today snapshot card ───────────────────────────────────────────────────────

function TodayCard({ snapshot }: { snapshot: ReturnType<typeof useWellness>['snapshot'] }) {
  if (!snapshot) return null

  const { sleep, steps, wellness, water_total_ml } = snapshot
  const waterL = (water_total_ml / 1000).toFixed(1)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h2 className="font-semibold text-gray-900 mb-4">Today at a glance</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">
            {formatSleepDuration(sleep?.duration_minutes ?? null)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Sleep</div>
          {sleep?.quality && <RatingDots value={sleep.quality} />}
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">
            {steps ? steps.steps.toLocaleString() : '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Steps</div>
          {steps?.distance_m && (
            <div className="text-xs text-gray-400">{formatDistanceKm(steps.distance_m)}</div>
          )}
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">
            {wellness?.mood ?? '—'}
          </div>
          <div className="text-xs text-gray-500 mt-1">Mood</div>
          {wellness?.mood && (
            <div className="text-xs text-gray-400">{MOOD_LABELS[wellness.mood]}</div>
          )}
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-indigo-600">{waterL}L</div>
          <div className="text-xs text-gray-500 mt-1">Water</div>
        </div>
      </div>
    </div>
  )
}

// ── Log sleep form ────────────────────────────────────────────────────────────

function LogSleepForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (p: LogSleepRequest) => Promise<void>
  onCancel: () => void
}) {
  const [date, setDate] = useState(today())
  const [mode, setMode] = useState<'duration' | 'times'>('duration')
  const [hours, setHours] = useState('')
  const [mins, setMins] = useState('')
  const [bedtime, setBedtime] = useState('')
  const [wakeTime, setWakeTime] = useState('')
  const [quality, setQuality] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const payload: LogSleepRequest = { date }
      if (mode === 'duration') {
        const h = parseInt(hours || '0', 10)
        const m = parseInt(mins || '0', 10)
        payload.duration_minutes = h * 60 + m
      } else {
        if (bedtime) payload.bedtime = `${date}T${bedtime}:00`
        if (wakeTime) {
          // wake time might be next day
          payload.wake_time = `${date}T${wakeTime}:00`
        }
      }
      if (quality) payload.quality = quality
      if (notes.trim()) payload.notes = notes.trim()
      await onSubmit(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode('duration')}
          className={`px-3 py-1 rounded-full text-sm border ${
            mode === 'duration'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'border-gray-300 text-gray-600'
          }`}
        >
          Duration
        </button>
        <button
          type="button"
          onClick={() => setMode('times')}
          className={`px-3 py-1 rounded-full text-sm border ${
            mode === 'times'
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'border-gray-300 text-gray-600'
          }`}
        >
          Bedtime & wake
        </button>
      </div>

      {mode === 'duration' ? (
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Hours</label>
            <input
              type="number"
              min={0}
              max={24}
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              placeholder="7"
              className="w-20 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Minutes</label>
            <input
              type="number"
              min={0}
              max={59}
              value={mins}
              onChange={(e) => setMins(e.target.value)}
              placeholder="30"
              className="w-20 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      ) : (
        <div className="flex gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Bedtime</label>
            <input
              type="time"
              value={bedtime}
              onChange={(e) => setBedtime(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Wake time</label>
            <input
              type="time"
              value={wakeTime}
              onChange={(e) => setWakeTime(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Sleep quality
        </label>
        <RatingPicker
          value={quality}
          onChange={setQuality}
          labels={{ 1: 'Very poor', 2: 'Poor', 3: 'Okay', 4: 'Good', 5: 'Excellent' }}
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Notes (optional)</label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. Felt restless"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Log sleep'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── Log steps form ────────────────────────────────────────────────────────────

function LogStepsForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (p: LogStepsRequest) => Promise<void>
  onCancel: () => void
}) {
  const [date, setDate] = useState(today())
  const [steps, setSteps] = useState('')
  const [activeMinutes, setActiveMinutes] = useState('')
  const [distanceKm, setDistanceKm] = useState('')
  const [caloriesBurned, setCaloriesBurned] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!steps) { setError('Step count is required'); return }
    setSaving(true)
    try {
      const payload: LogStepsRequest = {
        date,
        steps: parseInt(steps, 10),
      }
      if (activeMinutes) payload.active_minutes = parseInt(activeMinutes, 10)
      if (distanceKm) payload.distance_m = parseFloat(distanceKm) * 1000
      if (caloriesBurned) payload.calories_burned = parseFloat(caloriesBurned)
      if (notes.trim()) payload.notes = notes.trim()
      await onSubmit(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Date</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Steps *</label>
          <input
            type="number"
            min={0}
            value={steps}
            onChange={(e) => setSteps(e.target.value)}
            placeholder="8000"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Active minutes</label>
          <input
            type="number"
            min={0}
            value={activeMinutes}
            onChange={(e) => setActiveMinutes(e.target.value)}
            placeholder="45"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Distance (km)</label>
          <input
            type="number"
            min={0}
            step="0.1"
            value={distanceKm}
            onChange={(e) => setDistanceKm(e.target.value)}
            placeholder="6.4"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Calories burned</label>
          <input
            type="number"
            min={0}
            value={caloriesBurned}
            onChange={(e) => setCaloriesBurned(e.target.value)}
            placeholder="320"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Notes</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Log steps'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── Log wellness form ─────────────────────────────────────────────────────────

function LogWellnessForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (p: LogWellnessRequest) => Promise<void>
  onCancel: () => void
}) {
  const [date, setDate] = useState(today())
  const [mood, setMood] = useState<number | null>(null)
  const [energy, setEnergy] = useState<number | null>(null)
  const [stress, setStress] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!mood && !energy && !stress) {
      setError('Rate at least one of mood, energy, or stress.')
      return
    }
    setSaving(true)
    try {
      const payload: LogWellnessRequest = { date }
      if (mood) payload.mood = mood
      if (energy) payload.energy = energy
      if (stress) payload.stress = stress
      if (notes.trim()) payload.notes = notes.trim()
      await onSubmit(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Date</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Mood</label>
        <RatingPicker value={mood} onChange={setMood} labels={MOOD_LABELS} />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Energy</label>
        <RatingPicker value={energy} onChange={setEnergy} labels={ENERGY_LABELS} />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Stress{' '}
          <span className="text-xs font-normal text-gray-400">(1 = very calm)</span>
        </label>
        <RatingPicker value={stress} onChange={setStress} labels={STRESS_LABELS} />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Notes (optional)</label>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. Busy day at work"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Log wellness'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── Sleep tab ─────────────────────────────────────────────────────────────────

function SleepTab({
  logs,
  onLog,
  onDelete,
}: {
  logs: SleepLog[]
  onLog: (p: LogSleepRequest) => Promise<SleepLog>
  onDelete: (id: string) => Promise<void>
}) {
  const [showForm, setShowForm] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await onDelete(id) } finally { setDeletingId(null) }
  }

  return (
    <div className="space-y-4">
      {showForm ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-medium text-gray-900 mb-4">Log sleep</h3>
          <LogSleepForm
            onSubmit={async (p) => { await onLog(p); setShowForm(false) }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Log sleep
        </button>
      )}

      {logs.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          No sleep entries yet. Log your first sleep above.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {logs.map((entry) => (
            <div key={entry.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <div className="font-medium text-sm text-gray-900">{entry.date}</div>
                <div className="text-sm text-gray-500">
                  {formatSleepDuration(entry.duration_minutes)}
                  {entry.quality && (
                    <span className="ml-2">· Quality: {entry.quality}/5</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(entry.id)}
                disabled={deletingId === entry.id}
                className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                {deletingId === entry.id ? '…' : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Steps tab ─────────────────────────────────────────────────────────────────

function StepsTab({
  logs,
  onLog,
  onDelete,
}: {
  logs: StepsLog[]
  onLog: (p: LogStepsRequest) => Promise<StepsLog>
  onDelete: (id: string) => Promise<void>
}) {
  const [showForm, setShowForm] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await onDelete(id) } finally { setDeletingId(null) }
  }

  return (
    <div className="space-y-4">
      {showForm ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-medium text-gray-900 mb-4">Log steps</h3>
          <LogStepsForm
            onSubmit={async (p) => { await onLog(p); setShowForm(false) }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Log steps
        </button>
      )}

      {logs.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          No step entries yet. Log your first day above.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {logs.map((entry) => (
            <div key={entry.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <div className="font-medium text-sm text-gray-900">{entry.date}</div>
                <div className="text-sm text-gray-500">
                  {entry.steps.toLocaleString()} steps
                  {entry.distance_m && (
                    <span className="ml-2">· {formatDistanceKm(entry.distance_m)}</span>
                  )}
                  {entry.active_minutes && (
                    <span className="ml-2">· {entry.active_minutes} active min</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(entry.id)}
                disabled={deletingId === entry.id}
                className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                {deletingId === entry.id ? '…' : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Wellness tab ──────────────────────────────────────────────────────────────

function WellnessTab({
  logs,
  onLog,
  onDelete,
}: {
  logs: WellnessLog[]
  onLog: (p: LogWellnessRequest) => Promise<WellnessLog>
  onDelete: (id: string) => Promise<void>
}) {
  const [showForm, setShowForm] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await onDelete(id) } finally { setDeletingId(null) }
  }

  return (
    <div className="space-y-4">
      {showForm ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-medium text-gray-900 mb-4">Log wellness check-in</h3>
          <LogWellnessForm
            onSubmit={async (p) => { await onLog(p); setShowForm(false) }}
            onCancel={() => setShowForm(false)}
          />
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Log wellness
        </button>
      )}

      {logs.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          No wellness entries yet. Log your first check-in above.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {logs.map((entry) => (
            <div key={entry.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <div className="font-medium text-sm text-gray-900">{entry.date}</div>
                <div className="flex gap-4 mt-1">
                  {entry.mood && (
                    <span className="text-xs text-gray-500">
                      Mood <RatingDots value={entry.mood} />
                      <span className="ml-1">{MOOD_LABELS[entry.mood]}</span>
                    </span>
                  )}
                  {entry.energy && (
                    <span className="text-xs text-gray-500">
                      Energy <RatingDots value={entry.energy} />
                    </span>
                  )}
                  {entry.stress && (
                    <span className="text-xs text-gray-500">
                      Stress {entry.stress}/5
                    </span>
                  )}
                </div>
                {entry.notes && (
                  <div className="text-xs text-gray-400 mt-0.5">{entry.notes}</div>
                )}
              </div>
              <button
                onClick={() => handleDelete(entry.id)}
                disabled={deletingId === entry.id}
                className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
              >
                {deletingId === entry.id ? '…' : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = 'today' | 'sleep' | 'steps' | 'wellness'

export default function WellnessPage() {
  const [activeTab, setActiveTab] = useState<Tab>('today')
  const {
    sleepLogs,
    stepsLogs,
    wellnessLogs,
    snapshot,
    isLoading,
    error,
    logSleep,
    deleteSleep,
    logSteps,
    deleteSteps,
    logWellness,
    deleteWellness,
  } = useWellness()

  const tabs: { key: Tab; label: string }[] = [
    { key: 'today', label: 'Today' },
    { key: 'sleep', label: 'Sleep' },
    { key: 'steps', label: 'Steps' },
    { key: 'wellness', label: 'Wellness' },
  ]

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Wellness</h1>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === t.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="text-gray-400 text-sm py-8 text-center">Loading…</div>
      ) : (
        <>
          {activeTab === 'today' && <TodayCard snapshot={snapshot} />}

          {activeTab === 'sleep' && (
            <SleepTab logs={sleepLogs} onLog={logSleep} onDelete={deleteSleep} />
          )}

          {activeTab === 'steps' && (
            <StepsTab logs={stepsLogs} onLog={logSteps} onDelete={deleteSteps} />
          )}

          {activeTab === 'wellness' && (
            <WellnessTab
              logs={wellnessLogs}
              onLog={logWellness}
              onDelete={deleteWellness}
            />
          )}
        </>
      )}
    </div>
  )
}
