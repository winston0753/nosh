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

All local verification gates pass (2026-10-16, after the correctness-hardening pass):
- 12 root spike tests
- 148 API unit tests (lint, format, strict mypy clean)
- 46 integration tests (PostGIS + real migrations + 6 concurrent DB tests) — **all pass**
- 43 mobile Jest tests (TypeScript, ESLint, Expo Doctor 18/18 clean)

Stack: FastAPI + SQLAlchemy 2 async API; Expo SDK 58 mobile app (React Native 0.88, Expo Router `~58.0.24`).

**Next:** complete Milestone 3 (see [Next milestone](#next-milestone)). On 2026-10-20 the product direction changed to current-location-first with live Google Places data (DECISIONS.md D019–D028); the code below still reflects the earlier design.

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
  http://localhost:8000/v1/contexts
```

---

## Mobile local setup

```bash
cd apps/mobile
npm ci
echo "EXPO_PUBLIC_API_URL=http://localhost:8000" > .env.local
npx expo start
# Press 'i' for iOS simulator
```

Sign in with any UUID string (local dev adapter).

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
# Expected: 148 passed
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
# Expected: 46 passed (includes 6 genuine concurrent-DB tests)
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
npm test -- --runInBand # Jest unit tests (43 tests)
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
| 16 API routes (`/v1`) | Implemented and type-checked |
| policy_v0 recommendation engine | Pure-function, deterministic, 13 unit tests |
| Fixture restaurants (20 places, SF Mission) | Loadable via seed command above |
| Go / Another / Not today state machine | Implemented with idempotency |
| Visit confirmation + rating + history + progress | Implemented |
| Strict mypy | 0 errors |
| Mobile app (Expo SDK 58, Expo Router `~58.0.24`) | All MVP screens; TypeScript + ESLint + 43 Jest tests + Expo Doctor (20/20) pass |
| Integration tests | 46 tests covering full flow, provenance, validation, replay, pagination, and concurrency; requires PostgreSQL |
| Place importer | `uv run --frozen python -m jobs.ingest_places.importer` from `services/api` |

## What is not yet complete

- **End-to-end local flow without Docker:** requires PostgreSQL running.
- **Mobile authentication (Milestone 3):** the app uses a local UUID adapter only; Supabase passwordless email sign-in is not implemented. The app will need only the Supabase project URL and publishable key; the API needs `SUPABASE_URL` and verifies tokens against the project JWKS (no shared JWT secret for new projects).
- **Meal schedule and location (Milestone 3):** context creation hardcodes the SF Mission coordinate, a 1,600 m radius, and every active day; D020 replaces dining contexts with a meal schedule and current location.
- **Place data (Milestone 3):** suggestions use 20 fictional fixture places; D021 moves to live Google Places data.
- **Offline resilience (Milestone 3):** session identifiers are not persisted, and idempotent response writes are not queued during transient network failures.
- **EAS/TestFlight build (Milestone 3):** not configured.
- **App icons (Milestone 3):** `apps/mobile/assets/icon.png` and `notification-icon.png` are 1×1 placeholders.
- **Notifications (Milestone 4, not started):** Expo push tokens, scheduler/worker, confirmation prompts.
- **API hosting vendor:** deferred per D012.

### Dependency audit (mobile, 2026-10-21, Expo SDK 58)

| Command | Moderate | High | Critical | Total |
|---|---|---|---|---|
| `npm audit` | 25 | 28 | 0 | 53 |
| `npm audit --omit=dev` | 7 | 19 | 0 | 26 |

The findings reach the app through `expo`, `react-native`, and `jest-expo`. The only remedies npm proposes are semver-major downgrades (`expo@44`, `react-native@0.72`, `jest-expo@56`), so `npm audit fix` / `--force` has deliberately not been run. On SDK 53 (2026-10-13) the counts were 60 total and 37 production.

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
apps/mobile/          Expo SDK 58 React Native iOS-first client (Expo Router ~58.0.24)
services/api/         FastAPI modular monolith
  app/
    auth/             Supabase JWT validation (JWKS RS256/ES256; legacy HS256) + local-dev UUID adapter
    contexts/         Dining context CRUD
    places/           Place catalog, PostGIS filtering, onboarding
    recommendations/  policy_v0 pure engine (Thompson sampling + weighted scoring)
    suggestions/      Session lifecycle, Go/Another/Not today state machine
    visits/           Confirmation, ratings, history, monthly progress
    core/             Database, errors, async engine
  jobs/               Batch jobs in the API project (ingest_places importer)
  alembic/            Migrations 0001–0004 (upgrade + downgrade tested)
  tests/
    test_auth.py                30 unit tests
    test_context_validation.py  70 unit tests (schedule + meal-window rules, API 422s)
    test_health.py              4 unit tests
    test_job_imports.py         3 unit tests (job import-path guard)
    test_priors.py              7 unit tests (cuisine prior provenance)
    test_progress_metric.py     8 unit tests
    test_recommendations.py     13 unit tests (engine mechanics)
    test_suggestion_invariants.py  9 invariant tests
    test_state_machine.py       4 documentation tests
    test_integration.py         46 integration tests (PostgreSQL required)
spike/                Cuisine-policy simulation (preserved, 12 tests)
tests/                Root spike tests
db/                   Docker init SQL (PostGIS; pgvector deferred per D013)
```

## Next milestone

**Complete Milestone 3 — Expo vertical slice (tester readiness)**, following the 2026-10-20 decisions (evidence in `docs/research/2026-10-20-place-data-and-map-terms.md`):

1. ~~Upgrade Expo SDK 53 → 58 (D019)~~ — done 2026-10-21; App Store Connect requires Xcode 26 builds.
2. Supabase passwordless email authentication in the mobile app (replacing the local UUID adapter), configured with the project URL and publishable key; the API validates tokens via `SUPABASE_URL` + JWKS.
3. Meal schedule (weekday lunch default, dinner opt-in), per-meal price ceiling, and optional Home/Work fallback spots replace dining contexts (D020, D026).
4. Live Google Places candidates behind a place-provider abstraction (fixtures in tests), `policy_v1` ranking, and Been here already (D021, D022, D024, D025).
5. Foreground current location at open time, a Google map on the card, and Google Maps handoff. No background location.
6. Persist session and proposal identifiers and queue idempotent writes during transient network failures; provider content is not cached (D022).
7. EAS development/TestFlight build, real bundle identifier, and real app and notification icons.

Milestone 4 — notifications and private-cohort readiness — follows only after Milestone 3 is complete.
