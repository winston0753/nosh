# Nosh Implementation Handoff

- **Last updated:** 2026-11-10
- **Direction:** dish-first pivot (D032–D043). **None of it is implemented yet.**

This file tells the next person (or Claude session) what exists, what has been agreed but not built, and what is only history. It keeps those three apart on purpose:

- **Part A — What is implemented today:** the code on `main`. It is restaurant-shaped.
- **Part B — Accepted but not implemented:** the new milestone plan for the dish-first product.
- **Part C — Historical:** the old milestone plan. Kept for reference; superseded.

## Mission

Build the phase-one Nosh MVP around one idea (D032): **Nosh recommends one specific dish at one specific restaurant branch, proactively, on the user's meal schedule.** A "branch" is one physical location of a restaurant. "Proactively" means Nosh sends the suggestion at meal time; the user does not have to ask.

The first target is **one complete loop**, end to end, for a private tester (D009):

> dish onboarding → dish-and-restaurant recommendation → scheduled delivery → actual-dish confirmation → immediate discovery reward → updated profile and minimal avatar/journal

The North Star (the one number that says whether Nosh is working) is **confirmed personally-new dishes tried per active user** (D033). "Tried" and "enjoyed" are recorded separately; enjoyment rate is a guardrail, not part of the count.

## Read these first

Treat these root documents as authoritative:

1. `PRODUCT.md` — requirements, edge cases, and non-goals
2. `DECISIONS.md` — accepted choices, rejected alternatives, and the **Open questions** list at the end
3. `ARCHITECTURE.md` — stack, data model, APIs, and system boundaries
4. `RECOMMENDATIONS.md` — filtering, ranking, feedback, and evaluation
5. `notes.md` — dated implementation log, newest first

If anything here disagrees with `DECISIONS.md`, `DECISIONS.md` wins. Material under `docs/` is historical research and never overrides the root documents.

## Where things stand (2026-11-10)

**Confirm this against Git before acting on it.** Run `git status`, `git log --oneline -5`, and `gh pr list`. This text is a snapshot and goes stale.

- `main` is at `8422298`. PRs #1–#6 are merged; PR #6 was the meal schedule. No open PRs are known.
- The pivot documents (this file, `DECISIONS.md`, and the other root documents) are on branch `docs/dish-first-pivot`, **uncommitted**, awaiting the owner's review. This is a docs-only change: no code, migrations, tests, or mobile files were changed.
- The repository has no branch protection. The owner reviews and merges PRs on GitHub. `gh` is installed and logged in.
- Test counts are not written here. Run the checks in `README.md` to see the current state.

---

## Part A — What is implemented today

The code on `main` is a working **local** prototype of the **old, restaurant-shaped** product. It was checkpointed as "Milestone 0.1 — Working Local Foundation". It runs on a developer's machine. It is **not** ready for TestFlight or outside testers, and it does not model dishes at all.

### Old milestones, as they stand

| Old milestone | Status |
|---|---|
| 1 — Repository and backend foundation | Complete |
| 2 — Deterministic suggestion API | Complete |
| 3 — Expo vertical slice | Partially complete: the local slice works; tester-readiness work was never done |
| 4 — Notifications and private-cohort readiness | Not started, beyond two tables (`device_tokens`, `notification_deliveries`) |

### What the code does (verified against source on 2026-11-10)

**Stack.** FastAPI modular monolith in `services/api/` (D004); PostgreSQL with PostGIS, no pgvector (D013); Expo SDK 58 app in `apps/mobile/` (D019); Supabase email one-time-code sign-in, with a local-development mode when Supabase is not configured.

**Everything is about places, not dishes.** Proposals, the candidate queue, the API responses (`place_id`, `place_name`, `cuisine_name`, `distance_meters`, `address`), the mobile card, and visits all refer to a restaurant. `proposals.place_id` and `proposals.cuisine_id` are required columns.

**Data.** 14 tables: `profiles`, `places`, `place_sources`, `cuisines`, `place_cuisines`, `user_place_states`, `suggestion_sessions`, `proposals`, `proposal_responses`, `visits`, `device_tokens`, `notification_deliveries`, `meal_schedules`, `saved_anchors`. Migrations `0001`–`0005`.

