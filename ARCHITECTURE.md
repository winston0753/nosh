# Nosh Architecture

- **Status:** Phase-one baseline
- **Version:** 0.1
- **Last updated:** 2026-10-20

## 1. Architecture goals

- Deliver the complete suggestion-to-confirmation loop with minimal operational complexity.
- Keep recommendation behavior deterministic, testable, and reconstructable.
- Preserve a clean boundary for later language and retrieval features.
- Support local development and a small private TestFlight cohort.
- Keep user location, preferences, and visit history private by default.

## 2. Non-goals

Phase one does not require microservices, a message broker, a separate vector database, real-time streaming infrastructure, an agent framework, or a globally replicated system.

## 3. System overview

```text
┌─────────────────────────────┐
│ Expo React Native app       │
│ iOS-first, TypeScript       │
└──────────────┬──────────────┘
               │ HTTPS / JSON
               ▼
┌─────────────────────────────┐
│ FastAPI modular monolith    │
│                             │
│ API and auth boundary       │
│ Product workflows           │
│ Recommendation module       │
│ Notification scheduling     │
│ Place administration        │
│ Evaluation commands         │
└───────┬─────────────┬───────┘
        │             │
        │             ├──────────► Expo Push Service
        │             └──────────► Google Places API (planned, D021)
        ▼
┌─────────────────────────────┐
│ Supabase PostgreSQL         │
│ PostGIS enabled             │
│ pgvector deferred (absent)  │
│ Supabase Auth               │
└─────────────────────────────┘
```

## 4. Technology choices

### Mobile

- Expo and React Native
- TypeScript with strict checking
- Expo Router
- TanStack Query
- `expo-notifications`
- Typed API client, currently hand-written in `apps/mobile/src/api/`; generation from OpenAPI into `packages/api-client/` is planned and not yet implemented
- Planned for Milestone 3: `expo-location` (foreground, when-in-use only) and a Google map view on the suggestion card (D020, D021)
- EAS development builds and TestFlight

### API

- Python 3.11+ (`requires-python`); CI runs 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic migrations
- PostgreSQL driver with async support
- `uv` for dependency and environment management
- pytest

### Data

- Supabase-hosted PostgreSQL in shared development and production environments
- Local PostgreSQL in Docker Compose
- PostGIS geography points and GiST indexes for radius queries
- pgvector deferred (see DECISIONS.md D013); not installed in the postgis/postgis image

### Operations

- One API container
- One lightweight scheduler/worker process built from the same codebase
- Structured JSON logs
- GitHub Actions for linting, typing, tests, migration checks, and simulator regression
- API hosting provider remains replaceable and will be selected before shared staging

## 5. Repository layout

```text
nosh/
├── apps/
│   └── mobile/
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── auth/
│       │   ├── contexts/
│       │   ├── places/
│       │   ├── recommendations/
│       │   ├── suggestions/
│       │   ├── visits/
│       │   ├── notifications/
│       │   └── core/
│       ├── tests/
│       └── jobs/            # same uv project and `app` package as the API
│           └── ingest_places/
├── db/
│   └── migrations/
├── packages/
│   └── api-client/          # placeholder; generated client not yet implemented
├── spike/
├── tests/
├── PRODUCT.md
├── ARCHITECTURE.md
├── RECOMMENDATIONS.md
├── DECISIONS.md
└── notes.md
```

Jobs live inside `services/api/jobs/` and import the application as the top-level `app` package, exactly like the API and its tests. Run them from `services/api` as `uv run --frozen python -m jobs.<job>.<module>`; never import through `services.api.app`. Future jobs (`schedule_notifications`, `evaluate_policy`) join the same package. The directories describe ownership boundaries, not independently deployed microservices.

## 6. Component responsibilities

### Mobile application

