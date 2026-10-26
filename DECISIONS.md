# Nosh Decision Log

- **Status:** Active
- **Last updated:** 2026-10-20

This file records product and architecture decisions that affect multiple parts of the system. Each entry includes the selected option, rejected alternatives, consequences, and conditions for reconsideration.

Detailed historical ADRs may remain under `docs/decisions/`; this file is the canonical index and current decision state.

## D001 — Name the product Nosh

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Name the product and repository `Nosh`.

### Alternatives considered

- **Forage:** strong discovery metaphor but does not directly evoke eating or consumption.
- **Tuck, Crumb, Morsel, Savor, Bite:** useful candidates with different tone and positioning tradeoffs.
- **Toast-like spelling variants:** rejected because they would be derivative and potentially confusing with the established Toast brand.

### Consequences

The repository, package metadata, and documents use Nosh. The name still requires trademark, domain, App Store, and handle checks before public launch.

## D002 — Optimize confirmed positive new visits

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Use confirmed positively rated new restaurants per monthly active user as the North Star.

### Alternatives rejected

- **Distinct restaurants tried:** rewards bad experiences.
- **Been-to percentage:** unstable for small categories and confounded with taste.
- **Go taps or Maps opens:** measures intent rather than real visits.

### Consequences

Phase one requires visit confirmation and a quality signal. Suggestions and handoffs alone do not count as successful outcomes.

## D003 — Build an Expo iOS-first client

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Use Expo React Native with TypeScript for the phase-one mobile client and distribute through TestFlight.

### Alternatives rejected

- **Native SwiftUI:** stronger access to the newest iOS features but adds a second unfamiliar application language and slower cross-platform iteration.
- **Responsive web app:** insufficient proof of the notification-centered mobile experience.

### Consequences

The design must stay within Expo-supported notification and deep-link behavior unless a specific native capability justifies a config plugin or native module.

## D004 — Use a FastAPI modular monolith

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Build one FastAPI service with internal modules for contexts, places, suggestions, recommendations, visits, notifications, and users.

### Alternatives rejected

- **Microservices:** unjustified operational cost and distributed failure modes at private-cohort scale.
- **Backend logic only in Supabase functions:** weakens the Python recommendation and evaluation workflow.
- **Node-only backend:** possible, but it would split the existing Python simulation from the production policy.

### Consequences

Module boundaries must remain explicit, but deployment stays simple. A component becomes a separate service only after measured scaling or reliability pressure.

## D005 — Use Supabase PostgreSQL with PostGIS

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Use Supabase for hosted PostgreSQL and passwordless authentication. Enable PostGIS for radius queries. pgvector is deferred and absent in phase one (superseded by D013); vector retrieval is out of scope.

### Alternatives rejected

- **SQLite as the shared database:** insufficient for geospatial queries and concurrent hosted use.
- **Separate geospatial and vector databases:** unnecessary complexity.
- **Direct client access for all product writes:** makes recommendation state transitions and authorization harder to centralize.

### Consequences

The mobile app authenticates with Supabase using only the project URL and the client-safe publishable key, but the FastAPI service owns product writes and recommendation workflows. FastAPI verifies access tokens against the project's JWKS (asymmetric signing keys) and needs no shared JWT secret; the HS256 `SUPABASE_JWT_SECRET` path remains only for projects still on the legacy secret.

## D006 — Keep the recommendation core deterministic

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Use deterministic code and a versioned learning policy for candidate filtering and ranking. Do not require an LLM during meal-time recommendation generation.

### Alternatives rejected

- **LLM-generated decisions:** adds latency, cost, nondeterminism, and difficult evaluation to a structured ranking problem.
- **Lowest been-to percentage:** underperforms random selection in the repository's simulator.

### Consequences

Future LLM components are limited to language-shaped tasks and receive their own evaluation suites.

## D007 — Use directions-only handoff in phase one

- **Status:** Superseded by D021 (2026-10-20) — the Maps-only principle stands, but the handoff target is Google Maps
- **Date:** 2026-10-12

### Decision

The Go action opens Apple Maps. Phase one does not place orders, make reservations, or guarantee a delivery destination.

### Alternatives rejected

