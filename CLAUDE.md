# Nosh Implementation Brief

You are continuing the phase-one Nosh MVP in this repository.

Nosh is an iOS-first app that proactively suggests one specific dish at a specific restaurant branch on the user's meal schedule, then confirms what the user actually ate and whether they enjoyed it.

**The code today is still the earlier restaurant-shaped prototype.** It suggests one nearby restaurant, not a dish. None of the dish-first decisions (D032–D043 in `DECISIONS.md`) is implemented. Never describe a planned feature as if it exists.

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

Root documents are canonical. Files under `docs/` are historical research. `DECISIONS.md` explains how to read each decision's status line (Implemented, Accepted (not implemented), Proposed, Superseded, Amended).

## Current state (as of 2026-11-10)

`main` is at `8422298`. PRs #1–#6 are merged; no open PRs are known. The local foundation works end to end for restaurants. It is **not** ready for TestFlight or external testers. Start with "Where the last session left off" in `IMPLEMENTATION_HANDOFF.md`.

This section has three separate parts. Keep them separate when you write about the project.

### 1. Implemented today (restaurant-shaped)

**Do not recreate the backend, database, migrations, API, or Expo foundation. Extend what exists.**

- **Backend:** FastAPI modular monolith in `services/api/` (own uv project, `nosh-api`), SQLAlchemy 2 async + asyncpg, Alembic migrations `0001`–`0005`, `/health/live`, `/health/ready`, and OpenAPI. A deterministic `policy_v0` restaurant engine ranks 20 fictional San Francisco fixture places. Per-user meal schedule and Home/Work anchors; suggestion sessions keyed by user and meal window with Go / Another / Not today / Been here already; restaurant visit confirmation, rating, correction, history, progress, and product-data deletion. Nothing in the code models a dish.
- **Database:** Docker Compose PostGIS 16-3.4. `db` (port 5432, `nosh_dev`) is persistent development data; `db_test` (port 5433, `nosh_test`, `--profile test`) is disposable. pgvector is intentionally absent (D013).
- **Mobile:** Expo SDK 58 app in `apps/mobile/` with Expo Router `~58.0.26`, React Native 0.88, React 19.3, strict TypeScript, TanStack Query, and Supabase email-code sign-in. Every session is anchored at a hard-coded San Francisco placeholder location, and Go opens Apple Maps. Do not upgrade or downgrade Expo, React Native, or Expo Router without a recorded decision.
- **Jobs:** batch jobs live in `services/api/jobs/` and import the app as `app`; run from `services/api` with `uv run --frozen python -m jobs.ingest_places.importer`.
- **Notifications:** two tables only (`device_tokens`, `notification_deliveries`). There is no worker and no device route.
- **Tests:** run the checks in `README.md` for current results. Do not rely on test counts written anywhere.

Still decided and unchanged: bundle identifier `com.winstontang.nosh` (D029); Fly.io with Supabase Postgres (D030, not deployed); private cohort (D009); no background location (D010; D017 as amended by D035).

### 2. Accepted but not implemented (the dish-first pivot, 2026-11-10)

Two parts are not yet agreed: the budget (D043 is open) and the one-home-country rule in D039 (proposed).

- **D032 — Unit:** one dish at one restaurant branch, suggested proactively on the meal schedule.
- **D033 — North Star:** confirmed personally-new dishes tried per active user. "Tried" and "enjoyed" are separate signals; enjoyment rate is a guardrail.
- **D034 — Supply:** a published dish-offering index built offline (sources → adapters → branch match → source-backed menu items → catalog mapping → review → published offering). Three data classes kept apart: shared catalog, provider content (tagged with source, retrieval date, and expiry), and personal data. Google content other than place IDs is not stored.
- **D035 — Meal area:** the user confirms a coarse meal area per meal, stored as a coarse cell, never a point. A notification names a dish only when a meal area exists.
- **D036 — Legacy data:** restaurant visits and place states become read-only history. No dish backfill, no retrospective rewards. "Been here" becomes a familiarity signal only.
- **D037 — Sessions:** Go is final for the window. The system may supersede only unanswered proposals, recorded separately from user responses. An accepted proposal is never silently replaced.
- **D038 — Confirmation:** one commit per request; confirming a meal writes the dish experience, checks novelty under a per-user lock, and inserts rewards idempotently. Corrections are appended events.
- **D039 — Rewards:** a cosmetic unlocks only for a dish from a country new to the user; the avatar is computed from valid rewards. The one-home-country-per-dish rule is **Proposed, awaiting confirmation** — do not build on it.
- **D040 — Catalog identity:** dish, variant (one level), alias. Only dishes and variants have IDs, and IDs are permanent. Every fact is marked generated, reviewed, or source-backed.
- **D041 — LLM boundary:** LLMs offline only, each use with its own evaluation set. No LLM call at meal time.
- **D042 — Pilot:** downtown San Mateo is the first hand-verified offering index. A source-comparison experiment runs in parallel; no source is selected.
- **D043 — Budget:** open. No figure is agreed.

### 3. Historical or superseded

Kept as history only; do not build on them:

