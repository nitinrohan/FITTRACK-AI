# FitTrack AI

An AI-powered personal fitness tracker for workouts, nutrition, body measurements, wellness, habits, goals, and progress insights.

The MVP is designed for one user and built to expand into a multi-user platform supporting trainers, clients, gyms, organizations, and wearable integrations.

---

## What's Built

**Phases 1-14 complete.** Habits (daily check-offs, streaks) + dashboard widget, and a **Progress** page with selectable-range charts (weight / workouts / calories) - each chart paired with an accessible text summary and data table.

Latest add: a **Mind** page - **Stress** (self-reported 0-100 readings with daily highest / lowest / average and a Low/Moderate/High band gauge) and **Mindfulness** (a curated session library plus mindful-minute logging with a day streak). Stress is presented supportively and is explicitly not a medical assessment.

Also recent: **Settings & privacy** (Phase 14) - a per-category summary of your stored data, a full **JSON data export** (downloaded client-side), AI and email-notification opt-ins, and **password-confirmed account deletion** (irreversible hard delete, typed confirmation). See [`docs/privacy.md`](./docs/privacy.md).

Earlier add-on: **AI macro estimation for nutrition** - describe a food in plain text and the AI returns an editable macro *estimate* you review before saving (never auto-saved; portion math is deterministic). The AI layer is provider-independent (Anthropic / OpenAI / **Ollama** for free local dev) with graceful fallback when AI is off. Backend: 501 tests passing (4 pre-existing weight-test failures unrelated), ruff clean, mypy 0 errors; frontend tsc + eslint clean.

