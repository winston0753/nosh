# Nosh Decision Log

- **Status:** Active
- **Last updated:** 2026-11-10

This file records product and architecture decisions that affect multiple parts of the system. Each entry includes the selected option, rejected alternatives, consequences, and conditions for reconsideration.

**Direction change (2026-11-10): the dish-first pivot.** Nosh now recommends one specific dish at a specific restaurant branch, instead of one nearby unvisited restaurant. Decisions D032–D043 record the pivot. **None of D032–D043 is implemented**: the code on `main` still does what the older entries describe (restaurant suggestions from fixture places, `policy_v0`). Older entries are never deleted; their status lines say what replaced them.

How to read a status line:

- **Implemented** — the code does this today.
- **Accepted (not implemented)** — agreed, but no code exists yet.
- **Proposed, awaiting confirmation** — not yet agreed; do not build on it.
- **Accepted** (with nothing after it) — an older standing choice that still holds; the surrounding text says whether it has been carried out.
- **Partially implemented** — some of it is in the code; the status line says which part.
- **Accepted (not started)** — agreed work that is not code, such as an experiment, and has not begun.
- **Open** — the entry records that a figure or choice is not yet agreed.
- **Resolved** — a deferred choice that a later entry has since made.
- **Superseded** — replaced by a later entry; kept as history.
- **Amended** — still stands, with the change the named entry describes.

In entries dated before 2026-11-10, "the North Star" means the earlier restaurant measure (D002), now superseded by D033.

Questions that are not yet decided are listed under "Open questions" at the end of this file.

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

- **Status:** Superseded by D033 (2026-11-10) — the North Star is now confirmed personally-new dishes. The code's progress screen still computes this restaurant metric
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

- **Status:** Accepted; amended by D041 (2026-11-10) — LLMs are allowed offline (catalog generation, menu mapping); meal-time ranking stays deterministic with no LLM call
- **Date:** 2026-10-12

### Decision

Use deterministic code and a versioned learning policy for candidate filtering and ranking. Do not require an LLM during meal-time recommendation generation.

### Alternatives rejected

- **LLM-generated decisions:** adds latency, cost, nondeterminism, and difficult evaluation to a structured ranking problem.
- **Lowest been-to percentage:** underperforms random selection in the repository's simulator.

### Consequences

Future LLM components are limited to language-shaped tasks and receive their own evaluation suites.

## D007 — Use directions-only handoff in phase one

- **Status:** Superseded by D021 (2026-10-20) — the Maps-only principle stands, but the handoff target is Google Maps. D021 was itself superseded by D034 (2026-11-10) before it was implemented; the code still opens Apple Maps, and which map the dish card uses is an open question
- **Date:** 2026-10-12

### Decision

The Go action opens Apple Maps. Phase one does not place orders, make reservations, or guarantee a delivery destination.

### Alternatives rejected

- **Delivery-app integration:** consumer ordering APIs and reliable cross-provider place matching are not established.
- **Restaurant-site ordering:** inconsistent availability and still requires entity verification.

### Consequences

The product validates restaurant discovery and visit behavior without depending on ordering partnerships.

## D008 — Start with curated place data

- **Status:** Superseded by D021 and D027 (2026-10-20), which were in turn superseded by D034 (2026-11-10). The 20 fixture places are still what the code reads today
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

- **Status:** Accepted — the rules against background location and calendar access stand. The "dining contexts" part was replaced by the meal schedule (D020), and the location basis is amended by D035 (2026-11-10, not implemented)
- **Date:** 2026-10-12

### Decision

Use user-configured dining contexts. Do not request background location or calendar access.

### Alternatives rejected

- **Automatic visit detection:** creates battery, privacy, permission, and App Review costs before the product has earned trust.
- **Calendar-aware timing:** useful later, but not required to test the core loop.

### Consequences

The app may occasionally suggest at a bad moment. Not today is recorded as timing feedback, and timing automation can be reconsidered after real usage.

## D011 — Interpret Another conservatively