- Account session and onboarding UI
- Meal-schedule survey and settings (D020; currently dining-context configuration)
- Foreground location at use time, with optional Home/Work spots as the fallback (D017, D020)
- Current suggestion display
- Notification registration and deep links
- Go, Another, and Not today actions
- Google Maps handoff (D021; currently Apple Maps)
- Visit confirmation and rating
- History, progress, and privacy controls
- Local persistence of session and proposal identifiers and queued response writes; provider content is not cached (D022)

The mobile client contains presentation logic, not recommendation logic.

### FastAPI application

- Validate Supabase access tokens
- Enforce user ownership
- Implement product workflows and state transitions
- Generate and version recommendations
- Manage place and visit records
- Schedule and send notifications
- Expose product metrics to internal evaluation commands
- Produce the OpenAPI contract used to generate the TypeScript client

### Scheduler/worker

- Find users whose meal windows are approaching
- Send at most one location-free nudge per user and meal window; the suggestion is created when the user opens the app (D023)
- Create due visit-confirmation prompts
- Retry transient failures with bounded backoff
- Ignore disabled contexts and deleted users

The initial worker may poll PostgreSQL on a short interval. A message broker is not required at phase-one scale.

### Recommendation module

- Load eligible candidates
- Apply hard filters
- Score cuisines and places
- Persist score components and policy version
- Return the chosen proposal and factual reason codes
- Contain no network or LLM dependency in the decision path: the suggestion service fetches provider candidates first and passes them to pure ranking functions

### Place administration and ingestion

> Superseded for product data by D021 and D027: candidates come live from Google Places, and the fixture importer survives only to load test data until a fixture place provider replaces it.

- Import curated CSV or JSON fixtures
- Normalize source identifiers and cuisine labels
- Detect duplicate source identifiers
- Support manual correction and deactivation
- Preserve source and refresh timestamps

## 7. Database design

This section describes the implemented schema (migrations 0001–0004). Accepted changes that are not yet implemented:

- **D020:** `dining_contexts` is replaced by a per-user meal schedule and optional Home/Work anchors; `suggestion_sessions` becomes unique on `(user_id, meal_window_key)`.
- **D021/D022:** `places` becomes a registry of provider identifiers (Google `place_id`) without stored names, addresses, or metadata; a session stores its ranked list of place identifiers; `proposals.candidate_snapshot` keeps only identifiers, ranks, and Nosh-owned components.
- **D025:** a Been here already event records `was_visited_before_nosh` from the card.

All user-owned tables include `user_id`, `created_at`, and `updated_at` where applicable. Timestamps are stored in UTC. Dining contexts also store an IANA time-zone name.

### `profiles`

- `user_id` UUID, primary key and Supabase Auth reference
- `display_name` nullable
- `onboarding_state`
- `deleted_at` nullable

### `dining_contexts`

- `id` UUID
- `user_id`
- `name`
- `meal_type`
- `location` PostGIS geography point
- `radius_meters`
- `local_window_start`
- `local_window_end`
- `time_zone`
- `active_days` integer array or bit mask
- `notifications_enabled`
- `version`
- `disabled_at` nullable

Create a GiST index on `location`. Do not include precise coordinates in application logs.

Validation (DECISIONS.md D016; enforced on create and update):

- `local_window_start` / `local_window_end` are strict 24-hour `HH:MM` (00:00–23:59);
- the window ends strictly after it starts on the same local day — overnight and empty windows are rejected;
- `time_zone` must load as an IANA zone;
- `active_days` is a non-empty list of unique integers 0–6 (0 = Monday, Python `weekday()`);
- PATCH re-checks the window against the stored bound when only one bound changes.

Failures return `422` with code `validation_error` and the offending `field`.

### `places`

- `id` UUID
- `canonical_name`
- `location` PostGIS geography point
- `address`
- `status`
- `metadata` JSONB for non-critical source fields
- `created_at`, `updated_at`

### `place_sources`

- `id` UUID
- `place_id`
- `provider`
- `provider_place_id`
- `source_updated_at`
- `last_seen_at`
- unique constraint on `(provider, provider_place_id)`

### `cuisines`

- `id` UUID
- `slug` unique
- `display_name`
- `parent_id` nullable