- **Delivery-app integration:** consumer ordering APIs and reliable cross-provider place matching are not established.
- **Restaurant-site ordering:** inconsistent availability and still requires entity verification.

### Consequences

The product validates restaurant discovery and visit behavior without depending on ordering partnerships.

## D008 — Start with curated place data

- **Status:** Superseded by D021 and D027 (2026-10-20)
- **Date:** 2026-10-12

### Decision

Use a small, reviewed fixture for initial neighborhoods before building a broad ingestion pipeline.

### Alternatives rejected

- **Nationwide ingestion first:** delays the user loop and adds licensing, taxonomy, and entity-resolution work before validation.
- **Live Google Places for all product surfaces:** introduces cost and caching constraints too early.

### Consequences

The first cohort is geographically constrained. The schema still records provider IDs and source timestamps so repeatable ingestion can replace fixtures later.

## D009 — Build for the founder and a private cohort

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Design phase one for the founder plus a few invited testers using private TestFlight distribution.

### Alternatives rejected

- **Single-user-only schema:** creates avoidable migration work and unsafe ownership assumptions.
- **Public launch:** increases support, privacy, data coverage, and App Review scope before retention evidence exists.

### Consequences

Authentication and user isolation are required, while growth, monetization, and public onboarding optimization are deferred.

## D010 — Avoid sensitive ambient permissions in phase one

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Use user-configured dining contexts. Do not request background location or calendar access.

### Alternatives rejected

- **Automatic visit detection:** creates battery, privacy, permission, and App Review costs before the product has earned trust.
- **Calendar-aware timing:** useful later, but not required to test the core loop.

### Consequences

The app may occasionally suggest at a bad moment. Not today is recorded as timing feedback, and timing automation can be reconsidered after real usage.

## D011 — Interpret Another conservatively

- **Status:** Accepted for `policy_v0`
- **Date:** 2026-10-12

### Decision

Treat Another as weak negative evidence for the proposed restaurant, not as a strong cuisine rejection. Treat Not today only as timing feedback.

### Alternatives rejected

- **Full cuisine rejection:** a place-first card does not reveal whether the user rejected the cuisine, restaurant, distance, or mood.
- **No event logging:** loses an important interaction needed for later analysis.

### Consequences

The production policy will initially learn more slowly than the toy simulator. Real response data should determine whether the interface needs separate Another place and Different cuisine actions.

## D012 — Defer the API hosting vendor

- **Status:** Resolved by D030 (2026-10-26)
- **Date:** 2026-10-12

### Decision

Package the FastAPI application as a standard container and select the shared hosting vendor when the first deployable vertical slice exists.

### Alternatives considered

- Render, Fly.io, Railway, and a managed FastAPI offering may all be evaluated.

### Consequences

No vendor-specific runtime service may become a core application dependency during the initial build.

## D013 — Defer pgvector to a future phase

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Remove `CREATE EXTENSION vector` from the phase-one migration and local initialization. The `postgis/postgis` Docker image does not include pgvector, and the feature (embedding-based craving retrieval) has no defined evaluation set in phase one.

### Alternatives rejected

- **Install pgvector in the Docker image now:** requires building a custom image or using a different base image, adding operational complexity for a feature with no current use.
- **Add a combined postgis+pgvector image:** `pgvector/pgvector:pg16` does not include PostGIS; a custom Dockerfile is needed. Defer until an embedding feature has a concrete plan.

### Consequences

The extension can be added in a single migration when the first embedding feature is scoped. The `ARCHITECTURE.md` note "pgvector installed but not used" is revised to "pgvector deferred." The schema is otherwise unchanged.

## D014 — Revoke Supabase Data API access from product tables

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

Keep product tables in the `public` schema but revoke all privileges from the `anon` and `authenticated` Supabase roles.  Set default privileges so future tables are not auto-granted.  FastAPI connects with the postgres superuser or a dedicated service-role credential and retains full access.  PostgREST (the Supabase Data API) is blocked from reading or writing any product table directly.

### Alternatives rejected

- **Private schema:** Requires renaming the schema in all SQLAlchemy models and Alembic migrations.  Effective but significantly more disruptive than a one-migration REVOKE.
- **Row-Level Security only:** RLS adds policy complexity and is described in ARCHITECTURE.md as defense in depth, not the primary access control layer.
- **No action:** Any PostgREST client with the `anon` key could read all product tables without authentication.