**Supply.** Only a `fixture` place source: 20 fictional San Francisco places, whose names and addresses are stored and returned. No Google provider exists.

**Ranking.** Only `policy_v0` exists. It hard-excludes any place marked `visited` or `not_interested`, inactive places, places already proposed in the session, and places with no cuisine. The search radius is fixed at 1,600 m. The per-meal price ceiling is stored but not used anywhere.

**Sessions.** One session per user and meal window. Go (and Not today) closes the session and empties its candidate queue. Asking again for the same meal window returns the existing session, whatever location it carries. Opening a session empties the queues of the user's other sessions.

**Visits.** A visit linked to a proposal needs a prior Go on that exact proposal. A manual visit with no proposal is accepted. A rating is required. Editing a visit overwrites the rating or date and keeps no history.

**How saving works.** Every service function that writes saves (commits) inside the service, not once at the end of the request. D038 moves the save to the end of the request, so a confirmation and its rewards are always saved together.

**Mobile app.** It anchors every session at a hard-coded San Francisco Mission point, never uses the saved Home/Work spots, and on Go opens Apple Maps with a name-and-address search. In the confirmation screen, "No, I didn't go" and "Remind me later" send nothing to the server.

**Notifications.** Two tables only. No worker, no device routes. `expo-notifications` is installed but unused.

**Deletion.** `DELETE /v1/me/product-data` removes the user's product data but not their Supabase sign-in identity.

**Progress.** The progress screen still computes the old restaurant metric (D002), not the dish North Star (D033).

The full route and table detail lives in `ARCHITECTURE.md`. Do not recreate any of this; extend it.

---

## Part B — Accepted but not implemented

The milestone order and the first target are recorded in D032; the decisions each milestone implements are D032–D043. Two parts are not yet agreed: the budget (D043 is open) and the one-home-country rule (part of D039, proposed). **None of it exists in code.** Each milestone is a reviewable change or small series of changes. No implementation starts until the owner asks.

Where a milestone touches something still undecided, it names the open question by its number in the `DECISIONS.md` Open questions list. Do not build on an assumed answer.

### New milestones

| # | Milestone | Status |
|---|---|---|
| 1 | Catalog schema, identity rules, seed, evaluation set | Not started |
| 2 | Branch and offering tables with the San Mateo hand-verified index; source experiment in parallel | Not started |
| 3 | Dish onboarding and profile | Not started |
| 4 | Dish ranking with an additive proposals migration | Not started |
| 5 | Single-commit refactor, dish experience, rewards | Not started |
| 6 | Notification worker and meal area | Not started |
| 7 | Minimal journal and avatar | Not started |

#### 1 — Catalog schema, identity rules, seed, evaluation set

**What it is.** The shared dish catalog: Nosh's own list of dishes. It has three levels. A **dish** (for example, ramen). A **variant**, which eats differently (a regional style, a different main protein, or a different preparation). An **alias**, which is just another name.

**Implements:** D040, D041, and the "shared catalog" data class in D034.

**Done looks like:**

- Catalog tables covering dishes, variants (one level deep), and aliases; only dishes and variants have IDs. How a variant is stored relative to its dish is open (question 24).
- IDs are permanent. A merge leaves a redirect from the old ID. A split never moves a user's past experiences.
- Every catalog fact is marked generated, reviewed, or source-backed, and the catalog is versioned.
- A first seed of the catalog is loaded. (The long-term target is about 10,000 dishes, built as an intentional workstream with the founder hands-on.)
- An evaluation set exists for offline LLM catalog generation. Who reviews, the pass marks, and version numbering are open (question 17).
- Nothing depends on the one-home-country rule until it is confirmed (D039, question 1).

#### 2 — Branch and offering tables with the San Mateo hand-verified index; source experiment in parallel

