# FitTrack AI - Architecture Decision Log

Each entry follows the format:
**Context** - what situation prompted the decision  
**Decision** - what was chosen  
**Rationale** - why  
**Trade-offs** - what was given up  
**Status** - Accepted | Superseded | Deprecated

---

## ADR-001: Modular monolith over microservices

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing initial deployment architecture for a new product with one primary user.

**Decision:** Single deployable unit (FastAPI backend + Next.js frontend + PostgreSQL) with clean internal domain boundaries.

**Rationale:**
- Premature service extraction adds significant operational overhead (network latency, distributed transactions, service discovery, separate deployments) before the product has proven its value.
- Clean internal boundaries (routers → services → repositories → models) make future service extraction straightforward when there is a demonstrated need.
- A single database makes joining data, running migrations, and maintaining consistency dramatically simpler.

**Trade-offs:** Cannot scale individual components independently. Acceptable for MVP; revisit at 10k+ daily active users.

---

## ADR-002: Synchronous SQLAlchemy 2.0 over async

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing between sync and async SQLAlchemy for database access.

**Decision:** Synchronous SQLAlchemy 2.0 with psycopg2-binary.

**Rationale:**
- FastAPI handles sync route handlers via a thread pool - no blocking of the event loop.
- Sync SQLAlchemy is significantly simpler: no async context managers, no `await` in repositories, no async Alembic configuration.
- The application is not I/O-bound at MVP scale (no concurrent thousands of users).
- Alembic migration support is more mature for sync.

**Trade-offs:** Lower theoretical throughput under high concurrency. Migrating to async SQLAlchemy + asyncpg is a well-understood upgrade path when needed.

---

## ADR-003: JWT in HTTP-only cookies over localStorage

**Date:** 2026-06-10  
**Status:** Accepted (Phase 2 implementation)

**Context:** Choosing how to store authentication tokens in the browser.

**Decision:** JWT access token and refresh token in separate HTTP-only, SameSite=Lax cookies.

**Rationale:**
- HTTP-only cookies are not accessible via JavaScript, eliminating XSS token theft.
- SameSite=Lax provides CSRF protection for most state-changing requests.
- Next.js API rewrites mean the browser only communicates with one origin.

**Trade-offs:** Slightly more complex server-side token management. No localStorage means tokens survive page refreshes automatically (a benefit, not a trade-off).

---

## ADR-004: UUID v4 primary keys over auto-increment integers

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing primary key strategy for all database tables.

**Decision:** UUID v4, generated in Python (not by the database).

**Rationale:**
- UUIDs are safe to expose in URLs - sequential integers reveal record counts and allow enumeration attacks.
- Generated in Python so the application has the ID before the INSERT commits - useful for optimistic UI, idempotency keys, and logging.
- Consistent across all tables; no type mismatches when joining.

**Trade-offs:** 16 bytes vs 4-8 bytes for integers. Index fragmentation is higher with random UUIDs, but acceptable at MVP scale. UUIDv7 (monotonic) can be adopted later for better index locality.

---

## ADR-005: Canonical internal units (kilograms, meters, milliliters, UTC)

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** The application must support metric and imperial units across different users and regions.

**Decision:** Store all values in a single canonical unit per dimension. Convert only at input (user entry) and display (rendering).

**Rationale:**
- Eliminates per-row unit columns and conditional queries.
- Makes calculations, aggregations, and comparisons trivial - no unit-aware arithmetic in SQL.
- A single conversion layer (unit service) is the only place where conversion bugs can exist.
- Historical data remains consistent if a user switches their display preference.

**Trade-offs:** A data migration is required if the canonical unit ever needs to change (unlikely). Slight cognitive overhead when reading raw database values.

---

## ADR-006: Ruff over flake8 + isort + black

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing Python linting and formatting tools.

**Decision:** Ruff for both linting (replacing flake8, bugbear, isort, pyupgrade) and formatting (replacing black).

**Rationale:**
- Single tool replaces five separate tools.
- 10-100× faster than the tools it replaces.
- Active development with regular rule additions.
- Compatible with black's formatting style.

**Trade-offs:** Ruff is newer than flake8/black. Ruff format is not identical to black format in every edge case; the difference is cosmetic and consistent.

---

## ADR-007: Next.js App Router over Pages Router

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing Next.js routing strategy.

**Decision:** App Router (Next.js 14, React Server Components).

