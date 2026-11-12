# Nosh Architecture

- **Status:** Phase-one baseline, being reconciled with the dish-first pivot
- **Version:** 0.2
- **Last updated:** 2026-11-10

> **Read this first.** On 2026-11-10 Nosh pivoted from suggesting "one nearby unvisited restaurant" to suggesting "one specific dish at a specific restaurant branch" (DECISIONS.md D032–D043). **Everything this document labels "Planned" does not exist yet.** No part of D032–D043 is implemented. The code on `main` still suggests restaurants from 20 fictional San Francisco fixture places using `policy_v0`.
>
> This document keeps three things apart:
>
> - **Implemented today** — what the code on `main` does.
> - **Planned (not implemented)** — accepted decisions with no code yet.
> - **Superseded / historical** — older plans kept for context, labelled as such.
>
> Where something is not decided, this document says so and points to the "Open questions" list at the end of DECISIONS.md.

## 1. Architecture goals

- Deliver one complete loop with minimal operational complexity. Today that loop is restaurant suggestion → visit confirmation. The planned first target is: dish onboarding → dish-and-restaurant recommendation → scheduled delivery → actual-dish confirmation → immediate discovery reward → updated profile and a minimal avatar and journal.
- Keep meal-time recommendation behaviour deterministic, testable, and reconstructable. No LLM call at meal time (D006, D041).
- Keep the three data classes apart (planned, D034): the shared catalog Nosh owns, provider content from outside sources, and personal data.
- Support local development and a small private TestFlight cohort (D009).
- Keep user location, preferences, and meal history private by default.

## 2. Non-goals

Phase one does not use microservices, a message broker, a graph database, a separate vector database or vector service, an event platform, real-time streaming infrastructure, an agent framework, or a globally replicated system (D004, D041). pgvector stays absent (D013).

Nosh Meals and social features are possible later extensions. Nothing in this document creates tables, services, or infrastructure for them.

## 3. System overview

### 3.1 Implemented today

```text
┌─────────────────────────────┐
│ Expo React Native app       │
│ iOS-first, TypeScript       │
│ (placeholder SF location;   │
│  Go opens Apple Maps)       │
└──────────────┬──────────────┘
               │ HTTPS / JSON
               ▼
┌─────────────────────────────┐
│ FastAPI modular monolith    │
│                             │
│ API and auth boundary       │
│ Meal schedule, Home/Work    │
│ Suggestion sessions         │
│ policy_v0 (restaurants)     │
│ Visits, history, progress   │
│ Product-data deletion       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ PostgreSQL + PostGIS        │
│ (local Docker today;        │
│  Supabase planned, D030)    │
│ pgvector absent (D013)      │
│ 20 fixture places           │
└─────────────────────────────┘
        Supabase Auth (email code) verifies users
```

There is no notification worker, no push sending, no outside place provider, and no deployed environment. The API is not yet deployed to Fly.io (D030 is accepted, not done).

### 3.2 Planned (not implemented)

```text
                 OFFLINE (batch jobs, same codebase)
┌───────────────────────────────────────────────────────────┐
│ Sources (undecided, D042) → adapters → branch match →      │
│ menu items → catalog mapping (LLM allowed, D041) →         │
│ review → published dish offerings                          │
└───────────────────────────┬───────────────────────────────┘
                            ▼
┌─────────────────────────────┐        ┌─────────────────────┐
│ PostgreSQL + PostGIS        │◄──────►│ FastAPI monolith    │
│ shared catalog              │        │ + scheduler/worker  │
│ provider content (tagged)   │        │ deterministic dish  │
│ personal data               │        │ ranking, no LLM     │
└─────────────────────────────┘        └──┬───────┬──────────┘
                                          │       │
                    live place status/hours│       │ push
                    (provider undecided)  ▼       ▼
                                 ┌──────────────┐ ┌──────────────────┐
                                 │ status/hours │ │ Expo Push Service │
                                 └──────────────┘ └──────────────────┘
```

- Google Places is **no longer** the planned candidate source. D021 was superseded by D034 before anything was built. Candidates come from Nosh's own published dish-offering index.
- Live place status and opening hours are a separate input that can make an offering ineligible right now. Which provider supplies them is an open question (DECISIONS.md open question 4).
- Which map the card shows and which maps app Go opens is an open question (open question 5). The code opens Apple Maps.

## 4. Technology choices

These are implemented unless marked.

### Mobile

- Expo SDK 58 and React Native 0.88 (D019)
- TypeScript with strict checking
- Expo Router
- TanStack Query
- Supabase JS client for email one-time-code sign-in; session stored with `expo-secure-store`
- `expo-notifications` is a dependency, but nothing imports it yet
- Typed API client, hand-written in `apps/mobile/src/api/`. Generating it from OpenAPI is planned, not implemented.
- Planned: `expo-location` in the foreground only, to revalidate the meal area when the app opens (D017, D035). The app requests no location today.
- Planned: EAS development builds and TestFlight (D029 bundle identifier `com.winstontang.nosh`)

### API