- **Status:** Accepted for `policy_v0` (the restaurant policy the code runs today). What Another means for a dish suggestion is an open question
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

- **Status:** Implemented. Restaurant visits become read-only history under D036 (2026-11-10, not implemented); the dish experience (D038) replaces them going forward
- **Date:** 2026-10-12

### Decision

The `POST /v1/visits` endpoint accepts `proposal_id=null` for visits the user logs independently of a Nosh suggestion.  When `proposal_id` is provided, the service validates that the proposal exists, belongs to the user, and its session is in state `accepted`.

### Alternatives rejected

- **Require a proposal for every visit:** Prevents the user from logging visits to restaurants they found through other channels.  Reduces utility and creates a false impression that Nosh is the only discovery path.
- **Allow any session state:** Would let users confirm visits that were never accepted via Go, undermining the Go-is-intent principle.

### Consequences

Manual visits count toward visit history and can affect the North Star metric, but they do not influence cuisine preference state (no Beta update) because there is no proposal to link them to a cuisine selection event.  The progress metric already correctly handles this by checking only the confirmed-positive count.

## D016 — Strict dining-context schedules; no overnight windows

- **Status:** Implemented — since D020 (migration 0005) these rules apply to the meal schedule; dining contexts no longer exist
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

- **Status:** Accepted; amended by D020 (2026-10-20) — the fallback anchors are optional Home/Work spots, not dining-context points. The API contract (a transient `location` on session creation) is implemented (2026-10-25); the app does not yet request the device location. Amended again by D035 (2026-11-10, not implemented): the location basis for a suggestion becomes a user-confirmed coarse meal area, and foreground location is used to revalidate it when the app opens
- **Date:** 2026-10-16

### Decision

When the user opens a suggestion, the app should by default use the device's current location, obtained in the foreground with when-in-use permission at that moment. Each dining context keeps a saved anchor point (its map point) that is used whenever permission is denied, location is unavailable or stale, or the user prefers the anchor. Background location, geofencing, and continuous tracking remain prohibited (PRODUCT.md §12, D010).

### Alternatives rejected

- **Saved anchor only:** misses the common case of eating somewhere other than the saved point, but remains the fallback.
- **Background or significant-change location:** violates D010 and the phase-one privacy principle.

### Consequences

The use-time coordinate is transient request input: it must never be logged, must not be stored with more precision or longer than the recommendation record requires, and must not replace the context's anchor without an explicit user action. The API contract for passing a use-time location is not yet designed; until it is, suggestions use the anchor.

## D018 — Onboarding classifications have their own endpoint

- **Status:** Accepted; amended by D025 (2026-10-20) — the provenance rule stands, recorded from the suggestion card. The context-scoped onboarding endpoint below was removed with dining contexts (migration 0005, 2026-10-25); Been here already now records `source = been_here`. Amended by D036 (2026-11-10, not implemented): place states are frozen history and "Been here" becomes a familiarity signal only
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

- **Status:** Implemented (2026-10-25, migration 0005) — server, schedule survey, and Home/Work API; the app does not request the device location and anchors at a placeholder point. Amended by D035 (2026-11-10, not implemented): the meal schedule and the one-session-per-meal-window key stay; the location basis becomes a user-confirmed coarse meal area per meal
- **Date:** 2026-10-20

### Decision

A suggestion is anchored at the device's foreground location when the user opens the app at meal time, wherever they are. Dining contexts are replaced by one per-user meal schedule set from an onboarding survey: weekday lunch is the default, and dinner is opt-in. Users may save optional Home and Work anchors, used only when location permission is denied or a fix is unavailable. Suggestion sessions are keyed by `(user_id, meal_window_key)`. The D016 schedule rules (strict `HH:MM`, IANA zone, unique days 0–6, no overnight windows) apply to the meal schedule.

### Alternatives rejected

- **Saved dining contexts as the primary unit (original F2):** users are not always at the office or home at lunch; fixed anchors miss the common case.
- **Background or significant-change location:** violates D010.

### Consequences