**What it is.** Where dishes meet restaurants. An **offering** is "this dish is on the menu at this branch". Nosh publishes offerings only after an offline process: sources → adapters → branch match → source-backed menu items → mapping to the catalog → review → published offering. In plain terms: an *adapter* is a small piece of code that reads one source's format; *branch match* means working out which physical restaurant a menu belongs to; *source-backed* means the item can be traced to the source it came from.

**Implements:** D034, D042, and the kept D022 rule (Google content other than place IDs is not stored).

**Done looks like:**

- A branch registry (the existing `places` and `place_sources` tables, reused) plus new menu-item and offering tables, keeping the three data classes apart: shared catalog, provider content, personal data. Which class an offering belongs to, and what happens to it when its source is purged, is open (question 25).
- Every piece of provider content carries its source, retrieval date, and expiry, and all content from one source can be purged on its own.
- A hand-verified index of published offerings for downtown San Mateo.
- In parallel, the source-comparison experiment: about 40 restaurants (10 each in San Mateo, San Francisco, San Jose, and New York City) run through each vendor trial and through crawling restaurants' own sites. Pass/fail thresholds are written down **before** any results are looked at (question 3).
- Datafiniti, MealMe, and RelevantData are candidates only. No source is selected, and no vendor's rights, prices, or coverage are assumed.

#### 3 — Dish onboarding and profile

**What it is.** How a new user tells Nosh about their eating, so the first suggestion is sensible, and the personal profile that results.

**Implements:** D032 and D033; the profile follows D038 (taste evidence comes from dish experiences).

**Done looks like:**

- A dish-based onboarding flow in the app, saved as personal data and covered by deletion.
- A profile the ranking can read, with "tried" and "enjoyed" kept separate.
- Explicit constraints the user states are stored and never overridden by the policy. Which constraints are collected, and their wording, is open (question 10).
- What onboarding asks about dishes, and how the answers shape a new user's first suggestions, is open (question 20).

#### 4 — Dish ranking with an additive proposals migration

**What it is.** The recommendation policy picks one offering (a dish at a branch) for the meal window. "Additive" means the change adds new columns or tables to proposals; existing restaurant proposals stay readable.

**Implements:** D032, D034, D036, D037, D041 (and D006 as amended).

**Done looks like:**

- A deterministic, versioned dish policy that reads only published offerings and makes no LLM call.
- Live place status and opening hours can make an offering ineligible right now; they never establish that a dish is served. The provider for live status is open (question 4).
- A visited restaurant no longer excludes its dishes; "Been here" becomes a familiarity signal only (D036).
- Proposals can reference an offering, added without changing or backfilling existing rows.
- The system can mark an unanswered proposal as superseded, with a reason, recorded separately from user responses (D037).
- Open, to settle before or during this milestone: policy weights (question 6), a quality signal (question 7), how the price ceiling applies (question 8), what Another, Not today, and "Been here" teach the dish policy (question 9), whether a dish or branch may repeat (question 21), what the user sees when nothing is eligible (question 23), and how supersession and the existing proposal columns are handled in the schema (question 24).

#### 5 — Single-commit refactor, dish experience, rewards

**What it is.** First, change the backend so each request saves exactly once. Then build the **dish experience**: the record that a user actually ate a dish. Then the discovery reward the user sees straight away.

**Implements:** D038, D033, D036, D037, D039.

**Done looks like:**

- Application services no longer commit on their own; each request commits once.
- Confirming a meal is one operation: it writes the dish experience, checks whether the dish is new to the user while holding a per-user lock, and inserts any rewards so that a retry cannot create a second one.
- The user can say they ate something else. How they pick the actual dish, and what happens if it is not in the catalog, is open (question 13).
- Tried and enjoyed are recorded separately. Changing "enjoyed" never changes a reward. Changing which dish was eaten re-evaluates both dishes. Retracting an experience invalidates its reward. Corrections are appended, not overwritten.
- Go is final for the window; if an accepted offering goes stale, the user sees a notice (D037).
- An immediate discovery moment after confirmation. Whether a new variant counts as a personally-new dish is open (question 22), as is where appended corrections are stored (question 24).
- Legacy restaurant visits and place states stay as frozen, read-only history: no dish backfill, no retrospective rewards (D036). What the app shows for them is open (question 15).
- The map and handoff for Go are open (question 5); the code currently opens Apple Maps.