- D002 (restaurant North Star), D021 (Google Places end to end), D022 (store only provider IDs, except its rule about Google content), D023 (location-free nudges, except as the no-meal-area fallback), D024 (`policy_v1`, never built), D027 (curated-catalog retirement), D028 (~$50/month budget), and D031 (cuisine labels from place types, never built). Older entries such as D007, D008, D010, and D016 are also partly replaced; `DECISIONS.md` status lines are the full record.
- The old Milestone 3 ("Expo vertical slice") and Milestone 4 ("Notifications and private cohort readiness") plan. Its unfinished tester-readiness items (offline write queue, EAS/TestFlight build, real icons) and the Fly.io deployment have no agreed place in the new order yet (DECISIONS.md open question 19).

## Next: the dish-first milestones

All seven are **not started**. See `IMPLEMENTATION_HANDOFF.md` for detail.

1. Catalog schema, identity rules, seed, evaluation set.
2. Branch and offering tables with the San Mateo hand-verified index; source experiment in parallel.
3. Dish onboarding and profile.
4. Dish ranking with an additive proposals migration.
5. Single-commit refactor, dish experience, rewards.
6. Notification worker and meal area.
7. Minimal journal and avatar.

First target: one complete loop — dish onboarding → dish-and-restaurant recommendation → scheduled delivery → actual-dish confirmation → immediate discovery reward → updated profile and minimal avatar/journal.

Start any of this work only when the user asks, and keep each change reviewable. Unsettled items are listed under "Open questions" in `DECISIONS.md`. Ask the user about them; do not decide them silently.

## Non-negotiable rules

Rules about unbuilt behaviour are rules for future work. They do not describe the current code.

- Expo React Native with strict TypeScript for mobile.
- FastAPI modular monolith for the backend.
- PostgreSQL with PostGIS; no pgvector (D013).
- No microservices, graph database, vector service, or event platform (D041).
- The recommendation unit is a dish at a specific restaurant branch (D032).
- Meal-time ranking is deterministic and versioned, with no LLM call. LLMs may be used offline only, each use with its own evaluation set (D041).
- Ranking reads only the published offering index. Live place status and opening hours can make an offering ineligible; they never establish that a restaurant serves a dish (D034).
- Keep the three data classes (shared catalog, provider content, personal data) apart. Tag provider content with its source, retrieval date, and expiry. Never store Google content other than place IDs (D034).
- Go is intent, not a meal, and is final for the meal window (D037).
- The system never silently replaces an accepted proposal (D037).
- Tried and enjoyed are separate signals. Only confirmed personally-new dishes count toward the North Star (D033).
- One commit per request. Corrections are appended events, never overwrites. Rewards are inserted idempotently (D038).
- A cosmetic unlocks only for a new country, and the avatar is computed from valid rewards (D039).
- Catalog IDs are permanent (D040).
- Legacy restaurant visits and place states are read-only history: no dish backfill and no retrospective rewards (D036).
- The meal area is a coarse cell, never a point. No background location (D035, D010).
- A notification names a dish only when a meal area exists (D035).
- Another and Not today are not strong taste rejections in the existing restaurant code (D011). What they mean for dishes is an open question.
- No delivery, ordering, calendar access, RAG, agents, or public-launch work.
- Nosh Meals and social features are future extension points only: no tables, services, or infrastructure for them.
- Mobile writes must be idempotent.
- Never log precise coordinates, access tokens, or email addresses.
- Do not invent provider licensing rights, prices, or coverage.
- Update the canonical documents and `notes.md` when implementation changes a documented contract or completes a material milestone.

## Engineering style

- Prefer pure functions for recommendation logic.
- Keep route handlers thin and workflows in application services.
- Use explicit domain types and stable machine-readable error codes.
- Store timestamps in UTC and schedules with IANA time zones.
- Add tests for negative, retry, ownership, and duplicate-event paths.
- Preserve existing user work and the cuisine-policy simulator.
- Run destructive migration tests only against the disposable test database (port 5433); only ever `upgrade` the development database.
- Make dish-first schema changes additive so legacy restaurant data stays readable (D036).
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
- phase-one non-goals remain absent, and future extension points (Nosh Meals, social) have no tables, services, or infrastructure.

## Default objective-driven orchestration

For substantive repository tasks, the main conversation acts as the Fable supervisor. Delegate research, implementation, testing, and independent review to Opus subagents automatically, without requiring me to request delegation each time.

The supervisor owns:
- Understanding the objective and identifying acceptance criteria.
- Decomposing the work into bounded assignments.
- Resolving architectural decisions and conflicting findings.
- Maintaining continuity, reviewing evidence, and reporting the outcome.

Workers own the assigned investigation, implementation, or verification.

For each substantive task:
1. Establish the objective, constraints, and observable completion criteria.
2. Inspect existing work before assigning changes.
3. Delegate execution to at least one Opus subagent. Give each assignment a clear scope, expected output, and relevant context.
4. Parallelize independent work only. Prevent simultaneous edits to the same files unless explicitly coordinated.
5. Have workers report findings, changes, verification evidence, and unresolved issues.
6. Use a fresh Opus reviewer for material implementation changes.
7. Evaluate the evidence before declaring completion. Continue resolving issues within the authorized scope.
8. Maintain a concise work-plan record for longer tasks, including decisions, completed work, and next steps.

Use ordinary subagents for workers. Avoid forks or inheriting agents that would run on Fable.

Use only as many workers as the task needs, normally no more than three concurrently. Simple conversational answers can remain in the main conversation.

For architecture-review requests, workers investigate and assess; they do not implement unless implementation is part of my request.

Report the delegation briefly: assignment, worker role, result, and verification. Do not claim delegation or testing that did not occur.
