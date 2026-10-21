# Project Notes

## 2026-10-21 — Expo SDK 53 → 58 (D019, branch `expo-sdk-58`)

Started from `main` at `72bb0fb` (PR #2 merged, CI green including the new `alembic check` step). Not committed.

### Correction
D019 recorded SDK 57 as the latest release. The npm registry shows SDK 58.0.0 shipped on 2026-09-29 (`latest` = 58.0.16), so the upgrade continued to 58 and D019 now says so.

### Steps
Each step pinned `expo`, applied every version from `npx expo install --check`, and reran typecheck, ESLint, Jest, and Expo Doctor.
- **54** — all green (Doctor 18/18). A partial `expo install --fix` failed with an `@types/react` peer conflict and was resolved by setting all expected versions at once.
- **55** — all green (Doctor 20/20).
- **56** — Doctor flagged the known Hermes V1 memory regression (fixed in SDK 57). The updated `eslint-config-expo` added React Compiler `react-hooks/refs` rules: 4 errors in `useVisitConfirmation.ts`, which read `requestRef.current` during render.
- **57** — Doctor 21/21. Fixed the lint errors: the displayed rating now falls back to `mutation.variables?.rating` (the frozen request last sent) instead of the ref, and refs are only read in handlers. A clean `npm ci` then failed: Expo's optional `react-dom` peer resolved to 19.3.1, which conflicts with React 19.2.3. `react-dom` is now pinned to the React version, and the lockfile was regenerated with a strict install.
- **58** — expo 58.0.16, React Native 0.88.0, Expo Router 58.0.24, React 19.3.0, TypeScript 6.0. `jest-expo` 58 no longer installs `react-test-renderer`, so the confirmation-screen suite failed to load. It is now an explicit exact dev dependency (19.3.0). Migrating to `@testing-library/react-native` 14 is a possible follow-up.

### Verification (actual results, SDK 58)
| Check | Result |
|---|---|
| `rm -rf node_modules && npm ci` | ✅ (no `--legacy-peer-deps`) |
| `npm run typecheck`, `npm run lint` | ✅ |
| Jest | ✅ 43 passed (2 suites) |
| `npx expo install --check` | ✅ Dependencies are up to date |
| `npx expo-doctor` | ✅ 20/20 |
| `npm audit` | 53 (25 moderate, 28 high, 0 critical) |
| `npm audit --omit=dev` | 26 (7 moderate, 19 high, 0 critical) |

SDK 58 requires Node `^22.13.0` or `^24.3.0`; CI's `node-version: "22"` resolves to the latest 22.x. No backend, migration, or `app.json` changes.

## 2026-10-20 — Audit, architecture review, and direction change (docs only)

Started from branch `milestone-0.1-correctness-hardening` with the 2026-10-16 hardening pass still uncommitted (31 modified files, root `jobs/` deleted, new tests and modules untracked). No application code, dependencies, or migrations were changed; the development database was not touched. The hardening pass was then committed alone as `109b124` (staged from reconstructed pre-edit document versions so these document changes stay separate); these document changes are not committed.

### Audit findings
- **Expo SDK 53 cannot ship to TestFlight as is:** App Store Connect has required Xcode 26 / iOS 26 SDK builds since 2026-04-28; Expo recommends SDK 54+. Latest is SDK 57 (React Native 0.86).
- **Stale documents (fixed here):** ARCHITECTURE listed `DELETE /v1/me` (actual `DELETE /v1/me/product-data`) and unbuilt device routes without marking them; README said 13 endpoints (16 routes exist), described auth as HS256 only (JWKS is implemented), and required Node 20 (end of life); ARCHITECTURE claimed an OpenAPI-generated client (`packages/api-client/` is empty) and Python 3.12+ (`requires-python` is 3.11+); CI lacked `alembic check`.
- **Code issues confirmed (not fixed; addressed by the planned work):** `highly_rated` comes from fictional `quality_score`; cuisine sampling depends on candidate order and the radius query sorts only by distance; `exclusion_counts` is always empty; `context_fit` ignores meal type; TanStack query keys are not scoped per user; `mutations: { retry: 1 }` applies to non-idempotent context creation; Another reads current context settings; disabled contexts can open sessions.

### Decisions (D019–D028)
- **D019** upgrade Expo SDK 53 → 57.
- **D020** current location first; a meal schedule (weekday lunch default, dinner opt-in) and optional Home/Work fallback spots replace dining contexts.
- **D021** Google Places end to end: live candidates and signals, Google map and attribution, Go opens Google Maps (supersedes D007's Apple Maps handoff and D008's curated catalog).
- **D022** persist only provider IDs and Nosh-owned data.
- **D023** notifications are location-free nudges.
- **D024** `policy_v1`: quality floor, hidden-gem boost, price fit, national-chain penalty, deterministic ordering.
- **D025** Been here already on the card replaces bulk onboarding classification.
- **D026** per-meal price ceiling, no spend tracking.
- **D027** curated-catalog plan retired.
- **D028** ~$50/month budget.

Evidence and quotations are in `docs/research/2026-10-20-place-data-and-map-terms.md`. In short, Apple MapKit and the Apple Maps Server API have no ratings, hours, or price. Google forbids using Places content with a non-Google map (Service Specific Terms §14.2). Foursquare forbids co-mingling its ranking signals with Nosh's own (Master Terms §7.5.7). Yelp starts at $229/month. Overture has no ratings or hours.

### Documents changed
DECISIONS (D007, D008, D017, and D018 statuses; D019–D028), PRODUCT (summary, principle 6, journey, F2–F8, F11, edge cases, non-goals), ARCHITECTURE (stack, layout, components, planned schema, endpoints, notifications, new §17 provider terms), RECOMMENDATIONS (`policy_v1` notice and known `policy_v0` defects), IMPLEMENTATION_HANDOFF and CLAUDE/AGENTS (kept identical; direction change and the new Milestone 3 order), README, and CI (`alembic check` step; Node 22). The 2026-10-19 report moved from `reports/` to `docs/research/` and is marked superseded.

### Open questions
- How a visit's cuisine label is captured for cuisine learning without storing Google-derived data. Recommended: the rating step asks the user to confirm a pre-filled cuisine.
- The real iOS bundle identifier (`com.nosh.app` is a placeholder).
- Whether Google's "modify search results" clause (ToS §3.2.3(g)) covers filtering and re-ranking. Clarify with Google before any public launch.
- Untracked `.agents/`, `skills-lock.json`, `research_notes/`, and two unrelated files in `reports/` are not project material and remain uncommitted.

## 2026-10-16 — Correctness hardening (branch `milestone-0.1-correctness-hardening`)

Started from `main` at `de67821` (PR #1 merged), clean tree, synchronized with `origin/main`. Every finding below was reproduced before it was changed. Not committed.

### Reproduced findings
- Onboarding called `PUT /v1/places/{id}/state`, which always wrote `source=manual`, so `was_visited_before_nosh` stayed FALSE; a later Nosh visit to the same restaurant counted as a North Star "new" visit.
- Confirmation set its rating state before `createVisit` resolved and `onSuccess` navigated away, so "Thanks" never reflected the server; each attempt built a new `visited_at`.
- A user with no onboarding history got `Beta(1, 5)` (default `history_frequency=0.0`), not the documented `Beta(1, 1)`; history was built from every `state='visited'` row, double-counting post-Nosh visits as history and as outcomes, and manual visits updated cuisine preference contrary to D015.
- Contexts accepted `25:99`, unknown zones, `[0, 0, 9]`, overnight and empty windows; sessions accepted `2026-02-30#lunch` for a dinner context.
- `python -m jobs.ingest_places.importer` failed: `ModuleNotFoundError: No module named 'app'` (mixed `services.api.app` and `app` imports).
- Unknown place IDs raised an FK `IntegrityError` (500). First-time place-state writes were SELECT-then-INSERT: 29 of 30 concurrent rounds failed with a primary-key `IntegrityError`. Visit pagination used `visited_at <` only, skipping timestamp ties. Replaying Another returned `next_proposal: null`.

### Changes
- **Onboarding provenance (D018):** new `PUT /v1/contexts/{context_id}/onboarding-places/{place_id}/state` records `source=onboarding`; Been sets `was_visited_before_nosh` permanently; place must be active and within the context radius (`422 place_not_in_context`). The manual endpoint never sets the flag. Responses now include `was_visited_before_nosh`. Mobile onboarding uses the new endpoint.
- **Atomic place states:** `upsert_user_place_state` is one `INSERT … ON CONFLICT DO UPDATE` that ORs the provenance flag; used by onboarding, manual edits, and visit confirmation (duplicate helper in visits removed).
- **Stable errors:** unknown places → `404 not_found` (place-state and visit endpoints). Schema validation now returns `{"code": "validation_error", "message", "field", "detail": [...]}` (FastAPI's list kept under `detail`); `NoshError` carries an optional `field`.
- **Context validation (D016):** `app/contexts/validation.py` (pure). Create and update validate strict `HH:MM`, loadable IANA zones, unique `StrictInt` days 0–6, end strictly after start (overnight still rejected); PATCH re-checks against the stored bound. Session creation checks key date, meal type, active weekday, and the stored schedule.
- **Priors:** `app/recommendations/priors.build_cuisine_stats` (pure). `history_frequency=None` means no history → `Beta(1, 1)`; history only from `was_visited_before_nosh`; outcomes only from proposal-backed visits. Kept as `policy_v0` because this restores the documented policy; earlier sessions created with the buggy prior are not replayable bit-for-bit (dev data only).
- **Responses:** `record_response` returns `RecordedResponse`; replays reconstruct the original result (Another → the proposal it generated at sequence + 1, or `exhausted`).
- **Pagination:** `(visited_at DESC, id DESC)` with a tuple keyset cursor.
- **Importer:** moved from root `jobs/` to `services/api/jobs/` (same uv project and `app` package); supported invocation documented in README; CI ruff/mypy now cover `jobs/`.
- **Confirmation screen:** `useVisitConfirmation` freezes the request on first tap; phases choosing → saving → saved/failed; "Thanks" only on server success (showing the stored rating); retry re-sends the identical body; double taps send once; a link without `proposalId` refuses to write.
- **Docs:** ARCHITECTURE (contracts, auth, pgvector, layout), DECISIONS (D005 wording, D016–D018), PRODUCT (F2/F3), RECOMMENDATIONS (prior provenance), IMPLEMENTATION_HANDOFF (merged status), AGENTS/CLAUDE (kept identical), README, root `.env.example`. Supabase: mobile uses project URL + publishable key; API verifies via JWKS with no shared secret; HS256 secret is legacy-only.

### Tests added or changed
- API unit: `test_context_validation.py` (70), `test_priors.py` (7), `test_job_imports.py` (3).
- Integration (+17): same-restaurant onboarding → Nosh visit excluded from progress; provenance survives reclassification/manual edits; manual edit never sets the flag; onboarding negative paths (404/403/422); unknown place 404; stats with no history / onboarding history / later positive, negative, and manual visits; PATCH window merge; session key consistency; legacy invalid contexts; pagination ties; cursor ownership; Another replay (immediate, other event ID, after the session moved on, after exhaustion, other user); two 10-round concurrency tests for first-time place-state writes.
- Changed: `test_session_key_format_accepted` now uses matching meal types (mismatches are rejected by design); `test_progress_excludes_pre_nosh_onboarding_place` uses the onboarding endpoint; concurrency tests use `RecordedResponse`.
- Mobile: `src/__tests__/confirmationScreen.test.tsx` (7) with local `react-test-renderer` typings. Against the original code, 11 of 12 targeted integration tests and 6 of 7 mobile tests fail.

### Verification (actual results)
| Check | Result |
|---|---|
| Root `uv lock --check`; spike tests | ✅ 12 passed |
| API `uv lock --check` | ✅ |
| `ruff check app/ jobs/ tests/`; `ruff format --check` | ✅ All checks passed; 58 files formatted |
| `mypy app/ jobs/ --strict` | ✅ 46 source files, no issues |
| API unit tests | ✅ 148 passed, 46 deselected |
| `alembic downgrade base` → `upgrade head` → `check` (5433 only) | ✅ "No new upgrade operations detected"; head 0004 |
| Integration + concurrency (5433) | ✅ 46 passed |
| Importer via documented invocation (5433) | ✅ "Fixture data loaded." |
| Mobile `npm ci`, typecheck, ESLint | ✅ |
| Jest | ✅ 43 passed (2 suites) |
| `npx expo install --check` | ✅ Dependencies are up to date |
| `npx expo-doctor` | ✅ 18/18 |
| `git diff --check` | ✅ |

No migrations were added. The development database (5432) was not modified.

### Open questions
- Should session keys be bounded to a window around "today" in the context zone? Not enforced (D016).
- Onboarding Been is irreversible by design (D018); a mistaken tap needs an audited admin correction path.
- A place classified Been after it was already confirmed through Nosh also becomes pre-Nosh, removing that North Star credit.
- An untracked `research_notes/` directory appeared during the session; it was not created or modified by this work.

## 2026-10-13 — Milestone status correction

The earlier corrective pass overstated progress by naming Milestone 4 as next. Corrected status: Milestones 1–2 complete; Milestone 3 partially complete (local vertical slice implemented; Supabase passwordless auth, location/radius/day selection, offline suggestion persistence, queued idempotent writes, EAS/TestFlight build, and real icons remain); Milestone 4 not started and not next. The checkpoint stays **Milestone 0.1 — Working Local Foundation**: suitable for source control, not for TestFlight or external testers. Mobile `npm audit`: 60 findings (16 moderate, 44 high); `--omit=dev`: 37 (16 moderate, 21 high); no critical; `npm audit fix` not run. Documentation only; no runtime or dependency changes.

## 2026-10-13 — Corrective pass: agent handoff, docs, and conflict contract

An earlier session stopped mid-task when its context ran out. Its last edits (API `pyproject.toml` pytest loop scope, `alembic/env.py` include filter, the response service, integration tests, README, notes) were intact and consistent; the corrective items below had not been started.

### Agent handoff repaired
- `CLAUDE.md` and `AGENTS.md` (kept identical) told agents to begin Milestone 1 and claimed pgvector was enabled. They now describe the implemented state, name Milestone 4 as next and not started, require inspecting Git state before editing, and forbid recreating the foundation.
- `IMPLEMENTATION_HANDOFF.md` gained a status table; the original milestone plan is kept, and the "first pull request" section is marked historical. pgvector item annotated as superseded by D013.

### Conflicting-response contract made deterministic
- `record_response` now takes `SELECT … FOR UPDATE` on the suggestion-session row before reading the stored response or session state. A concurrent loser blocks until the winner commits, then sees the winner's row and receives `ConflictError` (409) — never `InvalidStateError` (422).
- The `IntegrityError` handler only interprets `proposal_responses_client_event_id_key` and `uq_proposal_responses_proposal_id`; any other integrity error is re-raised. Previously, an unmatched integrity error was converted to a generic 409 "Concurrent response conflict".
- The separate Another-path lock was removed; the earlier session lock covers it.
- `test_concurrent_conflicting_responses_one_wins` now accepts only `ConflictError` (status 409, code `conflict`) for the loser.
- Added `test_conflicting_response_after_answer_returns_409` and `test_unrelated_integrity_error_not_converted_to_conflict`.
- Contract recorded in `ARCHITECTURE.md` under `proposal_responses`.

### Concurrent-test fixture leak fixed
- Repeated runs exposed that `concurrent_setup` cleanup did not delete `user_place_states`; each visit-confirmation run marked one of the 20 fixture places visited, so setup failed after ~18 runs. The fixture now purges all rows for the concurrent-test user before setup and after teardown.

### Current counts
- 12 spike, 68 API unit, 29 integration (27 + 2 new negative tests), 36 mobile Jest.
- Mobile: Expo SDK 53, Expo Router `~5.1.11`.

### Deferred
- `apps/mobile/assets/icon.png` and `notification-icon.png` are 1×1 placeholders.
- Milestone 3 offline queue/cached suggestion and EAS development build.

## 2026-10-12 — Milestone 0.1 complete verification

### Infrastructure
- Docker Desktop installed and running.
- `docker compose up -d db` → `nosh-db-1` healthy on `127.0.0.1:5432/nosh_dev`
- `docker compose --profile test up -d db_test` → `nosh-db_test-1` healthy on `127.0.0.1:5433/nosh_test`
- PostgreSQL 16.4, PostGIS 3.4
- pgvector: intentionally absent (deferred per D013)

### Event-loop / pytest-asyncio fix
- Added `asyncio_default_test_loop_scope = "session"` and `asyncio_default_fixture_loop_scope = "session"` to `[tool.pytest.ini_options]` in `services/api/pyproject.toml`.
- Root cause: the session-scoped `engine` fixture was created with one event loop, but function-scoped tests created new loops. asyncpg connections are bound to their creation loop — using them from a different loop raises "Event loop is closed".
- Fix: all tests share a single session-wide event loop (the default changed from "session" to "function" in pytest-asyncio 0.21+).

### Alembic check fix
- Added `include_object` filter to `services/api/alembic/env.py`.
- Excludes tiger, tiger_data, topology schemas (PostGIS Tiger Geocoder extension).
- Excludes `spatial_ref_sys` and other non-application public tables.
- Applied to both `run_migrations_offline()` and `run_migrations_online()`.
- `alembic check` now prints "No new upgrade operations detected."

### Concurrent response semantics fixes
- `proposal.response is not None` check moved BEFORE `session.state != "active"` check.
  - Reason: a concurrent winner changes session state, so the loser would incorrectly get InvalidStateError instead of returning the winner's response.
- After IntegrityError and savepoint rollback: query `ProposalResponse` directly (not via `Proposal.response` relationship which may cache None from the identity map).
- Both callers now return the same response ID for identical concurrent attempts.
- Conflicting-action race: one wins, loser gets ConflictError (not InvalidStateError).

### Session creation serialization
- `get_or_create_session` now takes `SELECT ... FOR UPDATE` on the `DiningContext` row before checking/creating the session.
- Double-checked locking: fast unlocked read → lock acquisition → re-read → create if still absent.
- Guarantees both concurrent callers receive the same session ID.

### Concurrency test improvements
- All 4 concurrent tests use `asyncio.Barrier(2)` to maximise overlap.
- `test_concurrent_identical_response_idempotent`: BOTH callers must succeed, BOTH must return same response ID.
- `test_concurrent_conflicting_responses_one_wins`: exactly 1 winner, exactly 1 ConflictError/InvalidStateError loser, session state matches winner.
- `test_concurrent_visit_confirmation_idempotent`: BOTH callers must succeed, BOTH must return same visit ID.
- `test_concurrent_session_creation_idempotent`: BOTH callers must succeed, BOTH must return same session ID.
- All assertions are exact — no "≥ 1 success" weak checks.

### Verified results
All checks pass. See §8 command-by-command results below.

| Check | Result |
|---|---|
| Root lockfile + 12 spike tests | ✅ |
| API lockfile, ruff, format, mypy 0 errors | ✅ |
| 68 API unit tests | ✅ |
| Alembic downgrade base → upgrade head (5433) | ✅ |
| `alembic check` | ✅ "No new upgrade operations detected" |
| 27 integration tests (incl. 4 concurrent) | ✅ **27/27 passed in 6.94s** |
| API smoke test (/live, /ready, /openapi.json) | ✅ |
| Mobile: TypeScript, ESLint, 36 Jest, Expo Doctor 18/18 | ✅ |
| `git diff --check` | ✅ |
| npm audit --omit=dev | ⚠️ 37 vulns in Expo's own deps (see advisory section) |

## 2026-10-12 — Milestone 0.1 preparation: transaction, test-contract, and concurrency fixes

### What was changed

**Transaction correctness in record_response**
- `db.add(resp)` and `await db.flush()` moved INSIDE the `begin_nested()` block so that autoflush cannot fire during SAVEPOINT creation and escape the IntegrityError handler.

**Integration test contract fixes**
- `test_visit_idempotent_same_proposal`: added Go response before confirming visit.
- `test_visit_correction`: added Go response before confirming visit.
- `test_visited_place_excluded_from_next_session`: added Go response before confirming visit.
- `test_account_deletion_removes_all_data`: endpoint changed from `DELETE /v1/me` to `DELETE /v1/me/product-data`.
- Added negative test `test_visit_requires_go_response_first`: proposal-backed visit without Go → 422 `proposal_not_accepted`.
- Default integration test port changed from 5432 to 5433 (matches the `db_test` Compose service).

**Real concurrency tests added (separate DB connections)**
- `test_concurrent_identical_response_idempotent`: two sessions racing to insert the same Go response — exactly one row persists.
- `test_concurrent_conflicting_responses_one_wins`: Go vs Not-today race — one wins, exactly one row.
- `test_concurrent_visit_confirmation_idempotent`: two sessions racing to confirm the same proposal visit — exactly one visit row.
- `test_concurrent_session_creation_idempotent`: two sessions creating the same window session — exactly one session row.
- All use `committing_factory` with real commit/rollback semantics, not the rollback isolation fixture.

**ORM model drift fixed**
- `Visit.__table_args__` now includes the `uq_visits_user_proposal` partial unique index with `postgresql_where=text("proposal_id IS NOT NULL")`, matching migration 0003.

**Progress metric extracted as testable pure function**
- `compute_progress_months(visits, pre_nosh_places)` extracted from `get_progress()` in `visits/service.py`.
- `test_progress_metric.py` now imports and calls the real production function — not a duplicate algorithm.
- 8 unit tests covering: first visit, pre-Nosh exclusion, re-visit same place, negative rating, multi-place, month ordering, empty input, provenance permanence.

**Progress integration tests added**
- `test_progress_counts_new_positive_visits`: end-to-end Go → confirm → progress count.
- `test_progress_excludes_pre_nosh_onboarding_place`: onboarding 'Been' mark → visit confirmed → not counted as new.

### Verification status (this session)
- Root lockfile + 12 spike tests: ✅
- API ruff lint, format, mypy 0 errors, 68 unit tests: ✅
- Mobile TypeScript, ESLint, 36 Jest tests: ✅
- `git diff --check`: ✅
- `git status --short`: 15 lines

**Docker/PostgreSQL**: NOT INSTALLED at time of writing. Brew cask install fails without sudo for a symlink. User must run `brew install --cask docker` in a terminal with password. Integration tests and migrations cannot be verified until Docker is running.

## 2026-10-12 — Pre-milestone repair and hardening (round 2)

### Accidental node artifacts removed
- `services/api/node_modules/` (223 MB), `services/api/package.json`, `services/api/package-lock.json` removed.
- `.gitignore` updated: `node_modules/` ignored globally, Python caches covered, `memory/` excluded (agent-local).

### Jest boundary test corrected
- `2026-10-13T07:00:00Z` is midnight in LA (UTC-7) = Oct 13, not Oct 12. Test was asserting the wrong expected value.
- `mealWindowKey.ts` rewritten: `activeMealType()` now respects minutes, active_days (0=Mon…6=Sun), half-open interval, invalid TZ (returns null not fallback), overnight window rejection.
- `mealWindowKey()` returns `string | null`; mobile screen shows "No active meal window" when null.
- 36 Jest tests; all pass.

### Production auth hardened
- `SUPABASE_URL` required in all production modes (issuer verification requires it).
- URL normalized (trailing slashes stripped). Loopback check: only localhost/127.0.0.1/[::1].
- `AppEnvironment` StrEnum: `local | test | production`. `AUTH_LOCAL_DEV=true` rejected in `production`.
- JWKS: `cache_keys=False` (no stale revoked-key cache), JWK set cached 1 h, async via `anyio.to_thread.run_sync`, supports RS256+ES256.

### Migration 0002 completed
- Added `REVOKE ALL ON ALL ROUTINES` from `PUBLIC`, `anon`, `authenticated` + default privilege revocation for routines.

### Migration 0004 added: `was_visited_before_nosh`
- `user_place_states.was_visited_before_nosh BOOLEAN NOT NULL DEFAULT FALSE`.
- Set on onboarding; never reset; backfilled. Progress metric uses this flag.

### ORM models synced
- `ProposalResponse` UniqueConstraint on `proposal_id`. `Visit.proposal_id` FK `ON DELETE SET NULL`. `UserPlaceState.was_visited_before_nosh` column.

### Visit integrity: require exact Go response
- `confirm_visit()` now verifies `ProposalResponse(response='go')` for the specific proposal.

### Response idempotency: savepoints
- Competing response race handled via savepoint; verifies winning response belongs to same user/action.

### Deletion endpoint renamed
- `DELETE /v1/me/product-data` (was `/v1/me`). Honest about scope: removes product data, not Supabase Auth identity.

### Verification status
- Root: lockfile ✓, 12 spike tests ✓
- API: ruff ✓, format ✓, mypy 0 errors ✓, 65 unit tests ✓
- Mobile: TypeScript ✓, ESLint ✓, 36 Jest tests ✓, expo install --check ✓, expo-doctor 18/18 ✓
- git diff --check ✓, git status: 14 lines
- Integration tests: NOT RUN (PostgreSQL/Docker unavailable)
- npm audit (--omit=dev --audit-level=high): 37 vulnerabilities in Expo SDK 53 own deps (see below)

## 2026-10-12 — Phase-one product and architecture baseline

### Naming considered first and selected

The product and repository are named **Nosh**. Other candidates considered were Forage, Tuck, Crumb, Morsel, Savor, and Bite.

Nosh was selected because it is the closest conceptual match to the desired Toast-like feeling: short, food-native, and usable as an action. The name has not been checked for trademarks, domains, App Store conflicts, or social handles.

### Product requirements written

Created `PRODUCT.md` as the canonical phase-one PRD. It now defines:

- the problem and product vision;
- primary and secondary users;
- product principles and jobs to be done;
- the end-to-end MVP journey;
- eleven core feature groups and their requirements;
- required product events;
- the North Star, funnel metrics, guardrails, and initial validation targets;
- candidate, timing, response, connectivity, and privacy edge cases;
- explicit phase-one non-goals;
- MVP exit criteria;
- the naming shortlist.

The selected North Star is confirmed positively rated new restaurants per monthly active user.

### Architecture written

Created `ARCHITECTURE.md` with a modular-monolith design:

- Expo React Native and TypeScript mobile client;
- FastAPI and Python backend;
- Supabase Auth and hosted PostgreSQL;
- PostGIS for distance queries;
- pgvector installed but unused in phase one;
- a lightweight scheduler/worker from the same codebase;
- deterministic, versioned recommendation logic;
- OpenAPI-generated TypeScript client;
- proposed repository layout, database tables, API endpoints, state machine, testing, environments, observability, and security expectations.

The API hosting vendor remains deliberately undecided until a deployable vertical slice exists.

### Recommendation methodology written

Created `RECOMMENDATIONS.md` with:

- phase-one eligibility filters;
- a Thompson-sampling cuisine policy with remaining-pool value;
- a deterministic restaurant scoring model;
- conservative feedback semantics;
- cold-start and diversity behavior;
- decision logging and policy versioning requirements;
- offline, online, and invariant-based evaluation plans;
- capabilities explicitly deferred beyond phase one.

The production design intentionally treats Another more conservatively than the existing toy simulator because a place-first rejection does not identify whether the user disliked the restaurant, cuisine, distance, or moment.

### Decisions recorded

Created `DECISIONS.md` and recorded the accepted baseline decisions:

- name the product and repository Nosh;
- use confirmed positive new visits as the North Star;
- build an Expo iOS-first client;
- use a FastAPI modular monolith;
- use Supabase PostgreSQL with PostGIS;
- keep meal-time recommendations deterministic;
- use directions-only handoff;
- start with curated place data;
- build for the founder and a small private cohort;
- avoid background location and calendar permissions;
- interpret Another conservatively;
- defer the API hosting vendor.

### Repository preparation

The original directory was already a Git repository on branch `main`, with one existing commit and no configured remote. Product content, package metadata, and the local repository directory were renamed from Forage to Nosh. The new root documents make the product and technical baseline explicit and were committed before connecting the repository to GitHub.

The repository can be linked after an empty GitHub repository is created by adding its URL as `origin` and pushing `main`. No remote URL or GitHub credentials were available during this work, so no external repository was created or linked automatically.

### Claude implementation handoff

Created `IMPLEMENTATION_HANDOFF.md` with a concise implementation brief for Claude. It establishes the canonical document order, non-negotiable constraints, four implementation milestones, first-pull-request scope, engineering expectations, and the MVP definition of done.

The handoff directs Claude to begin with a reviewable backend-foundation pull request, preserve the existing simulator, keep the recommendation path deterministic, and surface product ambiguities through `DECISIONS.md` rather than silently expanding scope.

### GitHub readiness

Added a minimal GitHub Actions workflow that verifies the lockfile, installs the locked development dependencies, and runs the Python test suite on pushes to `main` and pull requests. Added a pull-request template that requires verification, privacy checks, canonical-document consistency, and phase-one scope discipline.

## 2026-10-12 — Security, correctness, and contract hardening

### What was fixed

**Priority 1 — Database access security (D014)**
- Migration 0002 revokes all privileges from Supabase's `anon` and `authenticated` roles on all product tables and sets default privileges to prevent auto-grant on future tables.  Uses `DO $$` blocks so it is a no-op on plain local PostgreSQL where those roles don't exist.
- Decided not to move to a private schema (would require renaming in all models); REVOKE is simpler and correct.

**Priority 2 — Production authentication**
- Replaced `python-jose` with `PyJWT[cryptography]>=2.8`.
- `_decode_hs256()`: validates exp, iss, aud (authenticated), role, and sub; granular error messages per claim.
- `_decode_rs256()`: uses `PyJWKClient` with in-memory JWKS cache (1 h TTL, auto-refresh on new kid).
- `AUTH_LOCAL_DEV=true` blocked at startup when `DATABASE_URL` points to a non-local host; checked via URL hostname parse.
- Config validates at startup; fails loudly when neither `SUPABASE_JWT_SECRET` nor `SUPABASE_URL` is set in production mode.
- 14 new auth unit tests covering all error cases: expired, wrong issuer, missing issuer, wrong audience, wrong role, missing sub, non-UUID sub, tampered signature.

**Priority 3 — Response idempotency**
- Migration 0003 adds `UNIQUE(proposal_id)` to `proposal_responses` (one response per proposal at DB level).
- `record_response` catches `IntegrityError` from concurrent response races and returns the winner's result idempotently.
- `SELECT FOR UPDATE` on session row serializes concurrent "Another" requests.
- Idempotency check verifies that a replayed `client_event_id` matches the same proposal AND action; returns 409 if they differ.
- Mobile idempotency key changed from `{proposal_id}:{action}:{Date.now()}` to `{proposal_id}:{action}` — stable across retries.

**Priority 4 — Visit integrity**
- Migration 0003 adds partial unique index `(user_id, proposal_id) WHERE proposal_id IS NOT NULL` — prevents concurrent duplicate confirmations.
- Migration 0003 changes `visits.proposal_id` FK from implicit `RESTRICT` to `ON DELETE SET NULL` — unblocks cascade deletion through contexts.
- `confirm_visit` now validates: proposal exists (404 otherwise), proposal belongs to the user (403), session state is `accepted` (422 session_not_accepted), and `place_id` matches the proposal (422 place_mismatch).
- Cursor ownership validated in `list_visits` — cursor must belong to the requesting user.
- Manual visits (no proposal_id) documented and allowed per D015.

**Priority 5 — Account deletion**
- Deletion order fixed: visits first (before contexts cascade to proposals), then notification_deliveries, then contexts (cascades sessions→proposals→responses), then place_states, device_tokens, profile.
- `NotificationDelivery` rows explicitly deleted.
- TODO documented: Supabase Auth user deletion requires service-role key (not yet implemented).

**Priority 6 — Meal-window key**
- New `apps/mobile/src/utils/mealWindowKey.ts`: pure function deriving `YYYY-MM-DD#meal_type` from the context's IANA time zone and configured meal type (not the device UTC date + local hour).
- `apps/mobile/src/utils/mealWindowKey.test.ts`: 11 unit tests covering UTC boundary, DST spring-forward, DST fall-back, and device-TZ-differs-from-context-TZ scenarios.
- Suggestion screen updated to use `mealWindowKey(activeContext)` instead of the old heuristic.

**Priority 7 — Progress metric correctness**
- `get_progress` now fetches `user_place_states` where `source='onboarding'` and `state='visited'` before counting new restaurants.  Pre-existing places are excluded from the "positive new" count.
- 5 new unit tests in `test_progress_metric.py` covering: first visit, onboarding-been excluded, second visit same place, negative visit, multiple new places.

**Priority 8 — Mobile/API contract**
- Added `'no_candidates'` to `Session.state` type union.
- Suggestion screen handles `no_candidates` with a specific empty-state message and settings link.

**Priority 9 — CORS and environment**
- CORS middleware now only activates when `CORS_ORIGINS` env var is set (non-empty).  No wildcard origins.  Allowed methods and headers explicitly enumerated.
- `.gitignore` updated to ignore `.env.production`, `.env.staging`, `.env.development`, `.env.test`, `.env.*` — with explicit `!.env.example` exception.
- `.env.example` updated to document JWKS path, CORS config, and AUTH_LOCAL_DEV safety note.

**Priority 10 — Tests**
- Replaced all `assert True` placeholders with real behavior tests (inactive/out-of-radius documented as contract tests).
- Added `tests/test_auth.py` (14 unit tests, no DB).
- Added `tests/test_progress_metric.py` (5 unit tests, no DB).
- Integration tests in `test_integration.py` unchanged; 20 tests still require PostgreSQL.
- Mobile: Jest configured (`jest-expo` preset); `mealWindowKey.test.ts` contains 11 unit tests runnable via `npm test`.

**Decisions recorded**
- D014: Revoke Supabase Data API access (REVOKE strategy in migration 0002).
- D015: Manual visits may omit a proposal_id.

### Verification status

| Check | Result |
|---|---|
| Root lockfile (`uv lock --check`) | ✅ Pass |
| Root spike tests (12) | ✅ 12 passed |
| API lockfile (`uv lock --check`) | ✅ Pass |
| Ruff lint | ✅ Clean |
| Ruff format | ✅ Clean |
| Strict mypy (0 errors) | ✅ Pass |
| API unit tests (56) | ✅ 56 passed, 20 deselected |
| `git diff --check` | ✅ Clean |
| Mobile `npm ci` | ✅ Clean |
| Mobile TypeScript `tsc --noEmit` | ✅ Clean |
| Mobile ESLint | ✅ Clean |
| Mobile `expo install --check` | ✅ Clean |
| Mobile `npm audit --omit=dev` | ⚠️ 37 vulnerabilities in Expo's own deps; not fixable without breaking the SDK 53 matrix |
| Integration tests (20) | ⏳ Written; require PostgreSQL (Docker not available in this environment) |
| Alembic migration round-trip | ⏳ Written (3 migrations); requires PostgreSQL |

### Remaining blockers

1. PostgreSQL not available — integration tests and migration tests cannot execute locally.
2. Supabase credentials — production auth requires `SUPABASE_JWT_SECRET` or `SUPABASE_URL`.
3. Supabase Auth user deletion — `DELETE /v1/me` removes product data but not the Supabase Auth record; requires `SUPABASE_SERVICE_ROLE_KEY` (not yet implemented, documented in `users/service.py`).
4. Production dependency audit — 37 moderate/high vulnerabilities in Expo SDK 53's own dependencies; tracked upstream.

## 2026-10-12 — Backend vertical slice repair and verification

### What was fixed and added

**Mobile (Priority 1):**
- Upgraded to a coherent Expo SDK 53 dependency matrix via `npx expo install --fix`.
  React 19.0.0, React Native 0.79.6, Expo Router 5.1.x — all confirmed by `expo install --check: Dependencies are up to date`.
- Fixed JSX syntax error in `confirmation/[sessionId].tsx` (curly right-quote in string literal).
- Fixed confirmation screen: now passes `proposalId`, `placeId`, and `placeName` as route params on Go so visit confirmation never submits an empty `place_id`.
- Fixed unescaped entity in `onboarding.tsx`.
- Removed unused import (`useMemo`) in `index.tsx`.
- Added `eslint.config.js` for Expo SDK 53 flat config (`eslint-config-expo/flat`).
- Added placeholder `assets/icon.png` and `assets/notification-icon.png`.
- `npm ci`, `npx tsc --noEmit`, `npx eslint .`, and `npx expo install --check` all pass clean.
- `npx expo-doctor`: 18/18 checks passed.

**Backend bugs (Priority 2):**
- Fixed missing `await` on `_session_id_for_proposal()` in the idempotency path.
- Added ownership check on the idempotency fast-path (cross-user replay now returns 403).
- One-response-per-proposal idempotency: existing proposal.response returns the stored result rather than raising ConflictError.
- Distance is now stored in `candidate_snapshot["distance_meters"]` and correctly serialized in `ProposalResponse_Schema`.
- Session creation with no candidates immediately enters `no_candidates` state.
- `select_cuisine` now returns `(cuisine_id, sampled_score)` so the score stored in the decision log is the one actually used, not a re-sample.
- `_load_cuisine_stats` now populates `history_frequency` from `user_place_states` visited counts (onboarding prior).
- Visit `confirm_visit` validates proposal ownership and `place_id` match before writing.

**Database (Priority 3):**
- Removed `CREATE EXTENSION vector` from migration and `db/init.sql`; pgvector deferred (D013).
- Docker Compose ports bound to `127.0.0.1`.

**Auth security (Priority 4):**
- Auth dependency now validates Supabase JWT: expiry, issuer, audience (`authenticated`), and `role` claim.
- `validate_auth_config()` called at startup; fails immediately when `AUTH_LOCAL_DEV=false` and `SUPABASE_JWT_SECRET` is empty.
- Readiness endpoint returns `{"status": "unavailable"}` rather than raw DB exception details.
- `DELETE /v1/me` now hard-deletes all user-owned rows (contexts, sessions, proposals, responses, place-states, visits, device tokens, profile) rather than soft-deleting only the profile.

**Tests (Priority 5):**
- Added `tests/test_integration.py`: 20 integration tests covering Go/Another/Not today, idempotency, cross-user authorization, candidate exhaustion, visit confirmation, correction, progress, not-interested exclusion, visited exclusion, account deletion, and migration round-trip.
- Tests require a live PostgreSQL; auto-apply migrations on first run.

**CI (Priority 6):**
- CI now runs: root lockfile check, API lockfile check, ruff lint, ruff format, strict mypy, unit tests, migration upgrade/downgrade/upgrade, real integration tests, `npm ci`, TypeScript, ESLint, Expo dependency check, `git diff --check`.

**Types (Priority 6):**
- Fixed all 29 mypy strict errors: return-type annotations on all route handlers, `dict[str, T]` generic args, `AsyncEngine` return type, lifespan `AsyncGenerator` return, `DiningContext` typed parameter replacing `object`.

### Decisions recorded

- D013: pgvector deferred until an embedding feature has a defined evaluation set.

### Verification status

- Root spike tests: 12 passed.
- API unit tests: 30 passed, mypy 0 errors, ruff clean.
- Integration tests: written and structured; require PostgreSQL to execute.
- Mobile: `npm ci` clean, TypeScript clean, ESLint clean, Expo Doctor 18/18.
- `git diff --check`: passes.

### Remaining blockers

- PostgreSQL required for integration tests (Docker not available in this environment).
- Supabase project and SUPABASE_JWT_SECRET needed for production auth.
- Milestone 4 (notifications, hosting, TestFlight) not started.

## 2026-10-12 — Milestones 1–3 implementation

### What was built

**Milestone 1 — Repository and backend foundation**

- Created monorepo structure: `services/api/`, `apps/mobile/`, `jobs/`, `db/`, `packages/api-client/`
- Scaffolded FastAPI modular monolith under `services/api/` with its own `pyproject.toml` and uv project
- Dependencies: FastAPI 0.115, Pydantic v2, SQLAlchemy 2, Alembic, asyncpg, GeoAlchemy2, psycopg2-binary, python-jose, pydantic-settings
- Dev tools: ruff (lint + format), pytest, pytest-asyncio, mypy
- Docker Compose PostgreSQL with PostGIS 16-3.4; pgvector enabled via `db/init.sql`
- `.env.example` at root and `services/api/.env.example` with local-dev defaults
- `/health/live` (no auth, no DB) and `/health/ready` (DB ping, 503 on failure)
- Initial Alembic migration (`0001_initial_schema.py`) covering all 13 tables from ARCHITECTURE.md
- Migration tested for upgrade and downgrade in CI
- CI updated: spike tests, API lint/format/test/migration jobs, mobile TypeScript check

**Milestone 2 — Deterministic suggestion API**

- 20 fixture restaurants in SF Mission District loaded via `load_fixture_data()`
- PostGIS radius filtering via `ST_DWithin` and `ST_Distance`
- `policy_v0` recommendation engine in `app/recommendations/engine.py` (pure functions, no I/O):
  - Thompson-sampling cuisine selection with Beta posteriors
  - History prior `Beta(1 + 4f, 1 + 4(1-f))` per RECOMMENDATIONS.md
  - Place scoring: 0.45 quality + 0.30 distance + 0.15 context_fit + 0.10 exploration
  - Deterministic via `sha256(session_id:sequence:policy_version)` seed
- All eligibility filters enforced upstream in `build_candidates()`; engine trusts caller
- Idempotent session creation via `UNIQUE(dining_context_id, meal_window_key)`
- Go/Another/Not today responses with validated state transitions
- Visit confirmation, rating, correction, history, and monthly progress endpoints
- Full authorization: every user-owned resource checked for ownership
- Mobile write idempotency via `client_event_id` on proposal responses and `proposal_id` on visits

**Milestone 3 — Expo client**

- Expo Router 4 app under `apps/mobile/` with strict TypeScript
- Hand-maintained typed client (`src/api/client.ts`) mirroring FastAPI OpenAPI schema
- Auth hook (`src/hooks/useAuth.ts`) with clearly isolated local-dev adapter (UUID token) and interface ready for Supabase JWT swap
- Screens: sign-in, context creation, onboarding place classification, suggestion card (main), confirmation, rating, history, progress, settings
- Apple Maps handoff on Go via `maps://` deep link with address fallback
- TanStack Query v5 for all data fetching and mutations
- SuggestionCard and ResponseButtons components

### Tests

- 12 existing spike tests: all pass (unchanged)
- 30 new API unit tests (no database required):
  - pool value and cuisine scoring mechanics
  - all required recommendation invariants (visited/not-interested exclusion, no repeat within session, exhaustion, determinism, policy version)
  - health endpoint (live/ready, 503 on DB failure)
  - state machine documentation tests

### Key contracts

- `policy_v0` treats Another as no cuisine update (per D011/RECOMMENDATIONS.md §7)
- Not today is timing feedback only; no cuisine or place preference updated
- Only confirmed + positively rated + previously unvisited visits count toward North Star
- Go is intent; visit confirmation is a separate explicit step

### Remaining for Milestone 4

- Expo push notification registration and device token endpoint
- Idempotent scheduler/worker (pre-meal-window session creation + notification)
- Visit-confirmation prompts sent after the meal window closes
- Time-zone and DST regression tests
- API hosting vendor selection (D012 deferred)
- EAS development build and TestFlight environment setup

## 2026-10-12 — GitHub connection and Claude brief

Added `CLAUDE.md` as the concise, automatically discoverable implementation brief. It directs Claude to read the canonical product and architecture documents, begin with the backend-foundation milestone, preserve the simulator, enforce phase-one constraints, and meet a concrete first-pull-request checklist.

Configured the repository for the provided GitHub destination `https://github.com/winston0753/nosh.git`. The remote was empty when checked, so the local `main` history was safe to publish without reconciling unrelated commits.