A pre-curated neighborhood catalog cannot serve "anywhere," so candidates come from a live provider (D021). Overlapping contexts disappear. The `dining_contexts` table, its endpoints, and the context screens are replaced in a migration with a tested downgrade.

## D021 — Google Places end to end for phase one

- **Status:** Superseded before implementation by D034 (2026-11-10). No Google provider was ever built. The terms research it cites remains valid evidence
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

- **Status:** Superseded as the supply model by D034 (2026-11-10). One rule is kept: Google content other than place IDs is not stored. What was implemented (2026-10-25) remains in the code: sessions rank candidates once and store the queue; `places` still holds fixture names and addresses
- **Date:** 2026-10-20

### Decision

The database stores the Google `place_id` (storable indefinitely) and Nosh-owned data only: user place states, responses, visits, ratings, chain-list matches computed from Nosh's own list, proposal ranks, and score components computed from Nosh-owned inputs. Names, addresses, ratings, review counts, hours, types, and anything derived from them are fetched live and not persisted. A session stores its ranked list of `place_id`s at creation; Another advances through that list without re-querying the provider. On the device, only session and proposal identifiers and queued writes are cached; card content requires the network.

### Alternatives rejected

- **Store a full candidate snapshot (current `candidate_snapshot`):** caches Google content contrary to ToS §3.2.3(a)–(b).
- **Store Google-derived scores or cuisine buckets:** no derived-data exception exists; a stored score approximates the rating.

### Consequences

PRODUCT principle 6 narrows to "reconstructable from stored IDs, ranks, Nosh-owned components, and policy version." Recommendation replay cannot reproduce provider inputs that have since changed. Because a queue of place IDs with distances can reveal where the user was, a session's queue is emptied when it closes and when the user opens a session for a newer meal window. The offline edge case "cache the current card" narrows to IDs and queued writes. History screens resolve names live. Cuisine learning needs a per-visit cuisine label that is Nosh- or user-owned; how it is captured is an open question to settle before `policy_v1` is implemented.

## D023 — Notifications are location-free nudges

- **Status:** Superseded before implementation by D035 (2026-11-10) — a notification may name a dish when a meal area exists; the location-free nudge remains only as the fallback when none exists
- **Date:** 2026-10-20

### Decision

A meal-time notification carries no restaurant. Tapping it opens the app, which obtains a foreground location and creates the suggestion session then. In-notification Go / Another / Not today actions are not offered in phase one.

### Alternatives rejected

- **Generate the suggestion before notifying (original F7):** requires knowing where the user is without background location, which D010 forbids.
- **Location-push or Live Activity techniques:** need Always permission or rely on undocumented behavior.

### Consequences

The scheduler only sends deduplicated, schedule-aware reminders and confirmation prompts; it does not pre-generate suggestions. A WidgetKit widget (which may receive location under "While Using the App or Widgets") is a possible later addition, not phase one.

## D024 — `policy_v1` ranking

- **Status:** Superseded before implementation by D032 (2026-11-10). `policy_v1` was never built; the dish policy is described in RECOMMENDATIONS.md
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

- **Status:** Implemented (2026-10-25) — a `been_here` proposal response. Amended by D036 (2026-11-10, not implemented): "Been here" keeps its meaning but becomes a familiarity signal only; a visited restaurant no longer excludes its dishes
- **Date:** 2026-10-20

### Decision

The suggestion card gets a secondary "Been here already" action alongside the three primary actions. It marks the place visited before Nosh (D018 provenance: never counts toward the North Star), excludes it, and shows the next proposal. It is recorded as its own idempotent event, not as Another.

### Alternatives rejected

- **Bulk onboarding classification of nearby places:** requires a fixed neighborhood, which D020 removes, and is the most tedious onboarding step.

### Consequences

The context-scoped onboarding endpoints are replaced. Another becomes a cleaner signal because "already been" is separated from it.

## D026 — Lunch budget is a per-meal price ceiling