### Consequences

Migration 0002 implements the REVOKE.  The DO blocks guard against the Supabase roles not existing in a plain local PostgreSQL instance.  Downgrade restores the default Supabase grants explicitly.

## D015 — Manual visits may omit a proposal

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

The `POST /v1/visits` endpoint accepts `proposal_id=null` for visits the user logs independently of a Nosh suggestion.  When `proposal_id` is provided, the service validates that the proposal exists, belongs to the user, and its session is in state `accepted`.

### Alternatives rejected

- **Require a proposal for every visit:** Prevents the user from logging visits to restaurants they found through other channels.  Reduces utility and creates a false impression that Nosh is the only discovery path.
- **Allow any session state:** Would let users confirm visits that were never accepted via Go, undermining the Go-is-intent principle.

### Consequences

Manual visits count toward visit history and can affect the North Star metric, but they do not influence cuisine preference state (no Beta update) because there is no proposal to link them to a cuisine selection event.  The progress metric already correctly handles this by checking only the confirmed-positive count.

## D016 — Strict dining-context schedules; no overnight windows

- **Status:** Accepted
- **Date:** 2026-10-16

### Decision

Validate every dining-context schedule on create and update: strict 24-hour `HH:MM` bounds, an IANA time zone that loads, a non-empty list of unique active days 0–6 (0 = Monday), and a window whose end is strictly after its start on the same local day. Overnight windows remain unsupported. Suggestion-session keys (`YYYY-MM-DD#meal_type`) must name a real date on an active day with the context's meal type, and the context's stored schedule must itself be valid. Failures return `422 validation_error` with the offending `field`.

### Alternatives rejected

- **Accept overnight windows:** a late-night window spans two local dates, which makes the meal-window key, active-day check, and DST handling ambiguous. No phase-one meal type needs it.
- **Validate only in the mobile client:** other clients, the future scheduler, and pre-validation rows would bypass it.
- **Separate error codes per rule:** one stable `validation_error` code plus `field` and a message is enough for the client; specific rules stay visible in the message and tests.

### Consequences

Late-night dining contexts cannot be configured until a decision defines how an overnight window maps to a meal-window date. Contexts written before this validation existed cannot open sessions until they are corrected. Whether session keys must also fall within a bounded distance of "today" is undecided (see notes.md 2026-10-16).

## D017 — Foreground location at use time, saved anchor as fallback

- **Status:** Accepted; amended by D020 (2026-10-20) — the fallback anchors are optional Home/Work spots, not dining-context points. The API contract (a transient `location` on session creation) is implemented (2026-10-25); the app requests the device location in Milestone 3 step 5
- **Date:** 2026-10-16

### Decision

When the user opens a suggestion, the app should by default use the device's current location, obtained in the foreground with when-in-use permission at that moment. Each dining context keeps a saved anchor point (its map point) that is used whenever permission is denied, location is unavailable or stale, or the user prefers the anchor. Background location, geofencing, and continuous tracking remain prohibited (PRODUCT.md §12, D010).

### Alternatives rejected

- **Saved anchor only:** misses the common case of eating somewhere other than the saved point, but remains the fallback.
- **Background or significant-change location:** violates D010 and the phase-one privacy principle.

### Consequences

The use-time coordinate is transient request input: it must never be logged, must not be stored with more precision or longer than the recommendation record requires, and must not replace the context's anchor without an explicit user action. The API contract for passing a use-time location is not yet designed; until it is, suggestions use the anchor.

## D018 — Onboarding classifications have their own endpoint

- **Status:** Accepted; amended by D025 (2026-10-20) — the provenance rule stands, recorded from the suggestion card. The context-scoped onboarding endpoint below was removed with dining contexts (migration 0005, 2026-10-25); Been here already now records `source = been_here`
- **Date:** 2026-10-16

### Decision

Onboarding classifications use `PUT /v1/contexts/{context_id}/onboarding-places/{place_id}/state`, which records `source = onboarding` and — for Been — sets `user_place_states.was_visited_before_nosh = TRUE` permanently. The place must be an active place within the context's radius (the set onboarding presents), otherwise `422 place_not_in_context`. `PUT /v1/places/{place_id}/state` is the manual settings edit: it records `source = manual` and never sets the flag. Neither a later Nosh confirmation nor a reclassification clears it.

