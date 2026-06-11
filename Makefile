.PHONY: help up down build logs shell-api shell-db migrate migration seed \
        test-api lint-api typecheck-api test-web lint-web typecheck-web \
        test lint clean

# ── Variables ──────────────────────────────────────────────────────────────
COMPOSE = docker-compose
API_SERVICE = api
WEB_SERVICE = web
DB_SERVICE  = db

# ── Help ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "FitTrack AI — Development Commands"
	@echo "======================================"
	@echo "  make up            Start all services (detached)"
	@echo "  make down          Stop and remove containers"
	@echo "  make build         Rebuild all images"
	@echo "  make logs          Tail all service logs"
	@echo "  make logs-api      Tail API logs"
	@echo "  make shell-api     Open a shell in the API container"
	@echo "  make shell-db      Open psql in the DB container"
	@echo "  make migrate       Run pending Alembic migrations"
	@echo "  make migration m=  Create a new migration (m=<name>)"
	@echo "  make seed          Seed development data"
	@echo "  make test          Run all tests (api + web)"
	@echo "  make test-api      Run backend tests"
	@echo "  make test-web      Run frontend tests"
	@echo "  make lint          Run all linters"
	@echo "  make lint-api      Run ruff on the API"
	@echo "  make lint-web      Run ESLint on the web app"
	@echo "  make typecheck-api Run mypy on the API"
	@echo "  make typecheck-web Run tsc --noEmit on the web app"
	@echo "  make clean         Remove containers, volumes, and caches"
	@echo ""

# ── Services ───────────────────────────────────────────────────────────────
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f $(API_SERVICE)

shell-api:
	$(COMPOSE) exec $(API_SERVICE) /bin/sh

shell-db:
	$(COMPOSE) exec $(DB_SERVICE) psql -U fittrack -d fittrack

# ── Database ───────────────────────────────────────────────────────────────
migrate:
	$(COMPOSE) exec $(API_SERVICE) alembic upgrade head

migration:
	$(COMPOSE) exec $(API_SERVICE) alembic revision --autogenerate -m "$(m)"

seed:
	$(COMPOSE) exec $(API_SERVICE) python -m scripts.seed

# ── Testing ────────────────────────────────────────────────────────────────
test-api:
	$(COMPOSE) exec $(API_SERVICE) pytest tests/ -v --tb=short

test-web:
	$(COMPOSE) exec $(WEB_SERVICE) npm test -- --passWithNoTests

test: test-api test-web

# ── Linting & Type-checking ────────────────────────────────────────────────
lint-api:
	$(COMPOSE) exec $(API_SERVICE) ruff check app tests

lint-web:
	$(COMPOSE) exec $(WEB_SERVICE) npm run lint

lint: lint-api lint-web

typecheck-api:
	$(COMPOSE) exec $(API_SERVICE) mypy app

typecheck-web:
	$(COMPOSE) exec $(WEB_SERVICE) npx tsc --noEmit

# ── Cleanup ────────────────────────────────────────────────────────────────
clean:
	$(COMPOSE) down -v --remove-orphans
	find ./apps/api -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find ./apps/api -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find ./apps/api -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find ./apps/api -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf ./apps/web/.next ./apps/web/node_modules 2>/dev/null || true