- Python 3.11+ (`requires-python`); CI runs 3.12
- FastAPI, Pydantic v2
- SQLAlchemy 2 (async) with asyncpg
- Alembic migrations
- `uv` for dependency and environment management
- pytest

### Data

- PostgreSQL with PostGIS: local Docker Compose today; Supabase-hosted Postgres planned for shared environments (D005, D030)
- PostGIS geography points and GiST indexes for radius queries
- pgvector absent (D013); the `postgis/postgis` image does not include it

### Operations

- One API container (planned host: Fly.io, D030; not deployed)
- Planned: one lightweight scheduler/worker process built from the same codebase (none exists today)
- Planned: offline batch jobs for acquisition and catalog work, in `services/api/jobs/`
- Structured logs
- GitHub Actions for linting, typing, tests, migration checks, and the simulator regression

## 5. Repository layout

Implemented today:

```text
nosh/
├── apps/
│   └── mobile/              # Expo app (app/ routes, src/ code and tests)
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/             # /v1 router
│       │   ├── auth/
│       │   ├── core/            # database, errors
│       │   ├── users/           # profile, product-data deletion
│       │   ├── schedules/       # meal schedule and Home/Work anchors
│       │   ├── places/
│       │   ├── recommendations/ # policy_v0
│       │   ├── suggestions/
│       │   ├── visits/
│       │   └── notifications/   # table models only
│       ├── alembic/versions/    # migrations 0001–0005
│       ├── tests/
│       └── jobs/                # same uv project and `app` package as the API
│           └── ingest_places/
├── db/
│   └── init.sql             # local database initialisation
├── spike/                   # cuisine-policy simulator
├── tests/                   # root spike tests
├── PRODUCT.md
├── ARCHITECTURE.md
├── RECOMMENDATIONS.md
├── DECISIONS.md
├── IMPLEMENTATION_HANDOFF.md
└── notes.md
```

Jobs live inside `services/api/jobs/` and import the application as the top-level `app` package, exactly like the API and its tests. Run them from `services/api` as `uv run --frozen python -m jobs.<job>.<module>`; never import through `services.api.app`. The directories describe ownership boundaries, not separately deployed services.

**Planned (not implemented):** new modules inside the same `app` package for the dish catalog, offerings and acquisition, dish experiences, and rewards; new jobs for acquisition, catalog mapping, evaluation, and notification scheduling. Module names are not decided.

## 6. Component responsibilities

### Mobile application

Implemented today:

- Account session (Supabase email code, or local-dev UUID mode)
- Meal-schedule survey and settings, including a per-meal price ceiling
- Restaurant suggestion card with Go, Another, Not today, and Been here already
- Go opens Apple Maps with a name-and-address search
- Visit confirmation and rating, history, progress, and product-data deletion
- Every session is anchored at a hard-coded San Francisco Mission point (`PLACEHOLDER_LOCATION`); saved Home/Work spots are never used

Planned (not implemented):

- Dish onboarding and preferences, including explicit constraints (which ones is open question 10)
- Confirming a coarse meal area per meal, revalidated with foreground location when the app opens (D035)
- Dish suggestion card; map and handoff target undecided (open question 5)
- Notification registration and deep links
- Actual-dish confirmation, including "I ate something else" (D037; open question 13)
- Discovery moment, journal, and avatar (D039)
- Local persistence of session and proposal identifiers and a queue of idempotent writes for network failures

The mobile client contains presentation logic, not recommendation logic.

### FastAPI application

Implemented today: validate Supabase access tokens, enforce user ownership, run product workflows and state transitions, generate and version restaurant recommendations, manage visit records, and publish an OpenAPI contract.

Planned: rank published dish offerings, record dish experiences and rewards in one transaction per confirmation (D038), compute the avatar, and serve the journal.

### Scheduler/worker (planned, not implemented)

- Find users whose meal windows are approaching.
- Prepare one dish proposal when the user has a meal area; otherwise send a generic nudge (D035).
- Send at most one meal-time notification per user and meal window, deduplicated.
- Create due confirmation prompts.
- Retry transient failures with bounded backoff.
- Ignore disabled meals and deleted users.

The send time, what a dish-naming notification may show, and whether it offers actions are open (open question 12). The first worker may poll PostgreSQL on a short interval; no message broker is needed at this scale.

### Recommendation module

Implemented today (`policy_v0`): load eligible fixture places within a fixed 1,600 m radius, apply hard filters, score cuisines and places, persist score components and the policy version, and return a proposal with factual reason codes. It has no network or LLM dependency. The stored `price_ceiling` is not used.

Planned: a deterministic dish policy that reads only published offerings, plus the live status/hours eligibility input, with no LLM call (D032, D034, D041). Its weights and the meaning of each response for dishes are open (open questions 6–9). RECOMMENDATIONS.md describes the policy.

### Acquisition and catalog (planned, not implemented)

Offline jobs that turn outside sources into published dish offerings (flow 1 in section 8). LLMs may help with catalog generation and menu mapping, each with its own evaluation set (D041). The first supply is a hand-verified index for downtown San Mateo (D042).