### Alternatives rejected

- **A client-supplied `source` field on the manual endpoint:** any caller could claim onboarding provenance for any place, with no link to the places onboarding showed.
- **Infer provenance from timing (e.g. before the first session):** onboarding can be skipped and resumed, so timing is unreliable.

### Consequences

A restaurant marked Been during onboarding never counts toward the North Star, even when later visited through Nosh. A mistaken Been tap therefore cannot be undone by reclassifying; correcting it would need an audited administrative change. The onboarding history prior is built only from flagged places (RECOMMENDATIONS.md §5.1).

## D019 — Upgrade Expo SDK 53 to the latest SDK (58)

- **Status:** Implemented (2026-10-21)
- **Date:** 2026-10-20; corrected 2026-10-21

### Decision

Upgrade the mobile app from Expo SDK 53 (React Native 0.79, Expo Router 5) to the latest Expo SDK, one SDK at a time, before adding the Supabase, location, and map dependencies Milestone 3 needs. This was first recorded as SDK 57 on the mistaken belief that it was the latest release; SDK 58 shipped on 2026-09-29, so the target is SDK 58 (React Native 0.88, Expo Router 58, React 19.3).

### Alternatives rejected

- **Stay on SDK 53 with an Xcode 26 EAS image:** since 2026-04-28 App Store Connect accepts only builds made with Xcode 26 and the iOS 26 SDK; Expo warns SDK 53 and older may not build with it and recommends SDK 54 or later.
- **Upgrade only to SDK 54:** the minimum compliant version, but already four releases behind and certain to need another upgrade during phase one.
- **Stop at SDK 57:** compliant and still patched, but one release behind with no offsetting benefit once the upgrade was underway.

### Consequences

New dependencies are installed once against the final SDK. Expo Router, React Native, and related packages move to the versions SDK 58 pins; SDK 58 requires Node `^22.13.0` or `^24.3.0`, and CI runs Node 22. `react-dom` is pinned to the React version so npm cannot resolve Expo's optional `react-dom` peer to an incompatible release, and `react-test-renderer` is an explicit, exact dev dependency because `jest-expo` 58 no longer installs it. The npm audit baseline in README was re-measured.

## D020 — Current location first; a meal schedule replaces dining contexts

- **Status:** Implemented (2026-10-25, migration 0005) — server, schedule survey, and Home/Work API; the app requests the device location in Milestone 3 step 5 and anchors at a placeholder point until then
- **Date:** 2026-10-20

### Decision

A suggestion is anchored at the device's foreground location when the user opens the app at meal time, wherever they are. Dining contexts are replaced by one per-user meal schedule set from an onboarding survey: weekday lunch is the default, and dinner is opt-in. Users may save optional Home and Work anchors, used only when location permission is denied or a fix is unavailable. Suggestion sessions are keyed by `(user_id, meal_window_key)`. The D016 schedule rules (strict `HH:MM`, IANA zone, unique days 0–6, no overnight windows) apply to the meal schedule.

### Alternatives rejected

- **Saved dining contexts as the primary unit (original F2):** users are not always at the office or home at lunch; fixed anchors miss the common case.
- **Background or significant-change location:** violates D010.

### Consequences

A pre-curated neighborhood catalog cannot serve "anywhere," so candidates come from a live provider (D021). Overlapping contexts disappear. The `dining_contexts` table, its endpoints, and the context screens are replaced in a migration with a tested downgrade.

## D021 — Google Places end to end for phase one

- **Status:** Accepted (not yet implemented)
- **Date:** 2026-10-20
- **Evidence:** `docs/research/2026-10-20-place-data-and-map-terms.md`

### Decision

Each suggestion session makes one Google Places API (New) Nearby Search request with an explicit Enterprise field mask (rating, review count, opening hours, price level, primary type) around the session's anchor. Those fields drive filtering and ranking. The card shows Google place details on a Google map with Google attribution, and Go opens the place in Google Maps. Apple Maps is not used in the meal-time path.

### Alternatives rejected

