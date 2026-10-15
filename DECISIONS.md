# Nosh Decision Log

- **Status:** Active
- **Last updated:** 2026-10-12

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

Use Supabase for hosted PostgreSQL and passwordless authentication. Enable PostGIS for radius queries and pgvector for future use, while leaving vector retrieval out of phase one.

### Alternatives rejected

- **SQLite as the shared database:** insufficient for geospatial queries and concurrent hosted use.
- **Separate geospatial and vector databases:** unnecessary complexity.
- **Direct client access for all product writes:** makes recommendation state transitions and authorization harder to centralize.

### Consequences

The mobile app authenticates with Supabase, but the FastAPI service owns product writes and recommendation workflows.

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

- **Status:** Accepted
- **Date:** 2026-10-12

### Decision

The Go action opens Apple Maps. Phase one does not place orders, make reservations, or guarantee a delivery destination.

### Alternatives rejected

- **Delivery-app integration:** consumer ordering APIs and reliable cross-provider place matching are not established.
- **Restaurant-site ordering:** inconsistent availability and still requires entity verification.

### Consequences

The product validates restaurant discovery and visit behavior without depending on ordering partnerships.

## D008 — Start with curated place data

- **Status:** Accepted
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

- **Status:** Deferred
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