### Place ingestion (historical)

> **Historical.** `jobs/ingest_places` loads the 20 fictional SF fixture places. It has no product role (D027). Under the pivot, branches are registered by the acquisition pipeline instead.

## 7. Database design

All user-owned tables include `user_id`, and `created_at`/`updated_at` where applicable. Timestamps are stored in UTC. Meal schedules also store an IANA time-zone name.

### 7.1 Implemented today (migrations 0001–0005)

Fourteen tables. Migration 0002 revokes Supabase Data API access (D014); 0003 adds response and visit constraints; 0004 adds `user_place_states.was_visited_before_nosh`; 0005 replaces `dining_contexts` with `meal_schedules` and `saved_anchors` (D020, D026), keys sessions by user, and adds the session candidate queue.

Under the pivot, the restaurant tables below (`user_place_states`, `visits`, and the place-shaped columns of `proposals`) become frozen, read-only history (D036). That is planned; today they are live.

#### `profiles`

- `user_id` UUID, primary key and Supabase Auth reference
- `display_name` nullable
- `onboarding_state`
- `deleted_at` nullable

`GET /v1/me` creates the profile on first access.

#### `meal_schedules`

One row per user and meal (D020, D026); the survey sets weekday lunch on and dinner off by default.

- `user_id`, `meal_type` (`lunch` or `dinner`) — composite primary key
- `enabled`
- `local_window_start`, `local_window_end`
- `time_zone`
- `active_days` integer array
- `price_ceiling` 1–4 (`$`–`$$$$`), NULL for no ceiling. Stored, but used nowhere in filtering or ranking. How it applies to dish offerings is open question 8.
- `notifications_enabled` — stored; nothing reads it yet
- `version`, incremented only when a stored value changes

Validation (D016; enforced by `PUT /v1/me/meal-schedule`, which replaces the whole schedule):

- `local_window_start` / `local_window_end` are strict 24-hour `HH:MM` (00:00–23:59);
- the window ends strictly after it starts on the same local day — overnight and empty windows are rejected;
- `time_zone` must load as an IANA zone;
- `active_days` is a non-empty list of unique integers 0–6 (0 = Monday, Python `weekday()`);
- two enabled meals that share an active day must not overlap (field `meals`), so at most one window is open at a time.

Failures return `422` with code `validation_error` and the offending `field`.

#### `saved_anchors`

- `user_id`, `kind` (`home` or `work`) — composite primary key
- `location` PostGIS geography point

Optional Home/Work spots that the API accepts as a session anchor (D020). The app never uses them today. The point is precise personal data: never log it; product-data deletion removes it. Whether these spots remain under the meal area (D035) is open question 11.

#### `places`

- `id` UUID
- `canonical_name`
- `location` PostGIS geography point
- `address`
- `status`
- `metadata` JSONB for non-critical source fields
- `created_at`, `updated_at`

Today it holds the 20 fixture places; names and addresses are stored and returned.

#### `place_sources`

- `id` UUID
- `place_id`
- `provider` (today only `fixture`)
- `provider_place_id`
- `source_updated_at`
- `last_seen_at`
- unique constraint on `(provider, provider_place_id)`

#### `cuisines`

- `id` UUID
- `slug` unique
- `display_name`
- `parent_id` nullable

#### `place_cuisines`

- `place_id`
- `cuisine_id`
- `is_primary`
- unique constraint on `(place_id, cuisine_id)`

#### `user_place_states`

- `user_id`
- `place_id`
- `state`: `unknown`, `visited`, or `not_interested`
- `source`: `been_here`, `confirmation`, `manual`, `import`, or (historical) `onboarding`
- `was_visited_before_nosh`: set only by Been here already (or historical onboarding Been); never reset
- `occurred_at`
- unique constraint on `(user_id, place_id)`

Writes are a single `INSERT … ON CONFLICT (user_id, place_id) DO UPDATE`, so concurrent first-time writes cannot fail, and `was_visited_before_nosh` is OR-ed with the stored value so provenance survives any writer order. Only a Been here already response records `source = been_here` and sets the flag (D018, D025); the manual settings edit and visit confirmation never do.

Today candidate building hard-excludes any place in state `visited` or `not_interested`. Planned (D036): "Been here" becomes a familiarity signal only, and a visited restaurant no longer excludes its dishes.

#### `suggestion_sessions`

- `id` UUID
- `user_id`
- `meal_window_key`
- `schedule_version` — the meal's `meal_schedules.version` at creation
- `anchor_source` — `device`, `home`, or `work` (`legacy_context` for migrated sessions); the coordinate itself is never stored
- `state` — `active`, `accepted`, `skipped`, `exhausted`, or `no_candidates`
- `policy_version`
- `candidate_queue` JSONB — ranked candidates not yet proposed
- `created_at`, `closed_at`
- unique constraint on `(user_id, meal_window_key)`