**Rationale:**
- React Server Components reduce client-side JavaScript bundle size significantly.
- Layout nesting is cleaner and more composable than `_app.tsx` + `_document.tsx`.
- App Router is the recommended and actively developed path for Next.js.
- Streaming and Suspense boundaries enable better loading states out of the box.

**Trade-offs:** Some third-party libraries have incomplete App Router support. The learning curve is steeper than the Pages Router. Components must explicitly opt into client-side rendering with `"use client"`.

---

## ADR-008: AI provider abstraction with safe fallback

**Date:** 2026-06-10  
**Status:** Accepted (Phase 6 implementation)

**Context:** The application uses AI for summaries and recommendations but must remain usable without AI.

**Decision:** All AI calls go through an `AIProvider` interface with three implementations: `AnthropicProvider`, `OpenAIProvider`, and `NullProvider`. `NullProvider` returns a polite "AI features are currently unavailable" response without raising an error.

**Rationale:**
- Core tracking features (logging workouts, meals, measurements) have zero dependency on AI.
- An AI provider outage should not degrade tracking functionality.
- Provider-independence allows switching models without touching application code.

**Trade-offs:** Additional abstraction layer. Cost: one interface + three implementations. Benefit: the application degrades gracefully under any AI failure mode.

---

## ADR-009: pydantic-settings for environment configuration

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing how to load and validate application configuration.

**Decision:** `pydantic-settings` with a `Settings` class, cached via `@lru_cache`.

**Rationale:**
- Validates all configuration at startup - misconfigured deployments fail immediately with clear error messages rather than at the first runtime use.
- Type annotations document the expected format of every variable.
- The `@lru_cache` decorator means settings are loaded once per process.
- Test override is straightforward: `get_settings.cache_clear()` before injecting test env vars.

**Trade-offs:** None significant at this scale.

---

## ADR-010: Docker Compose for local development

**Date:** 2026-06-10  
**Status:** Accepted

**Context:** Choosing local development environment tooling.

**Decision:** Docker Compose with source-code volumes for hot-reload.

**Rationale:**
- Every developer gets an identical environment regardless of host OS.
- No "works on my machine" issues from differing Python, Node, or PostgreSQL versions.
- `make up` is a single command from zero to running application.
- Hot-reload via mounted volumes means development speed is not sacrificed.

**Trade-offs:** Docker Desktop must be installed. First `docker-compose up` is slower than running services directly. Both mitigated by clear README instructions.

---

## ADR-011: Account deletion is an immediate hard delete

**Date:** 2026-06-26  
**Status:** Accepted

**Context:** Phase 14 needs an account-deletion capability. The options were an immediate hard delete versus a soft delete with a recovery grace period and a scheduled purge job.

**Decision:** Immediate hard delete, gated by re-verifying the account password (backend) and a typed `DELETE` confirmation (frontend).

**Rationale:**
- Matches the plain-language meaning users expect from "delete my account".
- No background purge job or extra account state to maintain in the MVP.
- A full data export exists alongside it, so users can keep their data before deleting.

**Trade-offs:** No self-service recovery window - deletion is irreversible. Acceptable for the MVP; a soft-delete grace period is noted as possible future work in `docs/privacy.md`.

---

## ADR-012: Delete via ORM cascade, not a single database cascade

**Date:** 2026-06-26  
**Status:** Accepted

**Context:** Deleting a user must remove all owned rows. Two foreign keys use `ON DELETE RESTRICT` (`food_logs -> foods`, and `workout_exercises` / `workout_template_exercises -> exercises`).

**Decision:** Use `db.delete(user)` and the ORM relationship cascades, purging `ai_usage_logs` explicitly first.

**Rationale:**
- PostgreSQL checks `RESTRICT` immediately, so a pure DB-level cascade from the user row could fail even when the referencing rows are also being deleted. The ORM deletes children in FK-dependency order, satisfying `RESTRICT`.
- `ai_usage_logs` has no ORM relationship on `User`; deleting it explicitly keeps behaviour identical under test databases that do not enforce foreign keys.

**Trade-offs:** Slightly more application code than relying solely on DB cascades, in exchange for correctness across both PostgreSQL and the test setup.

---

## ADR-013: DELETE account returns 200, not 204

**Date:** 2026-06-26  
**Status:** Accepted

**Context:** The account-deletion endpoint must receive the current password in the request body. The installed FastAPI version asserts that a `204 No Content` route cannot declare a request body.

