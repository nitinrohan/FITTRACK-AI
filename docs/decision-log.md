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
