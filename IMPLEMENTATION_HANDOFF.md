# Nosh MVP Implementation Handoff for Claude

## Mission

Implement the phase-one Nosh MVP: an iOS-first app that gives a user one timely, nearby, unvisited restaurant recommendation; supports Go, Another, and Not today; opens Apple Maps; and later confirms whether the visit occurred and was positive.

## Read these first

Treat these root documents as authoritative, in this order:

1. `PRODUCT.md` — product requirements, features, edge cases, and non-goals
2. `DECISIONS.md` — accepted choices and rejected alternatives
3. `ARCHITECTURE.md` — stack, data model, APIs, state machine, and security
4. `RECOMMENDATIONS.md` — filters, scoring, feedback semantics, and evaluation

The material under `docs/` is historical research. Do not let it override the canonical root documents.

## Non-negotiable constraints

- Keep the backend a FastAPI modular monolith.
- Use Expo React Native with TypeScript for the mobile client.
- Use PostgreSQL with PostGIS; pgvector is deferred and absent in phase one (D013).
- Keep recommendation generation deterministic and independent of LLM calls.
- Count only confirmed, positively rated, previously unvisited restaurants toward the North Star.
- Treat Go as intent, not a visit.
- Treat Another as ambiguous weak feedback, not a strong cuisine rejection.
- Treat Not today only as timing feedback.
- Use Apple Maps for the phase-one handoff.
- Do not add delivery, ordering, background location, calendar access, social features, RAG, agents, or public-launch scope.
- Update the canonical documents in the same change whenever implementation changes a documented contract or decision.

## Status (as of 2026-10-16)

| Milestone | Status |
|---|---|
| 1 — Repository and backend foundation | **Complete** (merged to `main` via PR #1) |
| 2 — Deterministic suggestion API | **Complete** |
| 3 — Expo vertical slice | **Partially complete** — local vertical slice implemented; tester-readiness work remains |
| 4 — Notifications and private cohort readiness | Not started; not next (only the `device_tokens` and `notification_deliveries` tables exist) |

The current checkpoint is **Milestone 0.1 — Working Local Foundation**, merged to `main` through PR #1: the local database, migrations, API, recommendation engine, state machine, and mobile prototype work together. A correctness-hardening pass (onboarding provenance, honest visit confirmation, neutral priors, strict context validation, importer layout, atomic place-state writes) followed on branch `milestone-0.1-correctness-hardening`; see `notes.md` 2026-10-16. It is suitable for source control but not for TestFlight or external testers.

**Next: complete Milestone 3.** Remaining work:

1. Replace the local UUID auth adapter with Supabase passwordless email authentication in the mobile app.
2. Let users select location, radius, and notification days; context creation currently hardcodes the SF Mission coordinate, 1,600 m, and every day. Location defaults to foreground current location at use time with the saved anchor as fallback (D017); background location stays out of scope.
3. Persist the current suggestion for offline use.
4. Queue idempotent response writes during transient network failures.
5. Configure an EAS development/TestFlight build.
6. Replace the 1×1 placeholder app and notification icons.

Milestone 4 begins only after Milestone 3 is complete.

Do not recreate Milestones 1–2 or the existing Milestone 3 slice. Inspect Git state before modifying files, extend the existing code, and see `README.md` for current verification commands and `notes.md` for the dated implementation log. The milestone list below is kept as the original plan.

## Implementation order

### Milestone 1 — Repository and backend foundation

1. Create the directory structure described in `ARCHITECTURE.md`.
2. Preserve the existing simulator and tests.
3. Add FastAPI, Pydantic, SQLAlchemy, Alembic, database driver, linting, and type checking.
4. Add local Docker Compose PostgreSQL with PostGIS and pgvector enabled. *(Superseded by D013: pgvector is deferred and intentionally absent.)*
5. Implement configuration from environment variables and provide `.env.example` without secrets.
6. Add `/health/live`, `/health/ready`, and OpenAPI generation.
7. Create initial migrations for profiles, dining contexts, places, cuisines, place cuisines, user place states, suggestion sessions, proposals, responses, and visits.
8. Add CI checks for formatting, linting, typing, migrations, tests, and the existing simulator tests.

### Milestone 2 — Deterministic suggestion API

1. Import a small deterministic restaurant fixture.
2. Implement PostGIS radius filtering.
3. Implement the `policy_v0` eligibility and ranking rules from `RECOMMENDATIONS.md`.
4. Persist candidate snapshots, component scores, reason codes, context version, and policy version.
5. Implement idempotent suggestion-session creation.
6. Implement Go, Another, and Not today responses with the documented state transitions.
7. Implement visit confirmation, correction, rating, history, and progress endpoints.
8. Cover every required invariant with automated tests.

### Milestone 3 — Expo vertical slice

1. Scaffold the Expo TypeScript application.
2. Generate or wire a typed client from FastAPI OpenAPI.
3. Build passwordless sign-in, context setup, onboarding history, suggestion card, response actions, Maps handoff, confirmation, history, progress, and settings.
4. Cache the current suggestion and queue idempotent writes during transient connectivity failures.
5. Use a development build rather than relying on Expo Go for push behavior.

### Milestone 4 — Notifications and private cohort readiness

1. Register notification categories and device tokens.
2. Add an idempotent scheduler/worker using the same backend codebase.
3. Generate suggestions before sending notifications.
4. Deep-link actions to the stored session.
5. Add visit-confirmation notifications.
6. Verify time-zone, daylight-saving, duplicate-action, revoked-permission, and exhausted-candidate behavior.
7. Prepare separate development and TestFlight environments and document setup.

## First pull request (historical — completed)

The original instruction was to start with Milestone 1 only. That foundation now exists; these criteria remain the baseline every later change must preserve:

- the existing 12 tests still pass;
- the API boots locally;
- readiness proves the database connection;
- migrations apply to an empty database and can be rolled back safely;
- CI runs without application secrets;
- no phase-one non-goal has been introduced;
- `README.md` contains exact local setup and verification commands.

## Engineering expectations

- Prefer explicit domain types and small modules over framework abstractions.
- Keep route handlers thin; put workflows in application services and scoring in pure functions.
- Use transactions around state transitions.
- Make mobile-originated writes idempotent.
- Store timestamps in UTC and schedules with IANA time zones.
- Never log precise coordinates, tokens, or email addresses.
- Do not invent provider licensing rights or unavailable restaurant attributes.
- Add tests with each behavior, especially negative and retry paths.
- Do not rewrite or discard the existing simulation without a documented decision.

## Definition of MVP done

The MVP is complete when a private tester can:

1. sign in;
2. create a dining context;
3. classify initial places;
4. receive one valid suggestion;
5. choose Go, Another, or Not today;
6. open Apple Maps;
7. confirm or deny the visit later;
8. rate a confirmed visit;
9. view history and monthly positive-new-visit progress;
10. change notification settings or delete their account;
11. complete the flow without receiving a visited, excluded, inactive, out-of-radius, or repeated restaurant.

When an ambiguity conflicts with the canonical documents, stop and surface it as a proposed entry in `DECISIONS.md` rather than silently choosing a new product direction.