**Decision:** `DELETE /api/v1/privacy/account` returns `200` with a small confirmation body instead of `204`.

**Rationale:** Keeps the password in the request body (the correct place for a secret, versus a query string or header) while satisfying the framework constraint.

**Trade-offs:** Minor deviation from the "204 for deletes" convention used elsewhere; documented here and in `docs/privacy.md`.

---

## ADR-014: Stress readings are a separate domain from the wellness check-in

**Date:** 2026-06-26  
**Status:** Accepted

**Context:** WellnessLog already has a subjective `stress` field on a 1-5 scale (a once-or-twice-daily check-in). The new Stress feature needs a finer-grained, multiple-readings-per-day 0-100 metric with daily highest/lowest/average and a Low/Moderate/High band, matching the requested design.

**Decision:** Add a dedicated `stress_logs` table (0-100, point-in-time `recorded_at`, `source` defaulting to "manual") rather than overloading the wellness `stress` field. Leave the wellness check-in unchanged.

**Rationale:**
- The 1-5 daily rating cannot represent multiple intraday readings or a 0-100 range.
- A `source` column is an extension point for wearable-provided readings later, without touching the subjective check-in.
- Daily highest/lowest/average and the band are derived at query time (timezone-aware), never stored.

**Trade-offs:** Two stress concepts now exist. Mitigated by keeping their purposes distinct (subjective daily mood/energy/stress check-in vs. granular stress readings) and documenting it here.

---

## ADR-015: Mindfulness music is an external link, not embedded audio

**Date:** 2026-06-26  
**Status:** Accepted

**Context:** The mindfulness feature should let users practise sessions with optional music, but there is no licensed audio source or player in the product yet.

**Decision:** `MindfulnessSession.external_url` holds an optional link (e.g. Spotify/YouTube) that opens in a new tab. Sessions with no link show a "Link coming soon" state. Mindful minutes are logged separately in `mindfulness_logs`.

**Rationale:**
- Ships the useful part (a session library + minute logging + streak) without taking on audio licensing/hosting now.
- The link field is a clean seam to fill in real content later, per session.

**Trade-offs:** No in-app playback yet; the experience depends on third-party links until an audio source is chosen.

---

## ADR-016: Nutrition targets are a dedicated settings table, not a Goal

**Date:** 2026-07-01  
**Status:** Accepted

**Context:** The daily nutrition insight feature needs to compare logged calories/protein/carbs/fat/fiber against numbers the user actually chose - never invented ones. The existing `Goal` model (title/description/target_value/status lifecycle) covers open-ended, dated fitness goals like "lose 5kg by September."

**Decision:** Added a separate `nutrition_targets` table - one optional row per user with five nullable fields (`calorie_target_kcal`, `protein_target_g`, `carbs_target_g`, `fat_target_g`, `fiber_target_g`). No status lifecycle; it's a plain settings row, upserted via `PUT /api/v1/nutrition/targets`.

**Rationale:**
- Daily macro targets are a standing setting, not a dated goal with active/paused/completed states - forcing them into `Goal` would mean either faking a lifecycle or adding nutrition-specific columns to a general-purpose table.
- Every field is independently nullable so a user can set just a protein target. `is_set` on the response is `true` only when at least one field is non-null, and the AI insight service is required to treat an unset field as "no target," never a guessed default (see AI Assistant Rules: never invent user goals/data).

**Trade-offs:** Two separate places a user's "goals" can live (`Goal` for dated targets, `NutritionTarget` for daily macros). Acceptable - they answer different questions and the nutrition table is intentionally minimal.

---

## ADR-017: Multi-item AI meal parsing is a separate endpoint, not a loop over the single-item one

**Date:** 2026-07-01  
**Status:** Accepted

**Context:** Users often describe an entire meal or "everything eaten so far today" in one message (e.g. "45g oats, 200ml almond milk, 2 belvita biscuits, 1 scoop whey protein"). The existing `/estimate-macros` endpoint and prompt (`macro-est-v1`) are built for exactly one food.

**Decision:** Added `POST /api/v1/nutrition/estimate-meal` with its own prompt version (`macro-est-multi-v1`) that asks the model to split the description into a JSON array of items, each with independent per-100g macros (including fiber, added to both the single- and multi-item schemas). Portion totals and the meal-level totals are computed in deterministic Python, never by the model. A separate `POST /api/v1/nutrition/log-meal` bulk-saves all user-approved items as one Food + one FoodLog per item in a single atomic commit.