### `place_cuisines`

- `place_id`
- `cuisine_id`
- `is_primary`
- unique constraint on `(place_id, cuisine_id)`

### `user_place_states`

- `user_id`
- `place_id`
- `state`: `unknown`, `visited`, or `not_interested`
- `source`: onboarding, confirmation, manual edit, or import
- `was_visited_before_nosh`: set only by an onboarding Been classification; never reset
- `occurred_at`
- unique constraint on `(user_id, place_id)`

Writes are a single `INSERT … ON CONFLICT (user_id, place_id) DO UPDATE`, so concurrent first-time writes cannot fail, and `was_visited_before_nosh` is OR-ed with the stored value so provenance survives any writer order. Only `PUT /v1/contexts/{context_id}/onboarding-places/{place_id}/state` records `source = onboarding` and can set the flag (DECISIONS.md D018); the manual settings edit and visit confirmation never do.

### `suggestion_sessions`

- `id` UUID
- `user_id`
- `dining_context_id`
- `context_version`
- `meal_window_key`
- `state`
- `policy_version`
- `created_at`, `closed_at`
- unique constraint on `(dining_context_id, meal_window_key)`

`meal_window_key` is `YYYY-MM-DD#meal_type`, the local calendar date in the context's time zone. Session creation rejects (`422 validation_error`, field `meal_window_key`) a key whose date is not a real calendar date, whose meal type differs from the context's, or whose weekday is not an active day, and any context whose stored time zone or window is invalid.

### `proposals`

- `id` UUID
- `suggestion_session_id`
- `place_id`
- `cuisine_id`
- `sequence_number`
- `total_score`
- `score_components` JSONB
- `reason_codes` text array
- `candidate_snapshot` JSONB
- unique constraint on `(suggestion_session_id, sequence_number)`

### `proposal_responses`

- `id` UUID
- `proposal_id`
- `user_id`
- `response`: `go`, `another`, or `not_today`
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

### `visits`

- `id` UUID
- `user_id`
- `place_id`
- `proposal_id` nullable
- `visited_at`
- `confirmation_source`
- `rating`: positive or negative
- `created_at`, `corrected_at`

`GET /v1/visits` pages in `(visited_at DESC, id DESC)` order. The cursor is the last visit ID of the previous page and must belong to the caller; the unique ID tie-breaker means visits sharing a timestamp are never skipped or repeated. A visit for an unknown `place_id` returns `404 not_found`.

### `device_tokens`

- `id` UUID
- `user_id`
- `platform`
- `expo_push_token`
- `last_seen_at`
- `disabled_at` nullable

### `notification_deliveries`

- `id` UUID
- `user_id`
- `suggestion_session_id` nullable
- `kind`
- `deduplication_key` unique
- `provider_message_id` nullable
- `state`
- `attempt_count`
- `scheduled_for`, `sent_at`

## 8. API conventions

- Base path: `/v1`
- JSON field names: `snake_case`
- Identifiers: server-generated UUIDs
- Time values: RFC 3339 UTC timestamps; local schedules also include an IANA time zone
- Pagination: cursor-based when needed
- Errors: stable machine-readable code, human-readable message, and optional field details — `{"code", "message", "field"?}`. Schema validation failures use code `validation_error` with the first offending `field` and keep FastAPI's per-field list under `detail`. Unknown resources (including place IDs) return `404 not_found`.
- Writes from the mobile app require an `Idempotency-Key` or unique `client_event_id`
- Authentication: Supabase bearer token
- Authorization: server-side ownership checks on every user resource
- API changes are reflected in OpenAPI and the generated TypeScript client in the same pull request

### Initial endpoints

