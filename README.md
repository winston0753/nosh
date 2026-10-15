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

All local verification gates pass:
- 12 root spike tests
- 68 API unit tests (lint, format, strict mypy clean)
- 29 integration tests (PostGIS + real migrations + 4 concurrent DB tests) — **all pass**
- 36 mobile Jest tests (TypeScript, ESLint, Expo Doctor 18/18 clean)

Stack: FastAPI + SQLAlchemy 2 async API; Expo SDK 53 mobile app with Expo Router `~5.1.11`.

**Next:** complete Milestone 3 (see [Next milestone](#next-milestone)).

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
- Node.js 20+ and npm (for mobile)
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

```bash
uv run python -c "
import asyncio, os
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_dev')
os.environ['AUTH_LOCAL_DEV'] = 'true'
from app.config import get_settings
from app.places.service import load_fixture_data
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
async def run():
    e = create_async_engine(get_settings().async_database_url)
    factory = async_sessionmaker(e, class_=AsyncSession)
    async with factory() as db:
        await load_fixture_data(db)
    await e.dispose()
    print('20 fixture restaurants loaded.')
asyncio.run(run())
"
```

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
# Expected: 68 passed
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
# Expected: 29 passed (includes 4 genuine concurrent-DB tests)
```

In CI, GitHub Actions maps the postgres service container to port 5432 and sets `DATABASE_URL` accordingly in `ci.yml`.

The integration test fixture applies migrations automatically before the first test.

### Lint, format, and types

```bash
cd services/api
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
uv run mypy app/ --strict
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
npm test -- --runInBand # Jest unit tests (36 tests)
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
| 13 API endpoints | Implemented and type-checked |
| policy_v0 recommendation engine | Pure-function, deterministic, 13 unit tests |
| Fixture restaurants (20 places, SF Mission) | Loadable via seed command above |
| Go / Another / Not today state machine | Implemented with idempotency |
| Visit confirmation + rating + history + progress | Implemented |
| Strict mypy | 0 errors |
| Mobile app (Expo SDK 53, Expo Router `~5.1.11`) | All MVP screens; TypeScript + ESLint + 36 Jest tests + Expo Doctor pass |
| Integration tests | 29 tests covering full flow and concurrency; requires PostgreSQL |

## What is not yet complete

- **End-to-end local flow without Docker:** requires PostgreSQL running.
- **Mobile authentication (Milestone 3):** the app uses a local UUID adapter only; Supabase passwordless email sign-in is not implemented. The API also needs `SUPABASE_JWT_SECRET` for production auth.
- **Context setup (Milestone 3):** context creation hardcodes the SF Mission coordinate, a 1,600 m radius, and every active day; users cannot choose location, radius, or notification days.
- **Offline resilience (Milestone 3):** the current suggestion is not persisted for offline use, and idempotent response writes are not queued during transient network failures.
- **EAS/TestFlight build (Milestone 3):** not configured.
- **App icons (Milestone 3):** `apps/mobile/assets/icon.png` and `notification-icon.png` are 1×1 placeholders.
- **Notifications (Milestone 4, not started):** Expo push tokens, scheduler/worker, confirmation prompts.
- **API hosting vendor:** deferred per D012.

### Dependency audit (mobile, 2026-10-13)

| Command | Moderate | High | Critical | Total |
|---|---|---|---|---|
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
apps/mobile/          Expo SDK 53 React Native iOS-first client (Expo Router ~5.1.11)
services/api/         FastAPI modular monolith
  app/
    auth/             JWT validation; Supabase HS256 + local-dev UUID adapter
    contexts/         Dining context CRUD
    places/           Place catalog, PostGIS filtering, onboarding
    recommendations/  policy_v0 pure engine (Thompson sampling + weighted scoring)
    suggestions/      Session lifecycle, Go/Another/Not today state machine
    visits/           Confirmation, ratings, history, monthly progress
    core/             Database, errors, async engine
  alembic/            Migrations 0001–0004 (upgrade + downgrade tested)
  tests/
    test_auth.py                30 unit tests
    test_health.py              4 unit tests
    test_progress_metric.py     8 unit tests
    test_recommendations.py     13 unit tests (engine mechanics)
    test_suggestion_invariants.py  9 invariant tests
    test_state_machine.py       4 documentation tests
    test_integration.py         29 integration tests (PostgreSQL required)
jobs/                 Place ingestor scaffold
spike/                Cuisine-policy simulation (preserved, 12 tests)
tests/                Root spike tests
db/                   Docker init SQL (PostGIS; pgvector deferred per D013)
```

## Next milestone

**Complete Milestone 3 — Expo vertical slice (tester readiness)**

1. Supabase passwordless email authentication in the mobile app (replacing the local UUID adapter), with `SUPABASE_JWT_SECRET` configured for the API.
2. Location, radius, and notification-day selection during context creation.
3. Persist the current suggestion for offline use.
4. Queue idempotent response writes during transient network failures.
5. EAS development/TestFlight build configuration.
6. Real app and notification icons.

Milestone 4 — notifications and private-cohort readiness — follows only after Milestone 3 is complete.