#### 6 — Notification worker and meal area

**What it is.** Scheduled delivery. A **meal area** is roughly where the user will be for a meal, confirmed by the user and stored as a coarse cell (an area), never as a point.

**Implements:** D035 (superseding D023, amending D017 and D020), with D010 unchanged.

**Done looks like:**

- The user confirms a meal area per meal; it is stored as a coarse cell and covered by deletion.
- When the app opens, foreground location revalidates the area. No background location, geofencing, or continuous tracking.
- A notification worker in the same backend codebase sends deduplicated, schedule-aware notifications. It names a dish only when a meal area exists; otherwise it sends a generic nudge.
- Open: cell size, how the area is confirmed or changed, how long it is kept, and whether Home/Work spots remain (question 11); send time, what a dish-naming notification may show, and whether it has actions (question 12).

#### 7 — Minimal journal and avatar

**What it is.** The visible record of exploration. The **journal** lists dishes discovered. The **avatar** is a character that gains cosmetics.

**Implements:** D039 (and D038 for reward validity).

**Done looks like:**

- A new dish, or a new variant, gets a journal entry and a discovery moment, but no cosmetic.
- A cosmetic unlocks only when the user tries a dish from a country new to them.
- The avatar is always computed from currently valid rewards, so a retraction removes its cosmetic.
- What the avatar, its cosmetics, and a journal entry are is open (question 16). The one-home-country rule is proposed, not confirmed (question 1). Whether a new variant counts toward the North Star is open (question 22).

### Definition of MVP done

The MVP is done when a private tester can complete the first loop on their own phone, and the rules below hold.

1. Sign in.
2. Set a meal schedule (weekday lunch by default) and confirm a meal area.
3. Complete dish onboarding.
4. Receive, on schedule, one suggestion: a specific dish at a specific branch, drawn from published offerings.
5. Respond Go, Another, or Not today. Go is final for that meal window.
6. Get to the restaurant through a maps handoff (which map is open, question 5).
7. Confirm the dish they actually ate, including saying they ate something else.
8. Record separately whether they tried it and whether they enjoyed it.
9. See an immediate discovery reward when the dish is new to them.
10. See their updated profile, a journal entry, and the minimal avatar.
11. Correct or retract a confirmation later, with rewards and the avatar following the facts.
12. View progress on confirmed personally-new dishes tried.
13. Change notification settings or delete their product data.

Throughout, the tester never receives an offering that is unpublished, ineligible by live status, or in breach of a constraint they stated. Details that are still open questions in `DECISIONS.md` are not part of this definition until decided.

---

## Part C — Historical (superseded)

Kept so readers understand the code. **Do not build from this part.**

### Old mission (superseded by D032)

"One timely, nearby, unvisited restaurant", with Go / Another / Not today, a maps handoff, and later visit confirmation. The North Star was confirmed positively rated new restaurants (D002, superseded by D033).

### Old milestone plan (summary)

1. **Repository and backend foundation** — done.
2. **Deterministic suggestion API** (`policy_v0`, fixture restaurants, sessions, visits, progress) — done.
3. **Expo vertical slice** — partly done; see the remaining steps below.
4. **Notifications and private-cohort readiness**, which was to generate restaurant suggestions before notifying — superseded by D023 and then by D035. Only two tables exist.

### Old Milestone 3 steps

1. Expo SDK 53 → 58 (D019) — done 2026-10-21.
2. Supabase email sign-in — done 2026-10-21.
3. Meal schedule, price ceiling, Home/Work spots, Been here already (D020, D025, D026) — done 2026-10-25.
4. Google Places provider plus a fixture provider, and `policy_v1` with a price-ceiling filter — **superseded before implementation**: Google Places end to end (D021) and the store-only-IDs supply model (D022) by D034; `policy_v1` (D024) by D032. The step's prerequisite, how a visit gets a cuisine label, was answered by D031, itself superseded before implementation by D032/D034 (cuisine now comes from the catalog, D040).
5. Current-location flow, Home/Work setup, Google map, Google Maps handoff — **superseded**: the location basis is the meal area (D035); the map and handoff choice is open (question 5).
6. Persist session/proposal IDs and queue idempotent writes — **not done; still relevant**. Where it falls in the new order is open (question 19).
7. EAS development/TestFlight build, real bundle identifier, real icons — **not done; still relevant**. Bundle identifier `com.winstontang.nosh` is decided (D029). Placement is open (question 19).

