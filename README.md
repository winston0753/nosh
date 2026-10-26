# Nosh

An iOS-first restaurant-discovery app: around a configured meal window it suggests one nearby unvisited restaurant, supports Go / Another / Not today, opens Apple Maps, and later confirms whether the visit happened and was good.

**Milestone 0.1 — Working Local Foundation ✓**

This checkpoint proves that the local database, migrations, API, recommendation engine, state machine, and mobile prototype work together. It is suitable for a source-control checkpoint; it is **not** yet ready for TestFlight or external testers.

| Milestone | Status |
|---|---|
| 1 — Repository and backend foundation | Complete |
| 2 — Deterministic suggestion API | Complete |
| 3 — Expo vertical slice | Partially complete — local vertical slice implemented; tester-readiness work remains |
| 4 — Notifications and private cohort readiness | Not started; not next |

All local verification gates pass (2026-10-25, after the meal-schedule change):
- 12 root spike tests
- 163 API unit tests (lint, format, strict mypy clean)
- 51 integration tests (PostGIS + real migrations + 6 concurrent DB tests) — **all pass**
- 70 mobile Jest tests (TypeScript, ESLint, Expo Doctor 20/20 clean)

Stack: FastAPI + SQLAlchemy 2 async API; Expo SDK 58 mobile app (React Native 0.88, Expo Router `~58.0.26`).