```text
GET    /v1/me
DELETE /v1/me/product-data

GET    /v1/contexts
POST   /v1/contexts
PATCH  /v1/contexts/{context_id}
DELETE /v1/contexts/{context_id}

GET    /v1/contexts/{context_id}/onboarding-places
PUT    /v1/contexts/{context_id}/onboarding-places/{place_id}/state   # onboarding classification
PUT    /v1/places/{place_id}/state                                    # manual settings edit

POST   /v1/suggestion-sessions
GET    /v1/suggestion-sessions/{session_id}
POST   /v1/proposals/{proposal_id}/responses

POST   /v1/visits
PATCH  /v1/visits/{visit_id}
GET    /v1/visits
GET    /v1/progress

POST   /v1/devices                     # Milestone 4; not implemented
DELETE /v1/devices/{device_id}         # Milestone 4; not implemented
```

Sixteen routes are implemented today (the list above minus the two device routes). D020, D021, and D025 replace the context and onboarding routes and add a Been here already write; their contracts are designed with the implementation.

`POST /v1/suggestion-sessions` returns the existing session if the same dining context and meal-window key are submitted again.

## 9. Suggestion state machine

```text
scheduled
    │
    ▼
active ── Another ──► active with next proposal
  │  │
  │  └── Not today ─► skipped
  │
  └── Go ───────────► accepted ─► awaiting confirmation
                                      │
                                      ├── Yes ─► visited and rated
                                      ├── No ──► not visited
                                      └── Later ► awaiting confirmation
```

State transitions are validated by the server. Duplicate requests return the already-recorded result.

## 10. Authentication and authorization

- Supabase Auth provides passwordless email authentication.
- The mobile app is configured with only the Supabase project URL and the project's
  **publishable** key (the client-safe key that replaces the legacy `anon` key); it never
  holds a secret or service-role key. It obtains a user access token (Supabase JWT).
- Mobile sign-in is a one-time email code (`signInWithOtp` then `verifyOtp` with type
  `email`), which works when the email is opened on another device. The Supabase email
  templates for sign-in and sign-up must include `{{ .Token }}`.
- One `AuthProvider` (`apps/mobile/src/auth/`) owns the session for the whole app. The
  session persists in the iOS Keychain through `expo-secure-store`, split into chunks
  because a session can exceed SecureStore's 2 KB per-value limit. Tokens auto-refresh
  only while the app is in the foreground, and every API request reads the current access
  token.
- Query keys are scoped by user ID, and in-flight queries are cancelled and the query
  cache cleared whenever the signed-in user changes (sign-in, sign-out, account switch,
  data deletion), so one account's data is never shown to another.
- The mobile app runs in local-dev mode (UUID sign-in) when no Supabase URL and key are
  configured; it must match the API's `AUTH_LOCAL_DEV` setting.
- FastAPI validates: signature, expiry, issuer ({SUPABASE_URL}/auth/v1), audience
  (authenticated), role (authenticated), and UUID subject. SUPABASE_URL is required in
  production mode.
- Signature verification uses the project's JWKS
  ({SUPABASE_URL}/auth/v1/.well-known/jwks.json, RS256/ES256 asymmetric signing keys), so
  the API needs no shared JWT secret. `SUPABASE_JWT_SECRET` (HS256) exists only for projects
  still on the legacy shared secret; leave it empty for new projects.
- Local/test environments use a UUID-bypass adapter (AUTH_LOCAL_DEV=true) restricted to
  loopback database hosts; guarded by APP_ENVIRONMENT.
- The Supabase Data API is blocked at the database level (migration 0002 revokes all
  privileges from anon and authenticated roles; see DECISIONS.md D014).
- FastAPI connects as the postgres superuser (local Docker) or Supabase service-role (production).
- The mobile app does not directly write product tables.
- Database row-level security is defense in depth, not a substitute for API authorization.
- Full identity deletion (Supabase Auth user) requires a service-role credential and is not
  yet implemented.  The DELETE /v1/me/product-data endpoint removes product data only.

## 11. Notifications

- Register device tokens in the mobile app.
- The meal-time notification is a location-free nudge; it names no restaurant, and the suggestion is created after the user opens the app (D023).
- Put only opaque identifiers and non-sensitive display text in the payload.
- Visit-confirmation prompts deep-link to the stored suggestion session.
- Use a unique deduplication key per user, meal window, and notification kind.
- Keep the in-app flow usable when notification permission is denied.