- **Status:** Partially implemented (2026-10-25) — the survey collects a 1–4 ceiling per meal and the API stores it; nothing enforces it. `policy_v1` (D024), which was to enforce it, is superseded. The ceiling remains an explicit user constraint; how it is applied to dish offerings is an open question
- **Date:** 2026-10-20

### Decision

The onboarding survey asks for a typical per-meal ceiling. It is a hard filter and a price-fit component in `policy_v1`. Phase one does not track spending.

### Alternatives rejected

- **Monthly spend tracking:** requires entering an amount at every confirmation, adding friction to the step most likely to be skipped, and adds a finance feature to the MVP.

## D027 — Retire the curated-catalog plan

- **Status:** Superseded as the supply model by D034 (2026-11-10) — Nosh again stores its own index, now of dish offerings rather than restaurants. The Overture-seeded restaurant catalog this entry retired is still not being built
- **Date:** 2026-10-20

### Decision

Do not build the Overture-seeded curated catalog proposed in the 2026-10-19 research report. The 20 fictional SF fixtures remain only as data for the test place provider.

### Consequences

`jobs/ingest_places` loses its product role and is kept only to load fixtures until the provider abstraction replaces it.

## D028 — Phase-one operating budget

- **Status:** Superseded by D043 (2026-11-10) — the new figure is open
- **Date:** 2026-10-20

### Decision

Target about $50/month: Supabase Pro (~$25; the free tier pauses idle projects), Apple Developer Program (~$8 amortized), a small API host (~$5–7), and Google Maps Platform within its free monthly caps. At about 330 sessions/month, one Nearby Search Enterprise call per session fits inside the 1,000 free calls, and live card and history details fit inside the 5,000 free Place Details Pro calls.

### Consequences

Google Cloud quotas and billing alerts must be set so usage cannot exceed the free caps unnoticed. A larger cohort requires revisiting this decision.

## D029 — Bundle identifier `com.winstontang.nosh`

- **Status:** Accepted (not yet applied to `app.json`; that was step 7 of the old Milestone 3, and where it falls in the new milestone order is open question 19)
- **Date:** 2026-10-26

### Decision

The iOS bundle identifier is `com.winstontang.nosh`, using the developer's name as the namespace because no domain is owned. It replaces the placeholder `com.nosh.app`.

### Consequences

The identifier is permanent once the App Store Connect app record exists. The Google Maps SDK for iOS key is already restricted to it.

## D030 — Host the API on Fly.io with Supabase Postgres

- **Status:** Accepted (not yet deployed; that was step 7 of the old Milestone 3, and where it falls in the new milestone order is open question 19)
- **Date:** 2026-10-26

### Decision

Run the FastAPI container on a small Fly.io machine (about $2–5/month). The production database is the Supabase project's Postgres with the PostGIS extension enabled, so there is no second database bill. Connect through Supabase's direct or session connection, not the transaction pooler, which breaks asyncpg prepared statements. Run `alembic upgrade head` as a release step.

### Alternatives rejected

- **Render ($7/month starter):** simpler dashboard, slightly higher cost, no other advantage.
- **Railway with its own Postgres:** a second database bill and extra PostGIS setup.

### Consequences

D012's container-first rule stands: no Fly-specific service becomes a core dependency. The Google server key can be IP-restricted once the Fly machine has a static egress address.

## D031 — Cuisine labels from place types, confirmed by the user

- **Status:** Superseded before implementation by D032/D034 (2026-11-10). Accepted on 2026-10-26 but never recorded in this file at the time and never implemented; recorded here on 2026-11-10 so the history is complete
- **Date:** 2026-10-26

### Decision

Settle the open question D022 left (how a visit gets a cuisine label without storing Google-derived data) in three parts: at meal time, look the cuisine up from Google place types using a fixed table; at visit confirmation, show an LLM's guess for the user to confirm or change; store only the label the user confirmed.

### Alternatives rejected

- **Store a cuisine derived from Google place types:** D022 forbids storing values derived from provider content.

### Consequences

None in the code: nothing was built. Under the dish-first pivot the cuisine comes from the dish catalog (D034, D040), so no per-visit cuisine guess is needed.