- **Rank with Google, display and hand off with Apple:** prohibited — Google Service Specific Terms §14.2 forbids using Places content "in conjunction with a non-Google map"; ToS §3.2.3(e) forbids displaying or using Places content on one.
- **Apple MapKit / Apple Maps Server API only:** free and Apple-native, but no rating, review count, hours, or price, so the quality floor and open-now filter are impossible.
- **Foursquare for ranking, Apple for display:** about $6/month, but Foursquare Master Terms §7.5.7 forbids co-mingling its ranking signals with Nosh's own.
- **Yelp:** $229/month minimum.
- **Overture curated catalog:** no ratings or hours, and cannot cover arbitrary locations.

### Consequences

D007's Apple Maps handoff is superseded; the phase-one rule "Maps-only handoff, no ordering" remains. The mobile app needs a Google Maps SDK key restricted to the bundle ID; the API needs a server key. Whether re-ranking counts as "modifying search results" (ToS §3.2.3(g)) is ambiguous and must be clarified with Google before any public launch. Tests and CI use a fixture provider and need no Google key.

## D022 — Persist only provider IDs and Nosh-owned data

- **Status:** Partially implemented (2026-10-25) — sessions rank candidates once and store the queue; `places` still holds fixture names and addresses until the Google provider lands
- **Date:** 2026-10-20

### Decision

The database stores the Google `place_id` (storable indefinitely) and Nosh-owned data only: user place states, responses, visits, ratings, chain-list matches computed from Nosh's own list, proposal ranks, and score components computed from Nosh-owned inputs. Names, addresses, ratings, review counts, hours, types, and anything derived from them are fetched live and not persisted. A session stores its ranked list of `place_id`s at creation; Another advances through that list without re-querying the provider. On the device, only session and proposal identifiers and queued writes are cached; card content requires the network.

### Alternatives rejected

- **Store a full candidate snapshot (current `candidate_snapshot`):** caches Google content contrary to ToS §3.2.3(a)–(b).
- **Store Google-derived scores or cuisine buckets:** no derived-data exception exists; a stored score approximates the rating.

### Consequences

PRODUCT principle 6 narrows to "reconstructable from stored IDs, ranks, Nosh-owned components, and policy version." Recommendation replay cannot reproduce provider inputs that have since changed. Because a queue of place IDs with distances can reveal where the user was, a session's queue is emptied when it closes and when the user opens a session for a newer meal window. The offline edge case "cache the current card" narrows to IDs and queued writes. History screens resolve names live. Cuisine learning needs a per-visit cuisine label that is Nosh- or user-owned; how it is captured is an open question to settle before `policy_v1` is implemented.

## D023 — Notifications are location-free nudges

- **Status:** Accepted (Milestone 4; not yet implemented)
- **Date:** 2026-10-20

### Decision

A meal-time notification carries no restaurant. Tapping it opens the app, which obtains a foreground location and creates the suggestion session then. In-notification Go / Another / Not today actions are not offered in phase one.

### Alternatives rejected

- **Generate the suggestion before notifying (original F7):** requires knowing where the user is without background location, which D010 forbids.
- **Location-push or Live Activity techniques:** need Always permission or rely on undocumented behavior.

### Consequences

The scheduler only sends deduplicated, schedule-aware reminders and confirmation prompts; it does not pre-generate suggestions. A WidgetKit widget (which may receive location under "While Using the App or Widgets") is a possible later addition, not phase one.

## D024 — `policy_v1` ranking

- **Status:** Accepted (not yet implemented)
- **Date:** 2026-10-20

### Decision

Replace `policy_v0` with `policy_v1`, a pure, versioned policy:

- **Hard filters:** open through the meal window; not visited and not Not interested; not already proposed in the session; within walking range; at or under the user's price ceiling (D026).
- **Quality floor:** a review-count-adjusted (Bayesian) rating; places below the floor are excluded unless nothing clears it.
- **Weighted components:** walking time; quality above the floor; a hidden-gem boost for places above the floor with few reviews; price fit; learned cuisine preference (Thompson sampling, as in `policy_v0`); a national-chain penalty from a Nosh-maintained, versioned list of national chains (local chains are not penalized). The penalty is large enough that a listed chain wins only when no other candidate clears the floor.
- **Determinism:** candidates are sorted by provider ID before sampling and tie-breaking.
- Star rating is never maximized. The `highly_rated` reason code is removed.