Location-free notifications (D023) are superseded by D035. The ~$50/month budget (D028) is superseded by D043, which leaves the figure open.

---

## Non-negotiable constraints

These match `DECISIONS.md`. They apply to all new work.

- **The unit is a dish at a branch** (D032). Every suggestion, confirmation, and reward is about a specific dish at a specific branch.
- **North Star** (D033): confirmed personally-new dishes tried per active user. Tried and enjoyed are separate signals; enjoyment rate is a guardrail.
- **LLMs offline only** (D041, amending D006). LLMs may help build the catalog and map menus, each with its own evaluation set. Meal-time ranking is deterministic and makes no LLM call.
- **Published offering index** (D034). Meal-time ranking reads only published offerings. Live place status and hours can make an offering ineligible; they never establish that a dish is served.
- **Three data classes, kept apart** (D034): shared catalog, provider content (tagged with source, retrieval date, expiry; purgeable by source), and personal data.
- **Google content other than place IDs is not stored** (D034, keeping one D022 rule).
- **Meal area is a coarse cell, never a point** (D035). Foreground location only; no background location, geofencing, or continuous tracking (D010, D017).
- **Go is intent, not a visit, and is final for the meal window** (D037). The system may supersede only unanswered proposals, recorded separately from user responses. An accepted proposal is never replaced silently.
- **Legacy restaurant data is frozen, read-only history** (D036): no dish backfill, no retrospective rewards.
- **One commit per request** (D038). Confirmation and its rewards are saved together; corrections are appended.
- **Stack limits:** FastAPI modular monolith (D004); PostgreSQL with PostGIS, no pgvector (D013); no microservices, graph database, vector service, or event platform (D041). Expo React Native with strict TypeScript; Expo SDK 58 (D019) — no version change without a recorded decision.
- **Future extension points only:** Nosh Meals and social features. No tables, services, or infrastructure for them now.
- **Out of scope:** delivery, ordering, background location, calendar access, RAG, agents, and public-launch work.
- **Mobile writes are idempotent** (a retried request has the same effect as one request).
- **Never log** precise coordinates, access tokens, or email addresses.
- **Never invent** provider licensing rights, prices, or coverage (D042, D043), or restaurant attributes no source provides.
- **Update the canonical documents** in the same change whenever implementation changes a documented contract or decision.

## Next

**No implementation starts until the owner asks.** Before Milestone 1, the owner should settle, or explicitly defer, these items from the Open questions list in `DECISIONS.md`:

- **One home country per dish** (question 1, D039 — proposed, awaiting confirmation). The catalog must not depend on it until confirmed.
- **Source-experiment thresholds** (question 3, D042). The pass/fail thresholds must be written down before any experiment results are looked at, so they need to be agreed before Milestone 2's experiment starts.
- **Catalog process** (question 17): who reviews generated facts, and the evaluation sets and pass marks.
- **How variants are stored** (the first part of question 24): Milestone 1's tables depend on it.
- **Earlier tester-readiness work** (question 19): where the offline write queue, the EAS/TestFlight build, real icons, and the Fly.io deployment (D030) fall in the new milestone order.

The other open questions (map and handoff, policy weights, quality signal, price ceiling, response meanings, constraints, meal area, notifications, "I ate something else", active user, legacy screens, avatar and journal, sign-in identity deletion, budget, and questions 20–25 apart from the variant part of 24) can be settled when the milestone that needs them comes up. Each milestone above names the ones it touches.

---

## Practical reference

### Outside accounts and keys (as recorded on 2026-10-26)

