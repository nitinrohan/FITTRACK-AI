# FitTrack AI - Privacy, Export & Account Deletion

This document describes how FitTrack handles a user's personal data: what is
stored, how a user reviews and exports it, how AI access is controlled, and how
records and whole accounts are deleted. It reflects the Phase 14 implementation.

FitTrack is not a medical, legal, or regulatory-compliance product. This document
describes the controls that are actually implemented; it does not claim formal
compliance with any specific regulation.

---

## Principles

- Fitness, nutrition, body-measurement, wellness, and progress data are treated
  as sensitive.
- Every user-owned record carries explicit ownership (`user_id`); data isolation
  is enforced in the backend, never by frontend filtering alone.
- A user can see what is stored, take a full copy with them, and delete records
  or their entire account.
- AI is opt-in. The core tracker works fully whether or not AI is enabled.

---

## What is stored

FitTrack stores, per user: the account record (email, role, status), the profile
(display name, optional physical and demographic fields), preferences (units,
time zone, language, notification and AI opt-ins), and the tracked domains -
goals, weight entries, body measurements, custom exercises, workout templates and
logged workouts (with their exercises and sets), custom foods, food logs, water
logs, sleep logs, daily steps, wellness check-ins, and habits (with completions).
AI usage metadata (provider, model, prompt version, timestamp, token/cost
estimates, accept/reject) is stored when AI features are used.

Passwords are stored only as a bcrypt hash and are never logged or returned by any
endpoint, including the data export.

---

## Reviewing your data

The settings page (`/dashboard/settings`) shows a per-category count of the
records the signed-in user owns, backed by:

```
GET /api/v1/privacy/summary  ->  PrivacySummary (counts per category)
```

This lets a user see exactly what an export or an account deletion will cover
before acting.

---

## Exporting your data

```
GET /api/v1/privacy/export  ->  application/json
```

Returns a complete, machine-readable snapshot of every record the caller owns,
grouped by domain. Workouts, workout templates, and habits nest their child rows
(sets, template exercises, completions) so relationships are preserved.

- Serialization is generic: each row is converted via SQLAlchemy column
  introspection, so new columns are included automatically as the schema grows.
- UUIDs and dates/datetimes are emitted as strings (ISO 8601 for dates).
- The password hash is always excluded.
- `export_metadata.format_version` identifies the structure (currently `1.0`).

The frontend downloads this payload as a `fittrack-export-<date>.json` file
entirely client-side (no third party involved).

### Export shape (abridged)

```json
{
  "export_metadata": { "format_version": "1.0", "generated_at": "...", "user_id": "...", "email": "..." },
  "account": { "id": "...", "email": "...", "role": "user", "is_active": true, "is_verified": false },
  "profile": { ... },
  "preferences": { ... },
  "goals": [ ... ],
  "weight_entries": [ ... ],
  "body_measurements": [ ... ],
  "custom_exercises": [ ... ],
  "workout_templates": [ { ..., "exercises": [ ... ] } ],
  "workouts": [ { ..., "exercises": [ { ..., "sets": [ ... ] } ] } ],
  "custom_foods": [ ... ],
  "food_logs": [ ... ],
  "water_logs": [ ... ],
  "sleep_logs": [ ... ],
  "daily_steps": [ ... ],
  "wellness_logs": [ ... ],
  "habits": [ { ..., "completions": [ ... ] } ],
  "ai_usage_logs": [ ... ]
}
```

---

## AI data control

The `ai_features_enabled` preference (off by default) gates whether any data is
sent to an AI model. It is toggled from the settings page via
`PUT /api/v1/users/me/preferences`. When off, no personal data leaves the backend
for AI purposes, and the tracker remains fully functional. AI never modifies data
without an explicit user-approved preview (see `docs/ai-design.md` when present).

---

## Notification control

The `email_notifications_enabled` preference controls whether FitTrack may send
product or summary emails. Security-related messages (for example password
resets) are not governed by this opt-in. Toggled from the settings page.

---

## Deleting individual records

Per-record deletion is handled by each domain's own endpoints and surfaced on the
relevant tracking page (weight, workouts, nutrition, measurements, wellness,
habits, goals). Habits are archived rather than hard-deleted to preserve streak
history; other records are removed directly. The settings page points users to
these pages for partial deletion.

---

## Deleting your account

```
DELETE /api/v1/privacy/account   body: { "password": "<current password>" }
```

- The current password is re-verified server-side, so a stolen session cookie
  alone cannot destroy an account. A wrong password returns `401`.
- The frontend additionally requires the user to type `DELETE` to confirm,
  guarding against accidental clicks.
- Deletion is an **immediate hard delete** and is irreversible. We recommend
  exporting first; the UI says so.
- On success the response clears both auth cookies so the now-invalid session
  does not linger in the browser.

### How the cascade works

Account deletion uses the ORM (`db.delete(user)`) rather than a single database
cascade. This is deliberate: two foreign keys use `ON DELETE RESTRICT`
(`food_logs -> foods`, and `workout_exercises` / `workout_template_exercises ->
exercises`). PostgreSQL checks `RESTRICT` immediately, so a pure database cascade
from the user row could fail even though the referencing rows are also being
removed. The ORM deletes children in foreign-key-dependency order, which
satisfies those constraints. `ai_usage_logs` (which has no ORM relationship on
`User`) is purged explicitly first; its database-level `ON DELETE CASCADE` would
also cover it, but the explicit delete keeps behaviour identical under test
databases that do not enforce foreign keys.

### API note

`DELETE /api/v1/privacy/account` returns `200` with a small confirmation body
rather than `204`, because the installed FastAPI version rejects a request body
on a `204` route and the password must travel in the body.

---

## Not yet covered

The following are intentionally out of scope for Phase 14 and tracked for later
phases:

- Progress photos (the feature does not exist yet; when added it must be private
  by default).
- Reviewing and disconnecting external integrations (Phase 15+).
- A soft-delete / recovery grace period (current behaviour is immediate hard
  delete).
