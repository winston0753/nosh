# Nosh repository direction and low data experiments

## What assumptions in the current product should change?

### Takeaway

Nosh already decided to stop owning a restaurant catalog. The more promising strategic adjustment is to reduce its dependence on exhaustive personal history and learned taste, and help a user act on a small amount of explicit intent. Treat this as a proposed direction, not an accepted change to the canonical requirements.

### Cited Findings

- The product explicitly names “saved places are disconnected from meal timing and location” as a problem, but its journey asks users to accept recommendations, mark prior visits, confirm subsequent visits, and rate them. The target is the founder at weekday lunch plus a small private cohort. [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md:14)
- D021 selects live Google Places; D022 permits provider IDs plus Nosh-owned inputs; D027 retires the curated-catalog plan. This is an accepted repository design, not a fresh legal conclusion or current external API pricing audit. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md:376)
- D025 already removed bulk history classification because it was tedious, replacing it with Been here already on each suggestion. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md:459)
- D024 still proposes a substantial recommendation policy: Bayesian quality floor, hidden-gem boost, walking time, price fit, learned cuisine preference, and national-chain penalty. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md:434)
- The next unresolved implementation choice is how to capture cuisine labels without storing provider-derived data. The handoff recommends asking a user to confirm cuisine at rating time. It is a recommendation awaiting a decision. [IMPLEMENTATION_HANDOFF.md](/Users/winstontang/Downloads/nosh/IMPLEMENTATION_HANDOFF.md:41)
- Cold start already permits uniform priors when personal history is absent. Thus Nosh does not technically need a multi-year review corpus to function, although its intended taste learning and new-to-you guarantee create continuing data collection needs. [RECOMMENDATIONS.md](/Users/winstontang/Downloads/nosh/RECOMMENDATIONS.md:154)
- D002 and PRODUCT make confirmed positive previously unvisited restaurants the North Star. Clicks, intent, and actual visits are intentionally separate. [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md:190)

### Inferences

- Split “owning our data” into three problems: maintaining place facts; asking users to reconstruct historical tastes/visits; and collecting lightweight first-party evidence that Nosh caused useful meals. The first is already outsourced by design. The second can shrink radically. The third remains valuable and can be collected after value is delivered.
- Recommended positioning hypothesis: “Nosh turns places you want to try into meals you actually have.” Initial behavior: share or choose 3–5 places, select a realistic lunch window, get one feasible saved place, go alone or invite one known person, then answer a lightweight optional outcome prompt.
- A tiny explicit wishlist substitutes for learning a taste model for this narrow decision. It does not eliminate place identity resolution, operating hours, distance, price, provider restrictions, or stale wishlists.
- Preserve the distinction between Go and a real visit. Do not make complete history, cuisine taxonomy confirmation, or universal novelty a prerequisite for value. For this pivot, “you saved this” is a more defensible promise than “you have never visited.” Never assume absent history proves novelty.
- A mealtime notification alone is easy to reproduce. The defensibility hypothesis is repeated execution: accessible intake, relevant timing, trusted companions, credible availability, and meals that reliably happen. These are hypotheses requiring retention and outcome evidence, not a demonstrated moat.
- Do not automatically ship bulk imports from Beli, Yelp, Instagram, or Google Maps. Share-link/manual intake can be prototyped; reliable import/sync capabilities and permissions need separate verification. Start with three wants rather than migrating a user's life.

### Gaps

No actual Nosh cohort retention, notification response, historical-data onboarding attrition, or meal conversion evidence was found in the canonical documents. User concern is credible qualitative input, not measured funnel loss. No current competitor claims are made in this note. Historical October 19 provider research was reviewed only as background; it predates the accepted October 20 direction and must not override it.

## How should the proximity and shared wishlist idea be tested?

### Takeaway

Test coordination among existing pairs or small groups before matching nearby strangers. Make availability explicit, short-lived, and tied to a concrete plan; proximity alone does not mean someone wants company or can eat now.

### Cited Findings

- Current product excludes social feeds, following, shared lists, group voting, partner profiles, background location, and calendar access. A social experiment is a proposed scope change, not an unimplemented promised feature. [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md:290)
- D017/D020 use foreground location when the app is opened; D023 sends a generic location-free nudge. Therefore the current design cannot truthfully notify two people that they are both nearby before either opens the app. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md:301), [D023](/Users/winstontang/Downloads/nosh/DECISIONS.md:416)
- The current architecture stores optional Home/Work points and per-user meal schedules; sessions and permissions are individual, not shared. [ARCHITECTURE.md](/Users/winstontang/Downloads/nosh/ARCHITECTURE.md:182)

### Inferences

- User's version compounds at least five requirements: geographically nearby, available at the same time, willing to meet, compatible budget/constraints, and overlapping restaurant wants. Requiring exact wishlist intersection makes matches even scarcer. This trades a historical-data cold start for a local network-density cold start.
- Prefer an existing friend pair, couple, office, or coworking cohort with a recurring overlap. The proposed initial interaction is “Free for lunch near [chosen area] until 12:45,” automatically expiring. Use foreground location or self-declared area, and mutual acceptance before revealing a meeting point. Never imply live proximity from stale location.
- Example: at 11:15 two coworkers opt in; Nosh proposes one saved place and 12:10 departure, both accept or decline by 11:45; if the companion cannot join, the first user still has a valid solo option. The exact timings are experimental, not established optimums.
- Do not require everyone to have saved the same restaurant. A candidate can come from one participant's list if others explicitly accept it and constraints fit. Exact overlap is a useful reason when present, not a universal gate.
- Single-user utility prevents the app being empty before friends join. Invite through an ordinary shareable proposal in the experiment; a browser response without full account setup is a hypothesis to reduce recipient friction, not a feature already supported by the current app.
- A stranger product adds identity, blocking/reporting, unwanted-contact controls, no-show handling, meeting safety, and neighborhood density needs. This is a different business bet and should be deferred until known-contact coordination shows demand.