Not re-checked since 2026-10-26. Never print key values.

| Item | Status on 2026-10-26 |
|---|---|
| Supabase project `arrjixzbzumvxytlimpf` | Free plan. Email sign-in works end to end on a real iPhone. Custom SMTP is the owner's Gmail (app password). The Magic Link and Confirm signup templates send `{{ .Token }}` codes. Upgrade to Pro and move to a domain sender before outside testers |
| Google Cloud | Places API (New) and Maps SDK for iOS are enabled. Server key restricted to Places API (New); verified with one Nearby Search (IDs only) and refused by Geocoding. iOS key restricted to `com.winstontang.nosh` and Maps SDK for iOS. A $50 budget alert is set; the spend cap cannot cover Maps, so daily quotas (about 50 Nearby Search and 150 Place Details per day) are the hard stop. **These keys were set up for the superseded D021 plan. Whether they are used at all under the pivot (for example for place IDs or live status) is an open question (questions 4 and 5)** |
| Expo | `npx expo whoami` returns `winston0753` |
| Apple Developer Program | Not started; approval takes 1–2 days. Needed for the EAS/TestFlight build |
| Fly.io | `flyctl` and `eas-cli` are installed; no Fly account yet (D030). Needed for deployment |
| Domain, privacy policy, app icon | Postponed until before outside testers |

### Git-ignored local configuration

Never commit these files or print their values.

- `apps/mobile/.env.local` holds:
  - `EXPO_PUBLIC_API_URL` — the Mac's Wi-Fi address (on 2026-10-26, `http://192.168.1.73:8000`) so the phone can reach the API; update it if the network changes, and use `localhost` on a simulator;
  - the Supabase URL and publishable key;
  - `EXPO_PUBLIC_GOOGLE_MAPS_IOS_KEY` (set up for the superseded D021 plan; unused by the code).
- `services/api/.env` holds `AUTH_LOCAL_DEV=false`, `SUPABASE_URL`, `GOOGLE_PLACES_API_KEY` (also for the superseded D021 plan; unused by the code), and the database URL.

### Running the app locally

- Docker runs both databases: `db` (port 5432, development data, only ever upgraded) and `db_test` (port 5433, disposable, for destructive migration tests).
- The API runs from `services/api` with `uv run fastapi dev app/main.py --host 0.0.0.0`.
- Expo runs from `apps/mobile` with `npx expo start -c`.
- The owner tests in Expo Go on a physical iPhone. Xcode is not installed, so the simulator is unavailable.
- On 2026-10-26 the development database was migrated to `0005`.
- Full setup and verification commands are in `README.md`.

### Working with this owner

- Explain in plain, non-technical language. Short sentences.
- Commit, push, and open PRs only when asked.
- Leave the untracked `.agents/`, `skills-lock.json`, `research_notes/`, and `reports/` alone.
- When something is unclear, ask, or propose an entry in `DECISIONS.md`. Do not decide silently.

### Engineering expectations

- Inspect Git state before changing anything, and preserve existing work.
- Prefer explicit domain types and small modules over framework abstractions.
- Keep route handlers thin; put workflows in application services and scoring in pure functions.
- One commit per request, with transactions around state transitions (D038). This is the target from Milestone 5 onward; today's services commit internally.
- Make mobile-originated writes idempotent.
- Store timestamps in UTC and schedules with IANA time zones.
- Add tests with each behaviour, especially negative, retry, ownership, and duplicate-event paths.
- Migrations apply to an empty database and have a tested rollback; destructive migration tests run only against `db_test`.
- CI runs without application secrets.
- Do not rewrite or discard the existing cuisine-policy simulator without a documented decision.
- A change is ready for review only when the checks in `README.md` pass (tests, ruff, mypy, `alembic check`, mobile TypeScript, ESLint, Jest, `npx expo install --check`, `npx expo-doctor`) and `git diff --check` is clean. Run them; do not trust counts written in documents.

When an ambiguity conflicts with the canonical documents, stop and raise it as a proposed entry in `DECISIONS.md` rather than choosing a new product direction.
