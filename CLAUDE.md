# Nosh Implementation Brief

You are continuing the phase-one Nosh MVP in this repository.

Nosh is an iOS-first restaurant-discovery app that presents one timely, nearby, unvisited restaurant; supports **Go**, **Another**, and **Not today**; opens Apple Maps; and later confirms whether the visit happened and was positive.

## Before you change anything

1. Inspect Git state first: `git status --short`, `git diff`, and relevant untracked files. Earlier sessions may have left uncommitted work, including partially finished changes. Determine what is already done before editing.
2. Preserve existing user work. Do not use `git reset`, `git checkout --`, `git clean`, or delete or revert files unless the user explicitly asks.
3. Do not commit, stage, or push unless the user asks.
4. Re-run the checks in `README.md` rather than trusting counts written in documents.

## Source of truth

Read these before changing code:

1. `PRODUCT.md` — requirements, MVP scope, edge cases, and non-goals
2. `DECISIONS.md` — accepted product and technical choices
3. `ARCHITECTURE.md` — stack, data model, APIs, and system boundaries
4. `RECOMMENDATIONS.md` — filtering, ranking, feedback, and evaluation
5. `IMPLEMENTATION_HANDOFF.md` — milestone sequence, status, and MVP definition of done
6. `notes.md` — dated implementation log (newest first); older entries are historical

Root documents are canonical. Files under `docs/` are historical research.

## Current state (as of 2026-10-16)

Checkpoint: **Milestone 0.1 — Working Local Foundation**, merged to `main` via PR #1, plus a correctness-hardening pass (branch `milestone-0.1-correctness-hardening`; see `notes.md` 2026-10-16). The local database, migrations, API, recommendation engine, state machine, and mobile prototype work together. This is suitable for source control; it is **not** ready for TestFlight or external testers.

| Milestone | Status |
|---|---|
| 1 — Repository and backend foundation | Complete |
| 2 — Deterministic suggestion API | Complete |
| 3 — Expo vertical slice | **Partially complete** — local vertical slice implemented; tester-readiness work remains |
| 4 — Notifications and private cohort readiness | Not started; not next |

**Do not recreate the backend, database, migrations, API, or Expo foundation.** Extend what exists.

- **Backend:** FastAPI modular monolith in `services/api/` (own uv project, `nosh-api`), SQLAlchemy 2 async + asyncpg, Alembic migrations `0001`–`0004`, `/health/live`, `/health/ready`, OpenAPI, deterministic `policy_v0` engine, suggestion sessions with Go / Another / Not today, visit confirmation, rating, correction, history, progress, and product-data deletion.
- **Database:** Docker Compose PostGIS 16-3.4. `db` (port 5432, `nosh_dev`) is persistent development data; `db_test` (port 5433, `nosh_test`, `--profile test`) is disposable. pgvector is intentionally absent (D013).
- **Mobile:** Expo SDK 53 app in `apps/mobile/` with Expo Router `~5.1.11`, React Native 0.79, strict TypeScript, TanStack Query, and Apple Maps handoff. Do not upgrade or downgrade Expo, React Native, or Expo Router without a recorded decision.
- **Jobs:** batch jobs live in `services/api/jobs/` and import the app as `app`; run from `services/api` with `uv run --frozen python -m jobs.ingest_places.importer`.
- **Contracts added by the hardening pass:** onboarding classification via `PUT /v1/contexts/{context_id}/onboarding-places/{place_id}/state` (D018); strict context/meal-window validation with `422 validation_error` (D016); atomic `user_place_states` upserts; replay-equivalent responses; `(visited_at, id)` visit pagination.
- **Tests:** 12 root spike tests, 148 API unit tests, 46 PostgreSQL integration tests (including 6 genuine concurrent-database tests), and 43 mobile Jest tests.

## Next: complete Milestone 3

Milestone 3 remains incomplete because:

1. Mobile authentication is only a local UUID adapter; Supabase passwordless email authentication is not implemented in the app.
2. Context creation hardcodes the SF Mission coordinate, a 1,600-meter radius, and every active day; users cannot select location, radius, or notification days as `PRODUCT.md` requires. Location should default to foreground current location at use time with the saved anchor as fallback (D017); background location remains banned.
3. The current suggestion is not persisted for offline use.
4. Idempotent response writes are not queued during transient network failures.
5. No EAS development/TestFlight build is configured.
6. The app and notification icons are 1×1 placeholders.

Milestone 4 (notifications and private-cohort readiness) has not started beyond the `device_tokens` and `notification_deliveries` tables and must not begin until Milestone 3 is complete. Start any of this work only when the user asks, and keep each change reviewable.

## Non-negotiable rules

- Expo React Native with strict TypeScript for mobile.
- FastAPI modular monolith for the backend.
- PostgreSQL with PostGIS; pgvector is deferred and absent in phase one (D013).
- Deterministic, versioned recommendation code with no LLM dependency in the meal-time path.
- Go is intent, not a visit.
- Another is ambiguous weak feedback, not a strong cuisine rejection.
- Not today is timing feedback only.
- Only confirmed, positively rated, previously unvisited restaurants count toward the North Star.
- Maps-only handoff in phase one.
- No delivery, ordering, background location (foreground use-time location only, D017), calendar access, social features, RAG, agents, or public-launch work.
- Mobile writes must be idempotent; state transitions must be transactional.
- Never log precise coordinates, access tokens, or email addresses.
- Update the canonical documents and `notes.md` when implementation changes a documented contract or completes a material milestone.

## Engineering style

- Prefer pure functions for recommendation logic.
- Keep route handlers thin and workflows in application services.
- Use explicit domain types and stable machine-readable error codes.
- Store timestamps in UTC and schedules with IANA time zones.
- Add tests for negative, retry, ownership, and duplicate-event paths.
- Preserve existing user work and the cuisine-policy simulator.
- Run destructive migration tests only against the disposable test database (port 5433); only ever `upgrade` the development database.
- If a required choice is unclear, propose an entry in `DECISIONS.md` instead of silently expanding scope.

## Change completion check

A change is ready for review only when:

- all existing tests still pass, including integration tests against `db_test`;
- ruff lint and format, strict mypy, and `alembic check` pass;
- mobile TypeScript, ESLint, Jest, `npx expo install --check`, and `npx expo-doctor` pass;
- migrations apply to an empty database and have a tested rollback path;
- CI runs without application secrets;
- `git diff --check` passes;
- `README.md` commands remain reproducible;
- phase-one non-goals remain absent.