## 12. Testing strategy

### Unit tests

- score functions and policy priors;
- hard-filter invariants;
- state-machine transitions;
- time-window and daylight-saving calculations;
- response semantics;
- serialization and validation.

### Integration tests

- PostGIS radius queries;
- migrations from an empty database;
- idempotent session and response writes;
- authorization boundaries;
- notification deduplication;
- account deletion cleanup.

### Contract tests

- OpenAPI schema generation;
- generated TypeScript client is current;
- supported mobile-client version behavior.

### Evaluation tests

- retain the existing simulator as a regression and mechanism test;
- compare policy versions on common synthetic or logged sessions;
- prevent release if a policy recommends visited or ineligible places.

## 13. Environments and deployment

### Local

- Docker Compose PostgreSQL with PostGIS (pgvector deferred and absent; D013)
- FastAPI development server
- Expo development build
- deterministic fixture data

### Shared development

- separate Supabase project
- deployed API container
- Expo development build
- synthetic or consenting tester data only

### Production/TestFlight

- separate Supabase project
- migration-only database changes through CI/CD
- protected secrets
- EAS/TestFlight build
- backups and account-deletion procedure tested before inviting users

The API hosting vendor is deliberately deferred. The API must remain a standard container with environment-based configuration.

## 14. Observability

- Structured logs with request ID, user pseudonymous ID, endpoint, duration, and error code
- No precise coordinates, email addresses, access tokens, or free-form personal text in logs
- Metrics for API errors, job failures, notification failures, no-candidate sessions, and recommendation latency
- Persist product events in first-party tables before adding a third-party analytics SDK
- Add tracing to future LLM components separately from the deterministic recommendation path

## 15. Security and privacy

- Least-privilege credentials per environment
- TLS for all remote traffic
- Secrets outside the repository
- Coordinates excluded from routine logs and error reports
- Explicit account deletion and scheduled-job cancellation
- Provider licensing rules represented in ingestion and display code
- Untrusted provider text never inserted into future model prompts without isolation and validation

## 16. Evolution path

Add complexity only when evidence requires it:

1. Curated fixtures → repeatable place ingestion
2. Simple worker polling → managed scheduled jobs or queue
3. Factual reason codes → grounded explanation service
4. Structured craving filters → hybrid search (adds pgvector, deferred per D013)
5. Single-person context → group preference model
6. Private cohort → public App Store readiness

## 17. Provider terms constraints

Canonical rules from D021 and D022; evidence and quotations are in `docs/research/2026-10-20-place-data-and-map-terms.md`.

- **One provider in the meal-time path.** Google Places content may not be used in conjunction with a non-Google map (Service Specific Terms §14.2; ToS §3.2.3(e)). The card uses a Google map with Google attribution, and Go opens Google Maps. Do not mix Apple Maps data, maps, or handoff with Google-selected places.
- **Store only identifiers.** Persist the Google `place_id` and Nosh-owned data (user states, responses, visits, ratings, Nosh chain-list matches, ranks, and components computed from Nosh-owned inputs). Never persist names, addresses, ratings, review counts, hours, types, or values derived from them, in the database, logs, analytics, or device caches.
- **Fetch live.** Card and history details are fetched when displayed. A failed fetch shows an explicit retry state, never stale stored content.
- **Explicit field masks.** Request only the fields the policy needs; the most expensive field sets the billed SKU.
- **Quotas.** Configure Google Cloud quotas and billing alerts at the free-tier limits in D028.
- **Keys.** The server key stays in API configuration; the iOS Maps SDK key is restricted to the app's bundle identifier. Neither is logged.
- **Tests and CI** use a fixture place provider and need no provider key.
- **Open ambiguity.** Whether filtering and re-ranking Places results counts as modifying search results (ToS §3.2.3(g)) must be clarified with Google before any public launch.
