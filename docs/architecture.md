# FitTrack AI — Architecture

## Overview

FitTrack AI is a web application built as a **modular monolith** — a single deployable unit with clearly separated internal domains. This gives the simplicity of a monolith (single deployment, shared database, no network hops between services) while maintaining clean boundaries that make future extraction into services straightforward if needed.

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│           Next.js 14 (App Router, TypeScript)               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (rewrites /api/* → backend)
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│  Routers → Schemas → Services → Repositories → Models       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Auth       │  │  AI Layer    │  │  Domain Calcs    │  │
│  │  (Phase 2)   │  │  (Phase 6)   │  │  (Phase 3+)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQLAlchemy
┌──────────────────────────▼──────────────────────────────────┐
│                      PostgreSQL 15                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Backend Layer Responsibilities

Each layer has a single, clear responsibility:

| Layer | Location | Responsibility |
|---|---|---|
| **Routers** | `app/routers/` | HTTP request/response binding. Thin — validate input, call service, return response. No business logic. |
| **Schemas** | `app/schemas/` | Pydantic models for request bodies, response envelopes, and validation rules. |
| **Services** | `app/services/` | Business logic, orchestration, domain rules. Calls repositories; does not touch SQLAlchemy directly. |
| **Repositories** | `app/repositories/` | Database access. All SQLAlchemy queries live here. Returns domain objects, never raw SQL result rows. |
| **Models** | `app/models/` | SQLAlchemy ORM definitions. Column types, relationships, indexes. |
| **Domain** | `app/domain/` | Pure calculation functions (BMI, 1RM, moving average, pace, unit conversion). No I/O. |
| **AI** | `app/ai/` | Provider abstraction, prompt management, structured output parsing, usage logging. |
| **Core** | `app/core/` | Shared utilities: pagination, security helpers, dependency injection. |
| **Config** | `app/config.py` | Settings loaded from environment variables via pydantic-settings. |

---

## Frontend Layer Responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| **Pages** | `src/app/**/page.tsx` | Route entry points. Server Components by default; add `"use client"` only where interactivity is required. |
| **Features** | `src/features/` | Self-contained feature modules (workouts, nutrition, etc.) each containing components, hooks, and schemas. |
| **Components** | `src/components/ui/` | Primitive, design-system-level components (Button, Input, Card, etc.). No business logic. |
| **Hooks** | `src/hooks/` | Shared React hooks for data fetching, forms, and UI state. |
| **API Client** | `src/lib/api-client.ts` | Single `fetch` wrapper. Handles auth cookies, error parsing, and base URL. |
| **Schemas** | `src/schemas/` | Zod validation schemas shared between forms and API responses. |
| **Types** | `src/types/` | TypeScript type definitions. |

---

## Data Flow

```
User action (form submit)
  → Zod validation (frontend)
  → POST /api/v1/resource  (HTTP-only cookie carries auth token)
  → FastAPI router         (Pydantic validation)
  → Service               (business rules, authorization check)
  → Repository            (SQLAlchemy query)
  → PostgreSQL
  → Repository            (returns ORM model)
  → Service               (maps to response schema)
  → Router                (returns JSONResponse)
  → React state update
  → UI re-render
```

---

## Internal Canonical Units

All values are stored in canonical units and converted only for input/display:

| Dimension | Stored as |
|---|---|
| Body weight, load | kilograms (float, 3 dp) |
| Height, distance | meters (float, 3 dp) |
| Volume (water, liquid) | milliliters (float, 1 dp) |
| Energy | kilocalories (float, 1 dp) |
| Temperature | Celsius |
| Timestamps | UTC (naive datetime, assumed UTC) |
| Identifiers | UUID v4 |

---

## Authentication Design (Phase 2)

- Passwords hashed with bcrypt (passlib, cost factor 12)
- JWT access tokens (30-minute expiry) in HTTP-only, SameSite=Lax cookies
- JWT refresh tokens (30-day expiry) in a separate HTTP-only cookie
- Token rotation on every refresh
- All protected endpoints check ownership: `WHERE user_id = :current_user_id`
- AI provider API keys are backend-only — never sent to the frontend

---

## AI Layer Design (Phase 6)

The AI layer is designed as a provider-independent abstraction:

```
AIRequest → AIProvider (interface)
               ├── AnthropicProvider
               ├── OpenAIProvider
               └── NullProvider (returns "AI unavailable" safely)
```

The core tracker works fully when `AI_PROVIDER=none`. The AI layer reads verified application data (via services) and uses the language model only for explanation and summarisation — never as the source of truth for calculations.

All AI responses are parsed into typed `AIResponse` objects before being sent to the frontend. Raw model output never reaches the API response.

---

## Future Scalability Path

The modular monolith can evolve without a rewrite:

1. **Multi-tenant:** Add `organization_id` to user-owned tables; scope all queries by tenant.
2. **Trainer-client:** Add `TrainerClientRelationship` table; extend authorization service to check relationship permissions.
3. **Background jobs:** Extract long-running tasks (AI summaries, data exports) to a worker queue (Celery + Redis or similar) — the service layer is already decoupled from the HTTP request cycle.
4. **Microservices (if justified):** The AI service and the notification service are the most natural extraction candidates, because they have distinct infrastructure requirements.

---

## Technology Choices

See [`decision-log.md`](./decision-log.md) for full rationale on each choice.
