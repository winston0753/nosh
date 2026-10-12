# Nosh Implementation Brief

You are implementing the phase-one Nosh MVP in this repository.

Nosh is an iOS-first restaurant-discovery app that presents one timely, nearby, unvisited restaurant; supports **Go**, **Another**, and **Not today**; opens Apple Maps; and later confirms whether the visit happened and was positive.

## Source of truth

Read these before changing code:

1. `PRODUCT.md` — requirements, MVP scope, edge cases, and non-goals
2. `DECISIONS.md` — accepted product and technical choices
3. `ARCHITECTURE.md` — stack, data model, APIs, and system boundaries
4. `RECOMMENDATIONS.md` — filtering, ranking, feedback, and evaluation
5. `IMPLEMENTATION_HANDOFF.md` — milestone sequence and MVP definition of done

Root documents are canonical. Files under `docs/` are historical research.

## Start here

Implement **Milestone 1 — Repository and backend foundation** from `IMPLEMENTATION_HANDOFF.md` as a focused first pull request:

- create the planned monorepo structure without deleting the existing simulator;
- scaffold the FastAPI modular monolith;
- add Pydantic, SQLAlchemy, Alembic, the async PostgreSQL driver, linting, and typing;
- add local Docker Compose PostgreSQL with PostGIS and pgvector enabled;
- add environment-based configuration and a secret-free `.env.example`;
- implement `/health/live`, `/health/ready`, and OpenAPI generation;
- create the initial database migrations defined in `ARCHITECTURE.md`;
- extend CI to check formatting, linting, typing, migrations, and tests;
- document exact local setup and verification commands in `README.md`.

Do not begin the Expo application or recommendation endpoints until this foundation is reviewable and green.

## Non-negotiable rules

- Expo React Native with strict TypeScript for mobile.
- FastAPI modular monolith for the backend.
- PostgreSQL with PostGIS; pgvector remains unused in phase one.
- Deterministic, versioned recommendation code with no LLM dependency in the meal-time path.
- Go is intent, not a visit.
- Another is ambiguous weak feedback, not a strong cuisine rejection.
- Not today is timing feedback only.
- Only confirmed, positively rated, previously unvisited restaurants count toward the North Star.
- Maps-only handoff in phase one.
- No delivery, ordering, background location, calendar access, social features, RAG, agents, or public-launch work.
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
- If a required choice is unclear, propose an entry in `DECISIONS.md` instead of silently expanding scope.

## First-PR completion check

The first PR is done only when:

- all existing tests still pass;
- the API boots locally;
- liveness succeeds without dependencies;
- readiness verifies the database connection;
- migrations apply to an empty database and have a tested rollback path;
- CI runs without application secrets;
- `git diff --check` passes;
- `README.md` contains reproducible setup commands;
- phase-one non-goals remain absent.