| Feature | Details |
|---|---|
| **Foundation** | FastAPI + Next.js + PostgreSQL + Docker Compose + GitHub Actions CI |
| **Authentication** | JWT + bcrypt, register/login/logout/refresh, HTTP-only cookies, route protection |
| **Onboarding** | Multi-step wizard, unit preferences (metric/imperial), timezone, fitness level |
| **Goals** | Create/track fitness goals with progress calculation |
| **Exercise library** | 60-exercise seed, category + equipment filters, search |
| **Workout templates** | Create reusable templates with ordered exercises |
| **Workout logging** | Active workout timer, set/rep/weight/duration logging, personal record detection |
| **Workout history** | Full history with filter tabs, volume calculations |
| **Nutrition tracking** | Food database, meal logging, daily macro totals (calories, protein, carbs, fat) |
| **Body measurements** | Weight entries + body measurements (chest, waist, hips, etc.) with trend tracking |
| **Dashboard** | Summary widgets: recent workouts, weight trend, goal progress, macro summary |
| **AI summaries** | Provider-independent AI service, weekly summary generation, usage logging with cost tracking |

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop) 4.x+
- [Docker Compose](https://docs.docker.com/compose/) v2.x (included with Docker Desktop)
- (Optional for local dev without Docker) Python 3.11+, Node 20+, PostgreSQL 15

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> fittrack-ai
cd fittrack-ai
cp .env.example .env
```

Edit `.env` - at minimum change:
- `POSTGRES_PASSWORD`
- `APP_SECRET_KEY`
- `JWT_SECRET_KEY`

### 2. Start all services

```bash
make up
# or: docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **FastAPI API** on port 8000 (with hot-reload)
- **Next.js Web** on port 3000 (with hot-reload)

Migrations run automatically before the API starts.

### 3. Verify

```
http://localhost:3000     - Web app
http://localhost:8000     - API root
http://localhost:8000/docs - OpenAPI documentation
http://localhost:8000/health - Liveness check
http://localhost:8000/ready  - Readiness check (DB connectivity)
```

---

## Environment Variables

See [`.env.example`](./.env.example) for all available variables with descriptions.

Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Full PostgreSQL connection string |
| `APP_SECRET_KEY` | Application secret (min 32 chars) |
| `JWT_SECRET_KEY` | JWT signing secret (min 32 chars) |
| `APP_ENV` | `development` \| `production` \| `test` |
| `AI_PROVIDER` | `anthropic` \| `openai` \| `none` |
| `ANTHROPIC_API_KEY` | Anthropic API key (backend-only) |
| `NEXT_PUBLIC_API_URL` | API URL visible to the browser |

---

## Development Commands

All commands are available via `make`. Run `make help` for the full list.

### Database

```bash
make migrate          # Apply pending migrations
make migration m="add users table"  # Generate a new migration
make seed             # Load development seed data
make shell-db         # Open psql session
```

### Testing

```bash
make test-api         # Run backend pytest suite
make test-web         # Run frontend jest suite
make test             # Run both
```

### Linting and type-checking

```bash
make lint-api         # ruff check
make typecheck-api    # mypy
make lint-web         # eslint
make typecheck-web    # tsc --noEmit
make lint             # Both
```

### Logs

```bash
make logs             # All services
make logs-api         # API only
```

---

## Running Without Docker

### Backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set environment
export DATABASE_URL="postgresql://fittrack:changeme@localhost:5432/fittrack"
export APP_SECRET_KEY="your-secret"
export JWT_SECRET_KEY="your-jwt-secret"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm ci

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev   # http://localhost:3000
```

---

## Project Structure

```
fittrack-ai/
├── apps/
│   ├── api/                      # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py           # App factory, middleware, router wiring
│   │   │   ├── config.py         # Settings (pydantic-settings)
│   │   │   ├── database.py       # SQLAlchemy engine and session
│   │   │   ├── models/           # ORM models: user, goal, exercise, workout,
│   │   │   │                     #   nutrition, measurement, weight_entry, ai_log
│   │   │   ├── schemas/          # Pydantic request/response schemas
│   │   │   ├── repositories/     # Data-access layer (query logic)
│   │   │   ├── services/         # Business logic (calculations, AI, summaries)
│   │   │   ├── routers/          # Route handlers: auth, users, goals, exercises,
│   │   │   │                     #   workouts, nutrition, measurements, weight,
│   │   │   │                     #   dashboard, ai, health
│   │   │   ├── seeds/            # Development seed data (60 exercises)
│   │   │   └── core/             # Shared utilities (pagination, security)
│   │   ├── alembic/              # 8 versioned migrations
│   │   └── tests/                # 362-test pytest suite
│   └── web/                      # Next.js 15 frontend
│       └── src/
│           ├── app/
│           │   ├── (auth)/       # Login + register pages
│           │   └── (dashboard)/  # Dashboard, goals, workouts, templates,
│           │                     #   nutrition, measurements, weight pages
│           ├── components/       # Reusable UI components
│           ├── features/         # Domain hooks (workouts, nutrition, etc.)
│           ├── lib/              # API client wrappers per domain
│           └── types/            # TypeScript interfaces per domain
├── docs/                         # Architecture, decisions, data model, security, AI
├── .github/workflows/            # GitHub Actions CI
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Running Tests Manually

### Backend (362 tests)

```bash
cd apps/api
export APP_ENV=test
export DATABASE_URL="postgresql://fittrack:testpassword@localhost:5432/fittrack_test"
export APP_SECRET_KEY="test-secret"
export JWT_SECRET_KEY="test-jwt-secret"
pytest tests/ -v
```

### Lint and type-checking

```bash
cd apps/api
ruff check app tests   # All checks passed!
mypy app               # 0 errors

cd apps/web
npx tsc --noEmit       # 0 errors
```

> **Note:** Jest crashes with a Bus error in some sandbox environments (pre-existing Docker/Node issue). Use `tsc --noEmit` as the reliable frontend check until the environment is resolved.

---

## Troubleshooting

**`make up` fails with DB connection error**
The API retries until the DB health check passes. Wait 10-15 seconds and check `make logs-api`.

**Port already in use**
Change the host port in `docker-compose.yml` (e.g. `"8001:8000"` for the API).

**Migrations fail**
Run `make shell-api` then `alembic history` to see the current state. Check `make logs-api` for the error detail.

**Hot-reload not working**
Ensure the source volumes are mounted (check `docker-compose.yml`). Restart with `make down && make up`.

---

## Documentation

- [`docs/architecture.md`](./docs/architecture.md) - System design and component overview
- [`docs/decision-log.md`](./docs/decision-log.md) - Architecture decision records
- [`docs/data-model.md`](./docs/data-model.md) - Database schema (Phase 2+)
- [`docs/api.md`](./docs/api.md) - API reference (Phase 2+)
- [`docs/security.md`](./docs/security.md) - Security design (Phase 2+)
- [`docs/ai-design.md`](./docs/ai-design.md) - AI assistant architecture (Phase 6+)
- [`docs/privacy.md`](./docs/privacy.md) - Privacy, data export, and account deletion (Phase 14)

---

## Implementation Phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Project foundation | ✅ Complete |
| 2 | Authentication and user profiles | ✅ Complete |
| 3 | Onboarding and user preferences | ✅ Complete |
| 4 | Goals | ✅ Complete |
| 5 | Exercise library + weight entries | ✅ Complete |
| 6 | Workout templates + logging | ✅ Complete |
| 7 | Workout history and PR detection | ✅ Complete |
| 8 | Nutrition tracking | ✅ Complete |
| 9 | Body measurements | ✅ Complete |
| 10 | Dashboard + AI summaries | ✅ Complete |
| 11 | Water, sleep, steps, and wellness | ✅ Complete |
| 12 | Habits | ✅ Complete |
| 13 | Progress charts | ✅ Complete |
| 14 | Privacy, export, and account deletion | ✅ Complete |
| 15 | Integrations and platform features | 🔜 Next |