`meal_window_key` is `YYYY-MM-DD#meal_type`, the local calendar date in the meal schedule's time zone. Session creation rejects (`422 validation_error`, field `meal_window_key`) a key whose date is not a real calendar date, whose meal is not enabled in the user's schedule, or whose weekday is not an active day, and any schedule whose stored time zone or window is invalid. These checks run only when a session is created. Creation locks the user's `meal_schedules` row so concurrent requests insert one session.

At creation the API ranks every eligible candidate within 1,600 m of the anchor once (`policy_v0`, in the order successive Another responses would produce) and stores the list in `candidate_queue`; the first entry becomes proposal 1. Another and Been here already turn the next entry into a proposal, so the anchor point is never needed again. The queue holds place IDs, scores, and distances, so it is emptied when the session closes (Go, Not today, or exhaustion) and when the user opens a session for any other meal window.

#### `proposals`

- `id` UUID
- `suggestion_session_id`
- `place_id` — NOT NULL
- `cuisine_id` — NOT NULL
- `sequence_number`
- `total_score`
- `score_components` JSONB
- `reason_codes` text array
- `candidate_snapshot` JSONB
- unique constraint on `(suggestion_session_id, sequence_number)`

#### `proposal_responses`

- `id` UUID
- `proposal_id`
- `user_id`
- `response`: `go`, `another`, `not_today`, or `been_here`
- `client_event_id` unique
- `responded_at`
- unique constraint on `proposal_id` (one response per proposal)

Response writes lock the owning suggestion-session row before reading the stored response or session state, so concurrent responders are serialised:

- identical retry (same proposal and action) → the stored response is returned;
- a different action on an already-answered proposal, including the loser of a concurrent race → `409 conflict`, never `422 invalid_state_transition`;
- a reused `client_event_id` for another proposal or action → `409 conflict`; for another user → `403 forbidden`;
- `422 invalid_state_transition` is reserved for unanswered proposals in a closed session;
- integrity errors from any other constraint propagate unchanged;
- every replay (same event, or same action under a new event) returns a result equivalent to the original: Go → `accepted`, Not today → `skipped`, Another → the proposal it generated with `active`, or `exhausted` with `no_candidates: true` when it generated none — even if the session has since moved on.

#### `visits`

- `id` UUID
- `user_id`
- `place_id`
- `proposal_id` nullable
- `visited_at`
- `confirmation_source` (`app_confirmation` or `manual`)
- `rating`: positive or negative (required by the API at creation)
- `created_at`, `corrected_at`

A proposal-backed visit requires a prior `go` response on that exact proposal and a matching place. A visit without `proposal_id` (manual, D015) is accepted. `PATCH /v1/visits/{visit_id}` overwrites `rating` and/or `visited_at` and sets `corrected_at`; it keeps no history. `GET /v1/visits` pages in `(visited_at DESC, id DESC)` order. The cursor is the last visit ID of the previous page and must belong to the caller. A visit for an unknown `place_id` returns `404 not_found`.

#### `device_tokens`

- `id` UUID
- `user_id`
- `platform`
- `expo_push_token`
- `last_seen_at`
- `disabled_at` nullable

#### `notification_deliveries`

- `id` UUID
- `user_id`
- `suggestion_session_id` nullable
- `kind`
- `deduplication_key` unique
- `provider_message_id` nullable
- `state`
- `attempt_count`
- `scheduled_for`, `sent_at`

Nothing writes to `device_tokens` or `notification_deliveries` today.

### 7.2 Planned (not implemented)

> None of the tables in this section exist. They are the minimum set implied by D032–D040. Column-level design is not done; only purposes are described. All are created by additive migrations with tested downgrades, so existing data stays readable (D036).

**Three data classes (D034).** Every planned table except `dish_offering` (see below; open question 25) belongs to exactly one class:

1. **Shared catalog** (owned by Nosh): `dish`, `dish_alias`, `dish_trait`.
2. **Provider content** (from outside sources): `menu_item`, and the source-backed parts of `places`/`place_sources`. Every provider-content row is tagged with its source, retrieval date, and expiry, and all content from one source can be purged on its own.
3. **Personal data** (what a user tells Nosh or does in it): `user_dish_preference`, `dish_experience`, `reward`, and the meal area.

`dish_offering` links catalog to branch. It is Nosh's reviewed, published claim that a branch serves a dish, built from provider evidence; which data class it belongs to, and what happens to it when its source expires or is purged, are not decided (open question 25).

#### Shared catalog

- **`dish`** — the catalog's dishes and their variants (D040; how a variant is stored relative to its dish is open question 24). Dishes and variants have permanent IDs. Variants are one level deep: a variant is something that eats differently (a regional style, a different main protein, a different preparation). Merging two entries leaves a redirect from the old ID; splitting never moves a user's past experiences. The catalog is versioned. Cuisine comes from here, which replaces per-place cuisine labels for dish work. The target size is about 10,000 dishes.
- **`dish_alias`** — other names for a dish or variant (D040). Aliases have no IDs of their own: a name is not a different thing to eat. Used when mapping menu text to the catalog.
- **`dish_trait`** — facts about a dish or variant, such as its home country or ingredients (D040). Every fact is marked as generated, reviewed, or source-backed. The rule that each dish has exactly one home country for unlock purposes is **proposed, awaiting confirmation** (D039, open question 1); the catalog must not depend on it until confirmed.