### Gaps

There is no existing group-sharing permission model, invite acceptance flow, short-lived availability object, or group state machine documented. There is no local density evidence or stated preference for dining with strangers. These cannot be assumed because people like discovering restaurants.

## What is the smallest next decision and experiment?

### Takeaway

Recommend a narrow saved-intent experiment with optional known-companion coordination. Validate whether reminders, availability, or social commitment solve the actual bottleneck before increasing ranking sophistication or building a stranger marketplace.

### Cited Findings

- Reusable documented work includes authenticated per-user state, schedules/price ceilings, Home/Work API, sessions, deterministic proposal queues, transactional idempotent responses, visit confirmation/correction, and account-data deletion. [ARCHITECTURE.md](/Users/winstontang/Downloads/nosh/ARCHITECTURE.md:182), [notes.md](/Users/winstontang/Downloads/nosh/notes.md:3)
- Mobile actual location, live provider, Google map, durable writes, and tester distribution remain unfinished in the handoff; notifications are Milestone 4 and must not begin before Milestone 3 under the current accepted plan. [IMPLEMENTATION_HANDOFF.md](/Users/winstontang/Downloads/nosh/IMPLEMENTATION_HANDOFF.md:41)
- The product's validation targets are explicitly hypotheses rather than external benchmarks. [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md:190)

### Inferences

Proposed directions, ranked by fit and learning value:

1. **Saved place activation:** turn 3–5 saved places into a timely, feasible suggestion. Lowest dependency on other users and shortest distance from today's product. Key uncertainty: forgotten intent versus logistical impossibility.
2. **Lunch buddy within an existing group:** a lightweight “going at 12:10, join?” with explicit availability. Potential distribution through invitations, but coordination overhead may exceed meal value.
3. **One shared food outing each week:** pairs choose a feasible future occasion for a place they both want. For restaurants requiring planning, a nudge at hunger time may be too late. This should be tested as timing variation rather than a reservation product.
4. **A small active shortlist:** “try soon / waiting for a friend / special occasion,” with at most a few active wants. This distinguishes actionable intent from collecting hundreds of bookmarks. Benefit must outweigh classification friction.
5. **Trusted friend picks:** ask one trusted person for three places, then help execute them. A way to avoid reconstructing tastes, but not a public feed, reviewer graph, or guaranteed superior recommendation.

Proposed pilot, not a statistical efficacy claim:

- Recruit roughly 12–20 consenting people, including several existing pairs in one lunch area. Ask why their last three saved restaurants remain unvisited: forgotten, distance, occasion/price, lack of company, reservations, or lost interest. Don't assume nudging addresses every cause.
- Collect only 3–5 realistic wants per participant. Observe whether intake itself loses participants; high-friction setup invalidates the pitch.
- Over about two weeks, compare comparable opportunities with a solo actionable nudge and with optional known-companion invitations. Include some preselected no-nudge opportunities if participants consent, rather than claiming all visits after a nudge were caused by Nosh. Tiny sample and changing circumstances limit causal interpretation.
- Observe completed meals, repeat voluntary use, time needed to coordinate, invitations accepted, no-shows, notification mute requests, and why proposals failed. An unconfirmed outcome remains unknown, not an inferred visit or failure.
- Suggested qualitative continuation test: multiple participants use it again after their first meal without founder chasing; invitations produce meals that participants say were otherwise unlikely; people want the service to continue. Set numerical decision thresholds before starting if desired, but do not present invented percentages as industry benchmarks.
- Stronger interest in companion finding means pursue coordination. Stronger solo conversion means keep it single-user. If people like the idea but don't act even on feasible existing wants, stop polishing ranking and revisit the job.

Proposed documentation changes only after the founder chooses a direction:

- PRODUCT: change main job and journey from exhaustive novelty to acting on explicit intent; clarify whether repeat visits with companions are allowed; keep quality and notification burden as guardrails. Proposed primary outcome: confirmed wanted meals completed per active user, with positive-new-discovery outcomes retained as a separate secondary metric. A friend returning to a place to join you can be a successful coordinated meal even though strict novel-only progress gives that friend no credit.
- DECISIONS: record a new proposal addressing scope, metric, candidate source, optional social mode, and foreground privacy. Supersede only the relevant portions of D002/D024/D025, not the backend architecture.
- RECOMMENDATIONS: replace taste-learning dependency with simple feasibility/explicit-intent ordering for the experiment; preserve deterministic code and exclusion semantics where still relevant.
- The roadmap currently defers the supposed core differentiator—the nudge—to Milestone 4 while much foundation and ranking work precede it. This is a validation-order mismatch, not a reason to violate the milestone rule silently. Test the nudge manually with consenting participants before more implementation.
- IMPLEMENTATION_HANDOFF: explicitly reprioritize the validation path before production notification/social implementation; current ordering remains binding until revised. A manual pilot can learn about the nudge without pretending the native notification implementation already exists.
- Keep provider abstraction, reliable writes, authentication, and existing simulator. Do not rewrite foundations; do not let sunk ranking work dictate product strategy.

### Gaps

Willingness to pay and distribution are unvalidated. A weekly habit may have different retention and monetization from weekday lunch. The experiment needs a chosen target group and actual participant availability. No code, canonical docs, database, or tests were changed or run for this strategy review; documented historical test counts were not represented as freshly verified. Git diff --check passed and tracked work was unchanged when inspected.
