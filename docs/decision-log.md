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