**Rationale:**
- A single free-text call is far cheaper and more natural than making the user submit N separate single-item estimates, and lets the model use context across items (e.g. recognising "2 scoops" as two identical entries rather than one doubled one).
- Keeping it a distinct endpoint/prompt (rather than looping the single-item prompt) means the response shape (list of items + totals) is explicit and versioned independently, so future prompt tuning for one flow doesn't silently affect the other.
- Items with all-zero macros (a food the model genuinely couldn't estimate) are dropped from the preview rather than shown as a bogus zero-calorie row.

**Trade-offs:** Two prompts/response shapes to maintain instead of one. Accepted given how different the parsing task and response shape are (single object vs. array + totals).

---

## ADR-018: Daily nutrition insight computes comparisons in code; the model only writes the narrative

**Date:** 2026-07-01  
**Status:** Accepted

**Context:** After logging a batch of foods, users want a plain-language read on how the day is tracking against their own targets, plus manageable suggestions for remaining meals - similar in spirit to the existing weekly AI summary but scoped to a single day's nutrition.

**Decision:** `daily_insight_service.get_daily_insight()` computes every number (current vs. target, percent, remaining) in deterministic Python from the day's real `FoodLog` totals and the user's own `NutritionTarget` row, then sends only that computed snapshot to the model, which is restricted to writing 2-4 highlights, 1-3 suggestions, and one encouragement line. When AI is off or fails, a rule-based fallback derived from the same comparisons is returned instead - the insight is never unavailable outright, and it never mutates any data (it's a GET). General population reference ranges (e.g. typical fiber intake) may be mentioned to the model as generic educational context, explicitly labelled as not the user's personal target.

**Rationale:**
- Matches the existing pattern in `weekly_summary_service` (deterministic snapshot -> versioned prompt -> parsed JSON -> rule-based fallback) rather than inventing a new one.
- Keeps the model out of the one place a math error would be most visible and most damaging to trust - the actual macro numbers.
- Satisfies the health-and-safety rule against presenting estimates as medical fact: the endpoint never diagnoses, guarantees outcomes, or recommends extreme restriction, and always discloses it isn't dietitian advice.

**Trade-offs:** The AI's narrative is only as good as the deterministic snapshot handed to it - it cannot reason over data outside that day (e.g. weekly trends), which is an intentional scope boundary, not an oversight.

---

## ADR-019: Recipes are hard-deleted; logging a recipe creates plain FoodLog rows

**Date:** 2026-07-01  
**Status:** Accepted

**Context:** Users wanted to save a combination of foods they eat often (e.g. a specific shake) and re-log the exact same thing later - with the option to log a different-sized portion - without re-describing it to the AI or re-searching each food.

**Decision:** `Recipe` -> `RecipeItem` is a simple one-to-many (food_id + quantity_g + position), hard-deleted on delete (items cascade) rather than archived like `Food`/`Habit`. `POST /{id}/log` creates one ordinary `FoodLog` row per item via the same `nutrition_repository.create_food_log` the manual and AI-estimated flows use, with `quantity_g = saved_quantity * scale_factor` (default 1.0 = exactly as saved). A recipe itself never appears in daily totals, progress, or the dashboard - only the FoodLog rows it produces do. Recipe item/total macros are computed fresh from the current `Food.*_per_100g` values every time (never cached on the recipe), matching how `FoodLog` display values already work. The scale-math and macro-summing helpers were extracted into a new shared `nutrition_calculations.py` (`scale_macro`, `scale_optional_macro`, `sum_macro_totals`) so `nutrition_service` and `recipe_service` share one tested implementation instead of duplicating the arithmetic.

**Rationale:**
- No other table references `recipe_id` - logging one just creates independent `FoodLog` rows - so a hard delete (with `RecipeItem` cascading) is safe and there's no history to preserve, unlike `Habit` (whose completions reference the habit).
- Reusing `create_food_log` for logging means recipes get all the existing FoodLog behavior (daily totals, Progress-page charts, edit/delete afterward) for free, with zero special-casing anywhere else in the app.
- Computing macros fresh (not caching them on the recipe) means editing a food's macros later automatically updates every recipe that uses it, same guarantee `FoodLog` already gives.

**Trade-offs:** If a food referenced by a saved recipe needs to be deleted, the `RESTRICT` foreign key blocks it (same trade-off `FoodLog` already accepts) - the user would need to delete the recipe (or remove that item) first.