#### Branch registry and provider content

- **`places` and `place_sources` (reused)** — become the registry of restaurant branches. A branch is one physical restaurant location. The existing fixture rows stay as history. Google content other than place IDs is not stored (D034, keeping the D022 rule).
- **`menu_item`** — one item as it appears on a source's menu for a branch (D034). Provider content: tagged with source, retrieval date, and expiry; purgeable per source. Menu evidence shows a dish is offered, not that it is good.

#### Published offerings

- **`dish_offering`** — the published link "this branch serves this dish (or variant)", created only after mapping and review (D034). Meal-time ranking reads only published offerings. Anything specific to how one restaurant prepares a dish lives here, not in the catalog (D040). A menu item that names only the dish is linked at dish level, not guessed into a variant.

#### Personal data

- **`user_dish_preference`** — what the user tells Nosh in dish onboarding, including explicit constraints the policy must never override (D032). What onboarding asks is not decided (open questions 10 and 20).
- **`dish_experience`** — the record that the user actually ate a dish at a branch, with "tried" and "enjoyed" as separate signals (D033, D038). It is the source of truth for novelty ("is this new to me?") and for taste evidence, which is derived from it rather than stored separately. Corrections are appended as new events; earlier records are not overwritten. Changing which dish was eaten re-evaluates both dishes; retracting an experience invalidates its reward.
- **`reward`** — a discovery reward earned from a dish experience (D038, D039). Inserted idempotently, so a retry cannot create a second reward. Each reward is individually valid or invalid; changing whether the dish was enjoyed never changes a reward. A cosmetic unlocks only for a dish from a country new to the user; a new dish or variant earns a journal entry and discovery moment, not a cosmetic.
- **Avatar — computed, not stored (D039).** The avatar is always computed from the currently valid rewards, so a retraction removes a cosmetic. There is no avatar table.

#### Changes to an existing table

- **`proposals`** gains a nullable reference to a dish offering, in an additive migration. Today `proposals.place_id` and `proposals.cuisine_id` are NOT NULL; the offering reference is decided (D032); whether dish proposals keep filling those two columns or the columns become nullable is open question 24.

#### To be designed (open questions, not tables)

These structures are needed but not decided. No table is added for them here.

- **Where the meal area is stored (D035).** It is a coarse cell, never a point. Cell size, confirmation, and retention are open question 11.
- **How variants are represented in `dish`** — for example, a parent reference on the same table or a separate structure (D040). Not decided (open question 24).
- **How system supersession of a proposal is recorded (D037)** — it must be distinct from user responses and carry a reason (open question 24).
- **How appended correction events for dish experiences are stored (D038)** — on `dish_experience` itself or in a separate event structure (open question 24).
- **How catalog merge redirects and catalog versions are stored (D040).** Version numbering is open question 17.
- **Source registry and per-source purge (D034)** — how sources, retrieval dates, and expiry are recorded so a purge can find everything from one source.

## 8. Planned data flows

> **Planned — none of these flows exist.** Today the app requests a session, `policy_v0` ranks fixture places, and the user confirms a restaurant visit.

```text
(1) OFFLINE ACQUISITION  (batch jobs; LLM allowed with evaluation sets, D041)

  sources ─► adapters ─► branch match ─► source-backed ─► mapping to ─► review ─► published
  (D042,      (one per    (places /       menu items       the catalog   (human)    offering
  undecided)  source)     place_sources)  (menu_item,      (dish,                   (dish_offering)
                                          tagged source,   dish_alias)
                                          date, expiry)

(2) MEAL-TIME RANKING  (deterministic; no LLM call, D006, D041)

  meal schedule ──┐
  meal area ──────┤      ┌──────────────────────┐
  (coarse cell)   ├─────►│ deterministic dish   │─► one proposal ─► scheduled delivery
  published ──────┤      │ ranking (versioned)  │   (proposals +     (dish named only when a
  offerings       │      └──────────────────────┘    offering ref)    meal area exists; else a
  live place ─────┘                                                  generic nudge, D035)
  status/hours
  (eligibility only: can make an offering ineligible now;
   never shows a restaurant serves a dish; provider undecided)

(3) OUTCOME  (one request, one transaction, D038)

  confirmation ─► ┌─────────────────────────────────────────────┐
  (actual dish,   │ write dish_experience                       │
   or "I ate      │ novelty check under a per-user lock         │
   something      │ insert rewards idempotently                 │
   else")         └──────────────────────┬──────────────────────┘
                                         ▼
                  derived taste evidence · journal · avatar computed from valid rewards
```

## 9. Transactions

### Implemented today

- Every service function that writes calls `db.commit()` itself. The request dependency does not commit. Read functions do not commit; `upsert_user_place_state` deliberately does not, so its caller's commit includes it. `GET /v1/me` commits because it creates the profile on first access.
- Recording a proposal response uses a savepoint around the insert so a uniqueness race can be interpreted without losing the session lock.
- `confirm_visit` does a full session rollback (not a savepoint) when it loses a uniqueness race, then re-reads the existing visit.
- `update_visit` overwrites `rating` and/or `visited_at` and sets `corrected_at`. It keeps no history and writes no event.