## D032 — The recommendation unit is a dish at a specific restaurant branch

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Supersedes:** the restaurant as the recommendation unit throughout; D024

### Decision

Nosh recommends one specific dish offered at one specific restaurant branch, proactively, on the user's meal schedule. Every part of the product that was built around "a restaurant" (suggestions, ranking, confirmation, the success metric, history) is redefined around "a dish at a branch".

The dish policy offers three kinds of suggestion: familiar, adjacent, and broader exploration. It widens toward other culinary regions when the user's recent experience is concentrated. It never overrides a constraint the user has stated explicitly. The balance between the three kinds, and every weight, is undecided (open question 6).

The pivot's scope is: onboarding and preferences; the dish catalog and its semantic layer; restaurant and menu acquisition; dish-to-restaurant matching; the recommendation policy; scheduled delivery; suggestion sessions and actions; actual-meal confirmation and corrections; exploration rewards, the avatar, and the journal; evaluation and operations.

### Alternatives rejected

- **One nearby unvisited restaurant (the original unit, PRODUCT.md 0.1):** superseded by this decision.
- **`policy_v1` restaurant ranking (D024):** it ranks restaurants; it was never implemented and is superseded.

### Consequences

Today's code is restaurant-shaped: proposals, the candidate queue, the API responses, the card, and visits all refer to a place. Moving to dishes is new work, done additively so existing data stays readable (D036): proposals gain a nullable reference to an offering, and the existing `places` and `place_sources` tables are reused as the registry of restaurant branches. The planned minimum set of new tables is `dish`, `dish_alias`, `dish_trait`, `menu_item`, `dish_offering`, `user_dish_preference`, `dish_experience`, and `reward` (ARCHITECTURE.md; column design is not done).

The agreed order of work is seven milestones, none started: (1) catalog schema, identity rules, seed, and evaluation set; (2) branch and offering tables with the San Mateo hand-verified index, with the source experiment in parallel; (3) dish onboarding and profile; (4) dish ranking with an additive proposals migration; (5) single-commit refactor, dish experience, and rewards; (6) notification worker and meal area; (7) minimal journal and avatar. The first target is one complete loop: dish onboarding → dish-and-restaurant recommendation → scheduled delivery → actual-dish confirmation → immediate discovery reward → updated profile and minimal avatar and journal. Details are in IMPLEMENTATION_HANDOFF.md. Nosh Meals and social features are possible later extensions only; no tables, services, or infrastructure are created for them now.

## D033 — North Star: confirmed personally-new dishes tried

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Supersedes:** D002

### Decision

The North Star is confirmed personally-new dishes tried per active user. Enjoyment rate is a guardrail, not part of the count. "Tried" and "enjoyed" are two separate signals and are recorded separately.

### Alternatives rejected

- **Confirmed positively rated new restaurants per monthly active user (D002):** measures restaurants, not dishes, and folds enjoyment into the count.

### Consequences

A dish the user tried and did not enjoy still counts as tried; a falling enjoyment rate is the warning that exploration is producing poor meals. Changing whether a dish was enjoyed never changes whether it was new (D038). The existing progress endpoint still reports the D002 restaurant metric until the dish experience exists.

## D034 — Supply model: a published dish-offering index built offline

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Supersedes:** D021, D022, and D027 as the supply model

### Decision

Nosh stores its own published index of dish offerings, built offline in this order: sources → adapters → branch match → source-backed menu items → mapping to the dish catalog → review → published offering. Meal-time ranking reads only published offerings.

Live place status and opening hours are a separate eligibility input. They can make an offering ineligible right now; they never establish that a restaurant serves a dish.

Data falls into three classes, kept apart:

1. **Shared catalog** — owned by Nosh (dishes, variants, aliases, and their facts; D040).
2. **Provider content** — anything obtained from an outside source. Every item is tagged with its source, retrieval date, and expiry, and all content from one source can be purged on its own.
3. **Personal data** — what a user tells Nosh or does in it.

One rule from D022 is kept: Google content other than place IDs is not stored.