**Next:** complete Milestone 3 (see [Next milestone](#next-milestone)). On 2026-10-20 the product direction changed to current-location-first with live Google Places data (DECISIONS.md D019–D028). The meal schedule (D020), price-ceiling setting (D026), and Been here already (D025) are implemented; suggestions still use fixture places and a placeholder location.

Running locally:
- Docker Compose: PostgreSQL 16.4 + PostGIS 3.4
- Dev DB: `localhost:5432/nosh_dev` | Test DB: `localhost:5433/nosh_test`
- pgvector: intentionally deferred (see DECISIONS.md D013)

Proposal-backed visit confirmation requires a prior Go response on the exact proposal.

---

## Canonical documents

| Document | Purpose |
|---|---|
| [PRODUCT.md](PRODUCT.md) | Requirements, success metrics, edge cases, non-goals |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, data model, API, state machine, security |
| [RECOMMENDATIONS.md](RECOMMENDATIONS.md) | Eligibility, scoring, feedback semantics |
| [DECISIONS.md](DECISIONS.md) | Accepted choices, rejected alternatives |
| [IMPLEMENTATION_HANDOFF.md](IMPLEMENTATION_HANDOFF.md) | Milestone sequence |
| [notes.md](notes.md) | Chronological project log |

---

## Prerequisites

- Docker Desktop (for local PostgreSQL) or an accessible PostgreSQL 16+ with PostGIS
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node.js 22 LTS (`^22.13.0`) or 24 (`^24.3.0`) and npm, for mobile (Expo SDK 58 minimums)
- Python 3.11+

---

## Backend local setup

### 1. Start PostgreSQL

```bash
docker compose up -d db
# Wait for healthy: docker compose ps
```

### 2. Install API dependencies and apply migrations

```bash
cd services/api
uv sync --frozen --group dev
DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5432/nosh_dev \
  uv run --frozen alembic upgrade head
```

### 3. Configure environment

```bash
cp .env.example .env   # works as-is for local dev (AUTH_LOCAL_DEV=true)
```

### 4. Seed fixture restaurants

The place importer is a job inside the API project (`services/api/jobs/`). Its one supported invocation is from `services/api`:

```bash
DATABASE_URL=postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_dev \
  uv run --frozen python -m jobs.ingest_places.importer
# Fixture data loaded.
```

It is idempotent (existing places and cuisines are left unchanged). Jobs import the application as `app`, like the API itself; `tests/test_job_imports.py` fails if any module imports through `services.api.app` or if a job stops importing from this working directory.

### 5. Start the API

```bash
uv run fastapi dev app/main.py
```

### 6. Verify

```bash
curl http://localhost:8000/health/live
# {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/health/ready
# {"status":"ok","database":"connected"}
```

OpenAPI docs: http://localhost:8000/docs

### Local auth in dev mode

With `AUTH_LOCAL_DEV=true`, the Bearer token is any UUID string representing your user:

```bash
curl -H "Authorization: Bearer 00000000-0000-0000-0000-000000000001" \
  http://localhost:8000/v1/me/meal-schedule
```

---

## Mobile local setup

```bash
cd apps/mobile
npm ci
cp .env.example .env.local   # then fill in values (git-ignored)
npx expo start
# Press 'i' for iOS simulator
```

The app has two sign-in modes, and the API must match:

| Mobile `.env.local` | API `services/api/.env` | Sign-in |
|---|---|---|
| `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` set | `AUTH_LOCAL_DEV=false`, `SUPABASE_URL` set to the same project, `SUPABASE_JWT_SECRET` empty | Email a one-time code, then enter it |
| Both Supabase values empty | `AUTH_LOCAL_DEV=true` | Enter any UUID (local dev adapter) |

Use the project API URL (`https://<project-ref>.supabase.co`), not the dashboard URL. For email codes, the Supabase **Magic Link** and **Confirm signup** email templates (Authentication → Emails) must include `{{ .Token }}`. Supabase only allows editing these templates once custom SMTP is configured (Authentication → Emails → SMTP Settings); a Gmail app password on `smtp.gmail.com:465` works for development, and a domain sender is needed before inviting testers.

---

## Running tests

### Spike tests (root)

```bash
uv run pytest tests/ -q
# Expected: 12 passed
```

### API unit tests (no database required)

```bash
cd services/api
uv run --frozen pytest tests/ -q -m "not integration"
# Expected: 163 passed
```

### API integration tests (requires PostgreSQL)

Two databases are defined in `docker-compose.yml`:

| Service | Host port | Database | Purpose |
|---|---|---|---|
| `db` | `5432` | `nosh_dev` | Persistent development data |
| `db_test` | `5433` | `nosh_test` | **Disposable** — used for integration tests |

Never run destructive operations (downgrade to base) against port 5432.

```bash
# Start the disposable test database (binds to 127.0.0.1:5433)
docker compose --profile test up -d db_test

cd services/api
DATABASE_URL=postgresql+asyncpg://nosh:nosh_dev@localhost:5433/nosh_test \
APP_ENVIRONMENT=test \
AUTH_LOCAL_DEV=true \
  uv run --frozen pytest tests/ -v -m "integration"
# Expected: 51 passed (includes 6 genuine concurrent-DB tests)
```

In CI, GitHub Actions maps the postgres service container to port 5432 and sets `DATABASE_URL` accordingly in `ci.yml`.

The integration test fixture applies migrations automatically before the first test.

### Lint, format, and types

```bash
cd services/api
uv run --frozen ruff check app/ jobs/ tests/
uv run --frozen ruff format --check app/ jobs/ tests/
uv run --frozen mypy app/ jobs/ --strict
```

### Migration round-trip (always use the disposable test database, port 5433)

```bash
cd services/api
DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5433/nosh_test \
  uv run --frozen alembic downgrade base
DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5433/nosh_test \
  uv run --frozen alembic upgrade head
DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5433/nosh_test \
  uv run --frozen alembic check    # must print "No new upgrade operations detected"
```

For the development database (port 5432), only ever run `upgrade head` — never `downgrade`.

```bash
DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5432/nosh_dev \
  uv run --frozen alembic upgrade head
```

### Mobile checks

```bash
cd apps/mobile
npm ci
npm run typecheck       # TypeScript strict
npm run lint            # ESLint
npm test -- --runInBand # Jest unit tests (70 tests)
npx expo install --check
npx expo-doctor
```

### Whitespace check

```bash
git diff --check
```

---

## What works today

| Area | Status |
|---|---|
| Backend foundation (health, DB, migrations) | Verified locally against Docker PostgreSQL; migration round-trip and `alembic check` pass |
| 15 API routes (`/v1`) | Implemented and type-checked |
| policy_v0 recommendation engine | Pure-function, deterministic, 13 unit tests |
| Fixture restaurants (20 places, SF Mission) | Loadable via seed command above |
| Meal schedule (lunch/dinner, days, window, price ceiling) and Home/Work spots | Implemented (migration 0005); the app's survey sets the schedule |
| Go / Another / Not today / Been here already state machine | Implemented with idempotency; candidates ranked once per session |
| Visit confirmation + rating + history + progress | Implemented |
| Strict mypy | 0 errors |
| Mobile app (Expo SDK 58, Expo Router `~58.0.26`) | All MVP screens; Supabase email-code sign-in; meal-time survey; TypeScript + ESLint + 70 Jest tests + Expo Doctor (20/20) pass |
| Integration tests | 51 tests covering full flow, schedules, anchors, provenance, validation, replay, pagination, and concurrency; requires PostgreSQL |
| Place importer | `uv run --frozen python -m jobs.ingest_places.importer` from `services/api` |

## What is not yet complete

- **End-to-end local flow without Docker:** requires PostgreSQL running.
- **Current location (Milestone 3):** the app anchors every session at a placeholder SF Mission point and has no Home/Work setup screen yet (the API supports both); the price ceiling is stored but not yet applied (`policy_v1`).
- **Place data (Milestone 3):** suggestions use 20 fictional fixture places; D021 moves to live Google Places data.
- **Offline resilience (Milestone 3):** session identifiers are not persisted, and idempotent response writes are not queued during transient network failures.
- **EAS/TestFlight build (Milestone 3):** not configured.
- **App icons (Milestone 3):** `apps/mobile/assets/icon.png` and `notification-icon.png` are 1×1 placeholders.
- **Notifications (Milestone 4, not started):** Expo push tokens, scheduler/worker, confirmation prompts.
- **API hosting:** Fly.io with Supabase Postgres (D030); not yet deployed.

### Dependency audit (mobile, 2026-10-25, Expo SDK 58.0.19)

| Command | Moderate | High | Critical | Total |
|---|---|---|---|---|
| `npm audit` | 0 | 5 | 0 | 5 |
| `npm audit --omit=dev` | 0 | 5 | 0 | 5 |

All five come from Expo's CLI tooling: `expo` → `@expo/cli` → `@expo/code-signing-certificates` → `node-forge`, and `zod`. npm's only proposed remedy is a semver-major downgrade (`expo@54`), so `npm audit fix` / `--force` has deliberately not been run. On SDK 58.0.16 (2026-10-21) the counts were 53 total and 26 production; on SDK 53 (2026-10-13), 60 and 37.

---|---|---|---|---|
| `npm audit` | 16 | 44 | 0 | 60 |
| `npm audit --omit=dev` | 16 | 21 | 0 | 37 |

The findings reach the app through `expo`, `expo-constants`, `expo-linking`, `expo-notifications`, `react-native`, `jest-expo`, and `@types/jest`; every fix npm proposes is a semver-major change (including an `expo@44` downgrade). `npm audit fix` / `--force` has deliberately not been run; resolving these requires a recorded Expo SDK upgrade decision.

---

## Spike: cuisine-selection policy simulation

```bash
uv sync
uv run pytest tests/ -q
uv run python -m spike.cuisine_policy_sim --users 500
```

| Policy (no churn, 500 users, 90 days) | New restaurants | Rejections / session |
|---|---|---|
| lowest been-to % (spec) | 64.3 | 1.64 |
| random | 76.1 | 1.08 |
| Thompson + history prior | 80.5 | 0.87 |
| oracle (upper bound) | 82.0 | 0.81 |

---

## Project structure

```
apps/mobile/          Expo SDK 58 React Native iOS-first client (Expo Router ~58.0.26)
services/api/         FastAPI modular monolith
  app/
    auth/             Supabase JWT validation (JWKS RS256/ES256; legacy HS256) + local-dev UUID adapter
    schedules/        Meal schedule and Home/Work anchors
    places/           Place catalog, PostGIS filtering, manual place state
    recommendations/  policy_v0 pure engine (Thompson sampling + weighted scoring)
    suggestions/      Session lifecycle, candidate queue, Go/Another/Not today/Been here already
    visits/           Confirmation, ratings, history, monthly progress
    core/             Database, errors, async engine
  jobs/               Batch jobs in the API project (ingest_places importer)
  alembic/            Migrations 0001–0005 (upgrade + downgrade tested)
  tests/
    test_auth.py                30 unit tests
    test_schedule_validation.py 85 unit tests (schedule + meal-window rules, API 422s)
    test_health.py              4 unit tests
    test_job_imports.py         3 unit tests (job import-path guard)
    test_priors.py              7 unit tests (cuisine prior provenance)
    test_progress_metric.py     8 unit tests
    test_recommendations.py     13 unit tests (engine mechanics)
    test_suggestion_invariants.py  9 invariant tests
    test_state_machine.py       4 documentation tests
    test_integration.py         51 integration tests (PostgreSQL required)
spike/                Cuisine-policy simulation (preserved, 12 tests)
tests/                Root spike tests
db/                   Docker init SQL (PostGIS; pgvector deferred per D013)
```

## Next milestone

**Complete Milestone 3 — Expo vertical slice (tester readiness)**, following the 2026-10-20 decisions (evidence in `docs/research/2026-10-20-place-data-and-map-terms.md`):

1. ~~Upgrade Expo SDK 53 → 58 (D019)~~ — done 2026-10-21; App Store Connect requires Xcode 26 builds.
2. ~~Supabase passwordless email authentication~~ — done 2026-10-21 (email one-time code, one session provider, per-user query cache).
3. ~~Meal schedule (weekday lunch default, dinner opt-in), per-meal price ceiling, and optional Home/Work fallback spots replace dining contexts (D020, D026)~~ — done 2026-10-25, with Been here already (D025).
4. Live Google Places candidates behind a place-provider abstraction (fixtures in tests) and `policy_v1` ranking, including the price ceiling (D021, D022, D024, D026).
5. Foreground current location at open time, Home/Work setup, a Google map on the card, and Google Maps handoff. No background location.
6. Persist session and proposal identifiers and queue idempotent writes during transient network failures; provider content is not cached (D022).
7. EAS development/TestFlight build, real bundle identifier, and real app and notification icons.

Milestone 4 — notifications and private-cohort readiness — follows only after Milestone 3 is complete.