### Planned (D038, not implemented)

- Application services stop committing on their own. Each request commits exactly once.
- Confirming a meal is one transaction: write the dish experience, check novelty while holding a per-user lock, and insert rewards idempotently.
- Corrections are appended, never overwritten.
- This refactor happens before the dish experience is built.

## 10. API conventions

- Base path: `/v1`
- JSON field names: `snake_case`
- Identifiers: server-generated UUIDs
- Time values: RFC 3339 UTC timestamps; local schedules also include an IANA time zone
- Pagination: cursor-based when needed
- Errors: stable machine-readable code, human-readable message, and optional field details — `{"code", "message", "field"?}`. Schema validation failures use code `validation_error` with the first offending `field` and keep FastAPI's per-field list under `detail`. Unknown resources (including place IDs) return `404 not_found`.
- Writes from the mobile app carry a unique `client_event_id` or are idempotent by design (full-replacement `PUT`s)
- Authentication: Supabase bearer token
- Authorization: server-side ownership checks on every user resource
- API changes are reflected in OpenAPI in the same pull request (and in the generated TypeScript client once it exists)

### Endpoints implemented today

```text
GET    /v1/me
DELETE /v1/me/product-data

GET    /v1/me/meal-schedule
PUT    /v1/me/meal-schedule            # full replacement; idempotent
GET    /v1/me/anchors
PUT    /v1/me/anchors/{kind}           # home | work
DELETE /v1/me/anchors/{kind}

PUT    /v1/places/{place_id}/state     # manual settings edit

POST   /v1/suggestion-sessions
GET    /v1/suggestion-sessions/{session_id}
POST   /v1/proposals/{proposal_id}/responses

POST   /v1/visits
PATCH  /v1/visits/{visit_id}
GET    /v1/visits
GET    /v1/progress

GET    /health/live
GET    /health/ready
```

There are no device routes. The proposal, session, and visit responses are place-shaped (`place_id`, `place_name`, `cuisine_name`, `distance_meters`, `address`). `GET /v1/progress` reports the superseded D002 restaurant metric.

`POST /v1/suggestion-sessions` takes `meal_window_key` and exactly one anchor: `location` (`{latitude, longitude}`, transient, never logged or stored) or `anchor` (`home` or `work`; `422 anchor_not_set` if that spot is not saved). A repeat request for the same user and meal window returns the existing session whatever anchor it carries, always with HTTP 201. Creating a session empties the candidate queues of the user's other sessions.

`POST /v1/proposals/{proposal_id}/responses` accepts `go`, `another`, `not_today`, and `been_here`. Been here already (D025) marks the place visited before Nosh and advances to the next proposal like Another; it is stored as its own response.

**Planned (not implemented):** device registration routes; routes for dish onboarding, the dish card, dish confirmation and corrections, rewards, the journal, and the avatar; and retirement of the visit and place-state write endpoints (timing is open question 15). Route shapes are not designed.

## 11. Suggestion sessions and state machine

### Implemented today

```text
active ── Another / Been here already ──► active with next proposal
  │  │                                    (exhausted when none remain)
  │  └── Not today ─► skipped   (session closed, queue emptied)
  │
  └── Go ───────────► accepted  (session closed, queue emptied)
                         │
                         ▼
                   visit confirmation (client screen)
                         ├── Yes ──► POST /v1/visits (visit + rating)
                         ├── No ───► client only; nothing sent or stored
                         └── Later ► client only; nothing sent or stored

no candidates at creation ─► no_candidates
```

State transitions are validated by the server, and duplicate requests return the already-recorded result. "No, I didn't go" and "Remind me later" exist only in the app. The "No" screen says the place will be suggested again, but nothing makes that happen.

### Planned (D037, not implemented)

- One session per user and meal window stays.
- Go is final for that window; there is no "change my pick".
- The system may supersede an **unanswered** proposal (for example, the meal area changed or the offering went stale). This is recorded separately from user responses, with a reason, so it is never read as user feedback. How it is recorded is to be designed (section 7.2).
- An accepted proposal is never replaced silently. If an accepted offering goes stale, the user sees a notice.
- If the user ate something else, they say so at confirmation (open question 13).
- What Another, Not today, and "Been here" teach the dish policy is open (open question 9).

## 12. Authentication and authorization

Implemented today:

- Supabase Auth provides passwordless email authentication.
- The mobile app is configured with only the Supabase project URL and the project's **publishable** key (the client-safe key that replaces the legacy `anon` key); it never holds a secret or service-role key. It obtains a user access token (Supabase JWT).
- Mobile sign-in is a one-time email code (`signInWithOtp` then `verifyOtp` with type `email`), which works when the email is opened on another device. The Supabase email templates for sign-in and sign-up must include `{{ .Token }}`.
- One `AuthProvider` (`apps/mobile/src/auth/`) owns the session for the whole app. The session persists in the iOS Keychain through `expo-secure-store`, split into chunks because a session can exceed SecureStore's 2 KB per-value limit. Tokens auto-refresh only while the app is in the foreground, and every API request reads the current access token.
- Query keys are scoped by user ID, and in-flight queries are cancelled and the query cache cleared whenever the signed-in user changes (sign-in, sign-out, account switch, data deletion), so one account's data is never shown to another.
- The mobile app runs in local-dev mode (UUID sign-in) when no Supabase URL and key are configured; it must match the API's `AUTH_LOCAL_DEV` setting.
- FastAPI validates signature, expiry, issuer (`{SUPABASE_URL}/auth/v1`), audience (`authenticated`), role (`authenticated`), and UUID subject. `SUPABASE_URL` is required in production mode.
- Signature verification uses the project's JWKS (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, RS256/ES256 asymmetric signing keys), so the API needs no shared JWT secret. `SUPABASE_JWT_SECRET` (HS256) exists only for projects still on the legacy shared secret; leave it empty for new projects.
- Local/test environments use a UUID-bypass adapter (`AUTH_LOCAL_DEV=true`) restricted to loopback database hosts and guarded by `APP_ENVIRONMENT`.
- The Supabase Data API is blocked at the database level (migration 0002 revokes all privileges from the `anon` and `authenticated` roles; D014).
- FastAPI connects as the postgres superuser (local Docker) or a Supabase service-role credential (production, planned).
- The mobile app does not directly write product tables.
- Database row-level security is defense in depth, not a substitute for API authorization.

## 13. Account and data deletion

### Implemented today

`DELETE /v1/me/product-data` removes product data: visits, notification deliveries, suggestion sessions with their proposals and responses, meal schedules, saved anchors, place states, device tokens, and the profile. It does **not** delete the Supabase sign-in identity; that needs a service-role credential and is not implemented.

### Planned (not implemented)

Deletion must also remove:

- the new personal tables: `user_dish_preference`, `dish_experience`, and `reward`;
- the meal area, wherever it is stored (D035);
- pending and scheduled notifications for the user;
- the sign-in identity. The mechanism is not designed (open question 18).

The shared catalog and provider content are not personal data and are not removed by a user's deletion. Provider content is instead purgeable per source (D034).

## 14. Notifications

### Implemented today

Two tables only (`device_tokens`, `notification_deliveries`). There is no worker, no device route, and no push sending. `meal_schedules.notifications_enabled` is stored. `expo-notifications` is installed in the app but not imported.

### Planned (D035, not implemented)

- When the user has a meal area, a meal-time notification may name the proposed dish.
- When no meal area exists, the notification is a generic nudge (D035). How and when the suggestion is then produced is not decided (open questions 11 and 12).
- Put only opaque identifiers and non-sensitive display text in the payload.
- Confirmation prompts deep-link to the stored suggestion session.
- Use a unique deduplication key per user, meal window, and notification kind.
- Keep the in-app flow usable when notification permission is denied.
- Send time, payload content, and actions are open (open question 12).

> **Superseded:** D023 (notifications are location-free nudges that never name a place) was superseded by D035 before it was implemented.

## 15. Location

- **Today:** the API accepts a transient `location` or a saved `home`/`work` anchor per session (D017, D020); the coordinate is never stored or logged. The app always sends a hard-coded San Francisco point.
- **Planned (D035):** the user confirms a coarse meal area per meal, stored as a coarse cell and never as a point. The app revalidates it with foreground location when opened. Background location, geofencing, and continuous tracking remain prohibited (D010, D017).

## 16. LLM boundary (D041, not implemented)

- LLMs may be used **offline only**: for catalog generation and for mapping menu items to the catalog. Each use has its own evaluation set (pass marks are open question 17).
- LLM output enters the product only as stored facts marked generated, reviewed, or source-backed (D040), and through reviewed offerings (D034).
- Meal-time ranking stays deterministic and makes no LLM call.
- No microservices, graph database, vector service, or event platform. pgvector stays absent (D013).
- Untrusted provider text is never placed into a model prompt without isolation and validation.
- Tracing for offline LLM jobs is kept separate from the deterministic recommendation path.

No LLM is used anywhere in the code today.

## 17. Testing strategy

Run the checks in `README.md` for current results; this document does not record test counts.

### Unit tests

- score functions and policy priors;
- hard-filter invariants;
- state-machine transitions;
- time-window and daylight-saving calculations;
- response semantics;
- serialization and validation.

### Integration tests

- PostGIS radius queries;
- migrations from an empty database, with rollback;
- idempotent session and response writes, including genuine concurrent-database tests;
- authorization boundaries;
- product-data deletion cleanup.

Planned additions: notification deduplication; single-commit confirmation with idempotent rewards under concurrency; correction and retraction re-evaluating rewards; per-source purge; deletion of the new personal tables.

### Contract tests (planned)

- OpenAPI schema generation;
- generated TypeScript client is current;
- supported mobile-client version behaviour.

### Evaluation tests