### Alternatives rejected

- **Maximize rating:** surfaces famous places and works against discovering lesser-known restaurants.
- **Exclude chains outright:** removes the fallback when nothing else is open nearby.
- **Use the provider's chain field:** Google has none; Foursquare's does not distinguish national from local chains.

### Consequences

Weights and the chain list are versioned with the policy. RECOMMENDATIONS.md documents the components once implemented.

## D025 — "Been here already" on the card replaces bulk onboarding classification

- **Status:** Implemented (2026-10-25) — a `been_here` proposal response
- **Date:** 2026-10-20

### Decision

The suggestion card gets a secondary "Been here already" action alongside the three primary actions. It marks the place visited before Nosh (D018 provenance: never counts toward the North Star), excludes it, and shows the next proposal. It is recorded as its own idempotent event, not as Another.

### Alternatives rejected

- **Bulk onboarding classification of nearby places:** requires a fixed neighborhood, which D020 removes, and is the most tedious onboarding step.

### Consequences

The context-scoped onboarding endpoints are replaced. Another becomes a cleaner signal because "already been" is separated from it.

## D026 — Lunch budget is a per-meal price ceiling

- **Status:** Partially implemented (2026-10-25) — the survey collects a 1–4 ceiling per meal and the API stores it; `policy_v1` enforces it
- **Date:** 2026-10-20

### Decision

The onboarding survey asks for a typical per-meal ceiling. It is a hard filter and a price-fit component in `policy_v1`. Phase one does not track spending.

### Alternatives rejected

- **Monthly spend tracking:** requires entering an amount at every confirmation, adding friction to the step most likely to be skipped, and adds a finance feature to the MVP.

## D027 — Retire the curated-catalog plan

- **Status:** Accepted
- **Date:** 2026-10-20

### Decision

Do not build the Overture-seeded curated catalog proposed in the 2026-10-19 research report. The 20 fictional SF fixtures remain only as data for the test place provider.

### Consequences

`jobs/ingest_places` loses its product role and is kept only to load fixtures until the provider abstraction replaces it.

## D028 — Phase-one operating budget

- **Status:** Accepted
- **Date:** 2026-10-20

### Decision

Target about $50/month: Supabase Pro (~$25; the free tier pauses idle projects), Apple Developer Program (~$8 amortized), a small API host (~$5–7), and Google Maps Platform within its free monthly caps. At about 330 sessions/month, one Nearby Search Enterprise call per session fits inside the 1,000 free calls, and live card and history details fit inside the 5,000 free Place Details Pro calls.

### Consequences

Google Cloud quotas and billing alerts must be set so usage cannot exceed the free caps unnoticed. A larger cohort requires revisiting this decision.

## D029 — Bundle identifier `com.winstontang.nosh`

- **Status:** Accepted (applied to `app.json` in Milestone 3 step 7)
- **Date:** 2026-10-26

### Decision

The iOS bundle identifier is `com.winstontang.nosh`, using the developer's name as the namespace because no domain is owned. It replaces the placeholder `com.nosh.app`.

### Consequences

The identifier is permanent once the App Store Connect app record exists. The Google Maps SDK for iOS key is already restricted to it.

## D030 — Host the API on Fly.io with Supabase Postgres

- **Status:** Accepted (not yet deployed; Milestone 3 step 7)
- **Date:** 2026-10-26

### Decision

Run the FastAPI container on a small Fly.io machine (about $2–5/month). The production database is the Supabase project's Postgres with the PostGIS extension enabled, so there is no second database bill. Connect through Supabase's direct or session connection, not the transaction pooler, which breaks asyncpg prepared statements. Run `alembic upgrade head` as a release step.

### Alternatives rejected

- **Render ($7/month starter):** simpler dashboard, slightly higher cost, no other advantage.
- **Railway with its own Postgres:** a second database bill and extra PostGIS setup.

### Consequences

D012's container-first rule stands: no Fly-specific service becomes a core dependency. The Google server key can be IP-restricted once the Fly machine has a static egress address.