### Alternatives rejected

- **Live Google Places candidates at meal time (D021):** place data does not say which dishes a restaurant serves.
- **Store only provider IDs (D022) as the whole supply model:** a dish recommendation needs stored menu evidence.
- **No Nosh-held catalog (D027):** the dish unit requires one.

### Consequences

Menu acquisition and offline processing move into scope (they were non-goals). Which sources are used is not decided (D042). Whether a given source's content may be stored, processed, and displayed is a license question measured by the D042 experiment, not assumed. Menu evidence shows that a dish is offered; it does not show the dish is good.

## D035 — Location basis: a user-confirmed coarse meal area

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Supersedes:** D023. **Amends:** D017 and D020

### Decision

For each meal, the user confirms a coarse meal area: roughly where they will be for that meal. It is stored as a coarse cell, never as a point. When the app opens, it revalidates the area using foreground location. When no meal area exists, the notification is a generic nudge. A notification may name a dish only when a meal area exists.

### Alternatives rejected

- **Location-free nudges only (D023):** a named dish in the notification is the proactive suggestion the product is built around, and it needs a location basis before the app is opened.
- **Background location:** still prohibited (D010).

### Consequences

Suggestions can be prepared before the user opens the app without tracking them. The meal area is personal data and is covered by deletion. Background location, geofencing, and continuous tracking remain prohibited. The cell size, how the user confirms the area, and what happens to the saved Home/Work spots are open questions.

## D036 — Legacy restaurant data is frozen, read-only history

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Amends:** D018 and D025

### Decision

Restaurant visits and place states recorded before the pivot are frozen as read-only history. They are not converted into dish experiences (no dish backfill) and earn no rewards after the fact (no retrospective rewards). "Been here" keeps its original meaning (the user had been to that restaurant before Nosh) and becomes a familiarity signal only. A visited restaurant no longer excludes its dishes from being suggested.

### Alternatives rejected

- **Backfill dish experiences from restaurant visits:** a restaurant visit does not record which dish was eaten.
- **Keep excluding visited restaurants:** under the dish unit, a familiar restaurant can serve a dish that is new to the user.

### Consequences

The code today does the opposite: candidate building excludes every place marked visited. That changes when dish ranking is built. Existing rows and their provenance flag (D018) are kept unchanged.

## D037 — Sessions: Go is final; the system may replace only unanswered proposals

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10

### Decision

- One suggestion session per user and meal window stays.
- Go is final for that window. There is no "change my pick".
- The system may supersede an unanswered proposal (for example, the location changed or the offering went stale). This is recorded separately from a user response.
- An accepted proposal is never replaced silently. If an accepted offering goes stale, the user sees a notice.
- If the user ate something else, they say so at confirmation.

### Alternatives rejected

- **A "change my pick" action after Go:** rejected; the correction happens at confirmation.
- **Recording a system replacement as a user response (such as Another):** it would be read as the user's feedback when the user did nothing.

### Consequences

Proposals need a way to be marked superseded by the system, with a reason, distinct from the user's responses. Today, Go closes the session and a repeat request returns the existing session; no system supersession exists.

## D038 — Confirmation is one transaction; rewards follow the facts

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10

### Decision

- Application services stop committing on their own. Each request commits once.
- Confirming a meal is one operation that writes the dish experience, checks whether the dish is new to the user while holding a per-user lock, and inserts any rewards idempotently (a retry cannot create a second reward).
- Taste evidence is derived from dish experiences, not stored separately as the source of truth.
- Corrections are appended as new events; earlier records are not overwritten.
- Changing whether the dish was enjoyed never changes a reward.
- Changing which dish was eaten re-evaluates both the old and the new dish.
- Retracting an experience invalidates its reward.

### Alternatives rejected

