# Project Notes

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

The original directory was already a Git repository on branch `main`, with one existing commit and no configured remote. Product content and package metadata were renamed from Forage to Nosh. The local folder rename is tracked as the final repository-preparation step. The new root documents make the product and technical baseline explicit and are intended to be committed before connecting the repository to GitHub.

The repository can be linked after an empty GitHub repository is created by adding its URL as `origin` and pushing `main`. No remote URL or GitHub credentials were available during this work, so no external repository was created or linked automatically.

### Claude implementation handoff

Created `IMPLEMENTATION_HANDOFF.md` with a concise implementation brief for Claude. It establishes the canonical document order, non-negotiable constraints, four implementation milestones, first-pull-request scope, engineering expectations, and the MVP definition of done.

The handoff directs Claude to begin with a reviewable backend-foundation pull request, preserve the existing simulator, keep the recommendation path deterministic, and surface product ambiguities through `DECISIONS.md` rather than silently expanding scope.

### GitHub readiness

Added a minimal GitHub Actions workflow that verifies the lockfile, installs the locked development dependencies, and runs the Python test suite on pushes to `main` and pull requests. Added a pull-request template that requires verification, privacy checks, canonical-document consistency, and phase-one scope discipline.