- Retain the existing cuisine-policy simulator as a regression and mechanism test.
- Compare policy versions on common synthetic or logged sessions.
- Today: prevent release if a policy recommends visited or ineligible places.
- Planned: evaluation sets for catalog generation and menu mapping (D041); the dish policy never recommends an offering that is unpublished, ineligible, or against an explicit constraint.

## 18. Environments and deployment

### Local (implemented)

- Docker Compose PostgreSQL with PostGIS: `db` (port 5432, development data) and `db_test` (port 5433, disposable, `--profile test`); pgvector absent (D013)
- FastAPI development server
- Expo app in local-dev or Supabase sign-in mode
- deterministic fixture data

### Shared development (planned)

- separate Supabase project
- deployed API container
- Expo development build
- synthetic or consenting tester data only

### Production/TestFlight (planned)

- separate Supabase project with PostGIS
- API on Fly.io, connecting through Supabase's direct or session connection (not the transaction pooler); `alembic upgrade head` as a release step (D030)
- migration-only database changes through CI/CD
- protected secrets
- EAS/TestFlight build with bundle identifier `com.winstontang.nosh` (D029)
- backups and the account-deletion procedure tested before inviting users

The API remains a standard container with environment-based configuration; no Fly-specific service becomes a core dependency (D012, D030).

## 19. Observability

- Structured logs with request ID, user pseudonymous ID, endpoint, duration, and error code
- No precise coordinates, email addresses, access tokens, or free-form personal text in logs
- Planned metrics: API errors, job failures, notification failures, no-candidate sessions, recommendation latency, and (offline) acquisition and mapping job outcomes
- Persist product events in first-party tables before adding a third-party analytics SDK

## 20. Security and privacy

- Least-privilege credentials per environment
- TLS for all remote traffic
- Secrets outside the repository
- Coordinates excluded from routine logs and error reports; the planned meal area is a coarse cell, never a point
- Explicit account deletion and scheduled-job cancellation
- Provider content tagged with source, retrieval date, and expiry, and purgeable per source (planned, D034)
- Each source's license rules represented in acquisition and display code once its rights are established (D042)
- Untrusted provider text never inserted into model prompts without isolation and validation

## 21. Evolution path

Add complexity only when evidence requires it:

1. Hand-verified San Mateo offering index → measured sources chosen by the D042 experiment
2. Simple worker polling → managed scheduled jobs or a queue
3. Factual reason codes → grounded explanations
4. Structured filters → hybrid search (would add pgvector; deferred per D013)
5. Private cohort → public App Store readiness
6. Later extension points only, with nothing built now: Nosh Meals and social features (including group preferences)

## 22. Provider terms constraints

> **Superseded as the supply model.** D021 (Google Places end to end) and D022 (store only provider IDs) were superseded by D034 before a Google provider was built. Their detailed rules (one provider in the meal-time path, live fetches, field masks, free-tier quotas) no longer describe the plan. The evidence in `docs/research/2026-10-20-place-data-and-map-terms.md` is kept as historical research.

Rules that still stand:

- **Google content other than place IDs is not stored** (D034, keeping the D022 rule).
- **Every item of provider content is tagged** with its source, retrieval date, and expiry, and each source's content can be purged on its own (D034).
- **Rights are measured, not assumed.** Whether any source's content may be stored, processed, or displayed is established per source by the D042 experiment. This document asserts no vendor's rights, prices, or coverage.
- **Keys** stay in server configuration or are restricted to the app's bundle identifier, and are never logged.
- **Tests and CI** use fixture data and need no provider key.

Still open: which map the dish card shows and which maps app Go opens (open question 5; the code opens Apple Maps), and which provider supplies live status and hours and what its terms require of the card (open question 4).

## 23. Open questions

These are not decided. The canonical list is "Open questions" in DECISIONS.md; the numbers below refer to it.

- Live place status/hours provider and its terms (4); map and handoff (5).
- Sources and their rights (3); budget (2).
- Policy weights, restaurant quality signal, price ceiling, and response meanings for dishes (6–9).
- Explicit constraints (10); meal area cell size, confirmation, retention, and Home/Work spots (11); notifications (12); "I ate something else" (13).
- One home country per dish (1); avatar and journal content (16); catalog review process, evaluation sets, and version numbering (17).
- Legacy screens and retiring the visit and place-state write endpoints (15).
- Sign-in identity deletion mechanism (18).
- Where unfinished tester-readiness work and the Fly.io deployment fall in the new milestone order (19).
- What "active user" means for the North Star (14); initial dish preferences (20); repetition (21); whether a new variant counts toward the North Star (22); what happens when nothing is eligible (23).
- **Planned schema details (24):** how variants are stored relative to dishes (D040); how a system-superseded proposal and its reason are recorded, distinct from `proposal_responses` (D037); whether appended corrections live on `dish_experience` or in a separate event structure (D038); whether dish proposals keep filling `place_id` and `cuisine_id` or those columns become nullable.
- **Offerings and purged content (25):** what happens to a published `dish_offering` when the provider content behind it expires or is purged, and which data class an offering belongs to (D034).