- **Services that commit internally (today's code):** a confirmation and its reward could be saved separately, so one could exist without the other.
- **Overwriting a rating in place (today's code):** loses the history of what changed.

### Consequences

A refactor of the existing services is required before the dish experience is built. Novelty and rewards can always be recomputed from the experience history.

## D039 — Rewards and avatar: a cosmetic only for a new country

- **Status:** Accepted (not implemented), except the one-home-country rule, which is **Proposed, awaiting confirmation**
- **Date:** 2026-11-10

### Decision

- A cosmetic for the avatar unlocks only when the user tries a dish from a country that is new to them.
- A new dish, or a new variant of a dish, gets a journal entry and a discovery moment, but no cosmetic.
- The avatar is always computed from the rewards that are currently valid, so a retraction removes the cosmetic.
- **Proposed, awaiting confirmation:** each dish has exactly one home country for unlock purposes, plus optional secondary associations that never unlock anything.

### Alternatives rejected

- **A cosmetic for every new dish or variant:** rejected; those get a journal entry and a discovery moment instead.
- **Storing the avatar's state directly:** it could drift from the rewards after a correction.

### Consequences

Rewards must be individually valid or invalid (D038). Until the one-home-country rule is confirmed, the catalog work must not depend on it.

## D040 — Catalog identity: dish, variant, alias

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10

### Decision

- The catalog has three levels: dish, variant, and alias. Only dishes and variants have IDs. Variants are one level deep (no variants of variants).
- A variant is something that eats differently: a regional style, a different main protein, or a different preparation. A difference in name only is an alias.
- IDs are permanent. Merging two entries leaves a redirect from the old ID. Splitting an entry never moves a user's past experiences.
- Every fact in the catalog is marked as generated, reviewed, or source-backed. The catalog is versioned.
- Anything specific to how one restaurant prepares a dish lives on the offering, not in the catalog.
- A menu item that names only the dish is recorded at dish level, not guessed into a variant.
- The target size is about 10,000 dishes, built as an intentional workstream with the founder hands-on.

### Alternatives rejected

- **Deeper variant trees:** rejected; one level keeps identity and novelty checks simple.
- **IDs for aliases:** rejected; a name is not a different thing to eat.

### Consequences

Novelty ("is this new to me?") and rewards rely on stable IDs, so the identity rules must be settled before experiences are recorded against them. Cuisine comes from the catalog (this is what makes D031 unnecessary).

## D041 — LLM boundary: offline only

- **Status:** Accepted (not implemented)
- **Date:** 2026-11-10
- **Amends:** D006

### Decision

LLMs may be used offline, for catalog generation and menu mapping, each with its own evaluation set. Meal-time ranking stays deterministic and makes no LLM call. D013 (no pgvector) stands. No microservices, graph database, vector service, or event platform.

### Alternatives rejected

- **No LLM use anywhere (the earlier reading of D006 and the PRODUCT.md 0.1 non-goals):** a catalog of about 10,000 dishes and menu mapping are language-shaped tasks.
- **An LLM call in the meal-time path:** still rejected, for D006's reasons.

### Consequences

LLM output enters the product only through stored, marked facts (generated, reviewed, or source-backed; D040) and reviewed offerings (D034).

## D042 — Pilot area and source-comparison experiment

- **Status:** Accepted (not started). No source is selected
- **Date:** 2026-11-10

### Decision

Downtown San Mateo is the first hand-verified offering index. Neighborhoods in San Francisco, San Jose, and New York City are comparison samples only.

A source-comparison experiment runs about 40 restaurants (10 per area) through each vendor trial and through crawling the restaurants' own sites. It measures: correct branch, menu presence, item detail, freshness, mapping accuracy, review minutes, cost per usable offering, and license rights for storage, processing, and display. Pass/fail thresholds are set before any results are looked at.

Datafiniti, MealMe, and RelevantData are candidates, not selected.

### Alternatives rejected

- **Choosing a vendor before measuring:** nothing about any vendor's coverage, price, or license has been confirmed.

### Consequences

Until the experiment reports, the only supply is the hand-verified San Mateo index. No vendor's licensing rights, prices, or coverage are assumed anywhere in these documents.

## D043 — Operating budget is open

- **Status:** Open — D028's figure is superseded and no new figure is agreed
- **Date:** 2026-11-10
- **Supersedes:** D028

### Decision

D028's target of about $50/month no longer holds. The new figure is open until the D042 experiment reports. For planning only: about $50–75/month while running on hand-verified data, and more if a paid feed is used.

Vendor pricing and menu coverage were **not** confirmed from vendor documentation. The planning range is not a quote.

### Consequences

No paid feed is committed to. The budget is decided after the experiment, as a new entry or an update to this one.

## Open questions

These are not decided. Do not build on an assumed answer; raise the question and record the answer as a decision.

1. **One home country per dish (D039).** Proposed, awaiting confirmation. Also open: how the home country is chosen for dishes with a contested or shared origin.
2. **Budget (D043).** The monthly figure, pending the source experiment.
3. **Sources (D042).** Which source or sources are used; the experiment's pass/fail thresholds (to be set before results); each source's rights to store, process, and display its content.
4. **Live place status and opening hours (D034).** Which provider supplies them, and what its terms require of the card.
5. **Map and handoff.** Which map the dish card shows and which maps app Go opens, now that D021 is superseded. The code opens Apple Maps.
6. **Policy weights (D032).** The balance between familiar, adjacent, and broader-exploration suggestions; how "recent experience is concentrated" is measured; how fast suggestions widen toward other culinary regions.
7. **Restaurant quality.** Menu evidence does not establish quality, and Google ratings are not stored. What quality signal, if any, the dish policy uses is undecided.
8. **Price ceiling (D026).** How the per-meal ceiling applies to dish offerings.
9. **Response meanings for dishes.** What Another, Not today, and "Been here" teach the dish policy. D011 was written for restaurants.
10. **Explicit constraints.** Which constraints onboarding collects (for example dietary ones) and how they are worded. The policy never overrides them, whatever they are.
11. **Meal area (D035).** The size of the coarse cell, how the user confirms or changes the area, how long it is kept, and whether the saved Home/Work spots remain.
12. **Notifications (D035).** Send time relative to the meal window, what a dish-naming notification may show, and whether it offers actions.
13. **"I ate something else" (D037).** How the user picks the actual dish at confirmation, and what happens when it is not in the catalog.
14. **Active user (D033).** The period that defines "active" for the North Star, and any target values.
15. **Legacy screens (D036).** What the app shows for frozen restaurant history, and when the visit and place-state write endpoints are retired.
16. **Avatar and journal (D039).** What the avatar and its cosmetics are, and what a journal entry contains.
17. **Catalog process (D040, D041).** Who reviews generated facts, the evaluation sets and their pass marks for catalog generation and menu mapping, and how catalog versions are numbered.
18. **Sign-in identity deletion.** Deleting an account should also delete the sign-in identity; the mechanism is not designed (today only product data is deleted).
19. **Earlier tester-readiness work.** Where the unfinished items from the old Milestone 3 (offline write queue, EAS/TestFlight build, real icons) and the Fly.io deployment (D030) fall in the new milestone order.
20. **Initial dish preferences (cold start).** What onboarding asks about dishes, and how those answers shape suggestions for a new user who has no dish experiences yet.
21. **Repetition.** Whether the same dish, or the same branch, may be proposed again within a session or in back-to-back meal windows.
22. **Variants and the North Star (D033, D039).** Whether trying a new variant of a dish the user has already had counts as a personally-new dish. D039 gives it a journal entry and a discovery moment but does not say.
23. **Nothing eligible.** What the user sees when no published offering is eligible, and whether any rule may be relaxed. Explicit constraints may not.
24. **Planned schema details.** How variants are represented relative to dishes (D040); how a system-superseded proposal and its reason are recorded, separate from user responses (D037); whether appended corrections live on the dish experience or in a separate event structure (D038); and whether dish proposals keep filling the existing `proposals.place_id` and `cuisine_id` columns or those columns become nullable (the new offering reference itself is decided, D032).
25. **Offerings and purged content (D034).** What happens to a published offering when the provider content behind it expires or is purged, and which data class an offering belongs to.
