# Nosh Recommendation System

- **Status:** Dish policy accepted (not implemented). The code runs `policy_v0`, the restaurant policy (Appendix A)
- **Last updated:** 2026-11-10

> **Read this first.**
>
> - **Accepted, not implemented:** Nosh is moving to a dish policy. It suggests one dish at one restaurant branch (DECISIONS.md D032). Sections 1–6 describe it only as far as it has been decided. **No dish policy code exists yet.** Weights, proportions, thresholds, and the meaning of each response for a dish are not decided; they are listed in section 5, "Open questions".
> - **Implemented (historical design):** the code on `main` still runs `policy_v0`. It suggests one nearby restaurant the user has not visited, from 20 fictional San Francisco fixture places. Appendix A describes exactly what it does today.
> - **Historical, never built:** `policy_v1` (D024) was a planned restaurant policy built on Google Places data. It was never built and is superseded by D032. Appendix B keeps a short record of it.
>
> The dish policy has no version name yet. This document does not invent one.

## 1. Objective

The North Star is **confirmed personally-new dishes tried per active user** (D033). "Personally new" means new to that user, not new to the world.

- **Tried** and **enjoyed** are two separate signals, recorded separately (D033, D038).
- A dish the user tried and did not enjoy still counts as tried.
- **Enjoyment rate is a guardrail.** It is watched alongside the count, but it is not part of the count. A falling enjoyment rate warns that exploration is producing poor meals.
- Changing whether a dish was enjoyed never changes whether it was new (D038).

The policy must not optimize raw novelty, Go taps, clicks, or Maps handoffs on their own. Go is intent, not a meal.

What counts as an "active user" is open (DECISIONS.md open question 14).

## 2. Terms

- **Dish:** an entry in Nosh's own catalog, such as a named dish people order (D040).
- **Variant:** a version of a dish that eats differently: a regional style, a different main protein, or a different preparation. Variants are one level deep (D040).
- **Alias:** another name for the same dish or variant. It has no ID of its own (D040).
- **Branch:** one physical location of a restaurant.
- **Offering:** a dish (or variant) offered at a specific branch, backed by menu evidence.
- **Published offering:** an offering that has passed Nosh's offline pipeline and review (D034). Only published offerings can be suggested.
- **Dish experience:** the record that a user actually ate a dish, confirmed after the meal (D038).
- **Session:** one decision opportunity for one user and one meal window. There is still one session per user and meal window (D037).
- **Proposal:** the one dish-at-a-branch shown to the user at a given point in a session.
- **Explicit constraint:** a limit the user has stated, such as a dietary rule. Which constraints are collected is open (open question 10).

## 3. The dish policy: what is decided

Everything in this section is **accepted but not implemented**.

### 3.1 The unit

The policy picks **one specific dish at one specific restaurant branch** (D032). Everything that used to be built around "a restaurant" is redefined around "a dish at a branch": ranking, confirmation, the success metric, and history.

### 3.2 What the policy reads

- **Only published offerings** (D034). The index is built offline: sources → adapters → branch match → source-backed menu items → mapping to the dish catalog → review → published offering. Meal-time ranking never reads raw provider content directly.
- **Live place status and opening hours, as a separate eligibility input** (D034). They can make an offering ineligible right now (for example, the branch is closed). They never prove that a restaurant serves a dish. Which provider supplies them is open (open question 4).
- **The shared catalog** for facts about dishes, including cuisine (D040). Cuisine comes from the catalog, not from place types.
- **The user's own data:** preferences, explicit constraints, the meal area (D035), and their dish experiences.

### 3.3 Eligibility rules that are decided

1. The offering is published.
2. The live status and hours do not make it ineligible right now.
3. It respects every explicit user constraint. **The policy never overrides an explicit constraint**, even when that leaves nothing to suggest.
4. **A restaurant the user has already visited does not exclude its dishes** (D036). A familiar restaurant can serve a dish that is new to the user. This is the opposite of what the code does today (Appendix A.2).

Other rules, such as whether a dish or branch may repeat within a session or in back-to-back meal windows, are not decided (section 5).

### 3.4 Three kinds of suggestion

Suggestions come in three kinds (D032):

- **Familiar:** close to what the user already eats and enjoys.
- **Adjacent:** a step away from what the user knows.
- **Broader exploration:** further afield, such as a dish from another culinary region.

When the user's recent experience is concentrated (for example, mostly one cuisine), the policy **widens toward other culinary regions**. It never does this by breaking an explicit constraint.

The balance between the three kinds, how "concentrated" is measured, and how fast the policy widens are **open** (open question 6).

### 3.5 What the policy learns from

- **Taste evidence comes from dish experiences** (D038). It is derived from the experience history each time it is needed, not stored separately as the source of truth. That means it can always be recomputed.
- **Tried and enjoyed are separate signals** (D033, D038). A dish can be tried and not enjoyed.
- **Corrections are appended as new events** (D038). If the user changes which dish they ate, both the old and the new dish are re-evaluated. If the user retracts an experience, it stops counting.
- **"Been here" keeps its meaning** (the user had been to that restaurant before Nosh) but is **a familiarity signal only** (D036). It no longer removes the restaurant from suggestions.
- **Old restaurant data is frozen history** (D036). Restaurant visits and place states recorded before the pivot are kept, read-only. They are not turned into dish experiences.

What Another, Not today, and "Been here" should teach the dish policy is **open** (open question 9). D011's rule for Another was written for restaurants.

### 3.6 Menu evidence is not quality evidence

A published offering shows that a branch **offers** a dish. It does not show the dish is **good** (D034). Google ratings are not stored (D034 keeps D022's rule that Google content other than place IDs is not stored). What quality signal, if any, the dish policy uses is **open** (open question 7). Until it is decided, a sensible precaution (a recommendation of this document, not a recorded decision) is that the card does not imply a dish is the best of its kind.

### 3.7 Deterministic at meal time; LLMs only offline

- **Meal-time ranking is deterministic and makes no LLM call** (D041, amending D006). The same inputs and policy version must give the same suggestion.
- LLMs may be used **offline** for catalog generation and menu mapping (D041). Their output reaches the policy only as stored facts marked generated, reviewed, or source-backed (D040), and as reviewed offerings (D034).
- The policy is versioned (D006). Each proposal records the version that produced it. The version name is not chosen.

### 3.8 Sessions and replacement

These session rules affect what the policy may do (D037):

- Go is final for that meal window. There is no "change my pick".
- The system may replace an **unanswered** proposal, for example when the location changed or the offering went stale. That replacement is recorded separately from user responses, so it is never read as the user's feedback.
- An accepted proposal is never replaced silently. If an accepted offering goes stale, the user sees a notice.

## 4. Evaluation

### 4.1 For the future dish policy

**Offline LLM tasks.** Catalog generation and menu mapping each need their own evaluation set before their output is trusted (D041). Who reviews generated facts, the evaluation sets, and their pass marks are open (open question 17). The D042 source experiment separately measures mapping accuracy, branch correctness, and freshness for each candidate source.

**Human-labeled checks.** Build a small review set of representative users, meal areas, and constraints with the offerings that should and should not be eligible. Check that:

- only published offerings appear;
- closed branches are excluded;
- explicit constraints are never broken;
- a visited restaurant's dishes still appear;
- the dish shown is really offered at that branch;
- any reason shown to the user is factual.

**Logged-session replay.** Once real sessions exist: re-run the policy on stored inputs to confirm it reproduces the same proposal; compare rankings between versions without claiming that one causes better outcomes; use counterfactual methods only after the needed probabilities are logged correctly.

**Online observation** (no automated A/B testing in phase one). Track by policy version:

- confirmed personally-new dishes tried (the North Star);
- enjoyment rate (the guardrail);
- the mix of familiar, adjacent, and broader suggestions shown and accepted;
- Go rate, Another per session, and confirmation rate;
- how often the user reports eating something else;
- no-candidate rate;
- notification disable rate.

Do not promote a policy because it raises Go taps if it lowers confirmed new dishes or enjoyment, or raises notification disabling.

**Tests to write when the dish policy is built.** These follow directly from accepted decisions:

- only published offerings are ever proposed;
- an offering made ineligible by live status is never proposed;
- an explicit constraint is never overridden;
- a visited restaurant does not exclude its dishes;
- no LLM call happens in the meal-time path;
- the same inputs and version reproduce the same proposal;
- every proposal records its policy version;
- a system replacement is never recorded as a user response;
- duplicate events do not count twice;
- changing "enjoyed" never changes novelty or a reward.

### 4.2 The existing simulator

The paired-user cuisine simulator (`spike/cuisine_policy_sim.py`) stays. It is a **regression test of the cuisine-selection mechanism** used by `policy_v0`. It is not a forecast, and it does not model dishes. It treats a rejected proposal as cuisine feedback more strongly than the product does (Appendix A.6). Run it with the commands in `README.md`.

## 5. Open questions

These are **not decided**. Do not build on an assumed answer. The canonical list is "Open questions" at the end of `DECISIONS.md`; numbers below refer to it.

- **Policy weights (open question 6).** The balance between familiar, adjacent, and broader-exploration suggestions; how "recent experience is concentrated" is measured; how fast suggestions widen toward other culinary regions.
- **Restaurant quality (open question 7).** Menu evidence does not establish quality, and Google ratings are not stored. What quality signal, if any, the dish policy uses is undecided.
- **Price ceiling (open question 8).** How the per-meal ceiling (D026) applies to dish offerings. Today it is stored and used nowhere.
- **Response meanings for dishes (open question 9).** What Another, Not today, and "Been here" teach the dish policy.
- **Explicit constraints (open question 10).** Which constraints onboarding collects and how they are worded. The policy never overrides them, whatever they are.
- **Live place status and opening hours (open question 4).** Which provider supplies them, and what its terms require of the card.
- **"I ate something else" (open question 13).** How the user picks the actual dish at confirmation, and what happens when it is not in the catalog.
- **Active user (open question 14).** The period that defines "active" for the North Star, and any target values.
- **Catalog process (open question 17).** Who reviews generated facts, the evaluation sets and their pass marks, and how catalog versions are numbered.

- **Initial dish preferences (open question 20).** How onboarding answers shape suggestions for a new user with no dish experiences.
- **Repetition (open question 21).** Whether the same dish, or the same branch, may be proposed again within a session or in back-to-back meal windows.
- **Variants and the North Star (open question 22).** Whether trying a new variant of a dish the user has already had counts as a personally-new dish. (D039 gives a new variant a journal entry, but does not say whether it counts toward D033.)
- **Nothing eligible (open question 23).** What the user sees when no published offering is eligible, and whether any rule may be relaxed (explicit constraints may not).

The dish policy's version name, formulas, and any numeric thresholds are also undecided.

## 6. Out of scope

These are not part of phase one. Each would need its own ground truth, failure cases, and evaluation set before being built:

- contextual bandits using time, weather, companions, or calendar state;
- free-text craving search;
- embeddings and vector retrieval (pgvector stays absent, D013);
- learned quality models;
- group preferences (social features are a possible later extension only);
- causal online experiments;
- any LLM call at meal time (rejected, D041);
- automatic dietary or allergen inference.

---

## Appendix A — policy_v0: what the code does today (restaurant policy, historical design)

**Status: implemented.** This is the only recommendation policy in the code. Its unit is a restaurant, and its design is superseded by the dish policy (D032). It will keep running until dish ranking is built. Code: `services/api/app/recommendations/` (pure engine) and `services/api/app/places/service.py` (candidate building); sessions call it from `services/api/app/suggestions/service.py`.

### A.1 Objective (historical)

`policy_v0` was designed to increase confirmed, positively rated new restaurant visits (D002, now superseded by D033). The progress screen still computes that restaurant metric.

### A.2 Eligibility filters

`build_candidates` keeps a place only when all of these pass:

1. The place is active.
2. It is within **a fixed 1,600 m radius** of the session's anchor point. The anchor is the transient device location sent with the request or a saved Home/Work spot. (The app today always sends a hard-coded San Francisco Mission point.)
3. The user's state for it is not `visited`. This includes places marked "Been here already" and places confirmed through Nosh.
4. The user's state for it is not `not_interested`.
5. It has not already been proposed in this session.
6. It has at least one cuisine. The primary cuisine is used; if none is marked primary, the first is used.

Not applied, although the old design or the stored data mentions them:

- The per-meal **price ceiling** is stored but **not used** in filtering or ranking.
- Opening hours are not checked.
- No other explicit user constraint exists.

If nothing is eligible, the session ends in `no_candidates` with the reason code `no_eligible_candidates`.

### A.3 Cuisine score

The policy has two levels: pick a cuisine, then pick the best eligible restaurant in it.

For each cuisine `c` that still has eligible, unproposed places:

```text
cuisine_score(c) = theta_c × pool_value(n_c)

pool_value(n) = 1 - exp(-n / 2)
theta_c ~ Beta(alpha_c, beta_c)
```

`n_c` is the number of eligible places in that cuisine not yet proposed in the session. The cuisine with the highest score wins; an exact tie goes to the lower cuisine ID string.

Prior:

```text
alpha_c = 1 + 4 × f(c)
beta_c  = 1 + 4 × (1 - f(c))
```

`f(c)` is the share of the user's pre-Nosh places whose primary cuisine is `c`. With no pre-Nosh history at all, every cuisine uses `Beta(1, 1)`. With history, a cuisine absent from it has `f = 0`, giving `Beta(1, 5)`.

Then confirmed outcomes are added:

```text
alpha_c += number of positive proposal-backed visits in c
beta_c  += 0.25 × number of negative proposal-backed visits in c
```

**Provenance.** Pre-Nosh history is only places with `was_visited_before_nosh = TRUE`: places the user marked "Been here already" on a suggestion (D025), or Been during the former onboarding step (D018). A place that became visited through a Nosh confirmation or a manual settings edit is not history. Outcomes come only from proposal-backed visits; manual visits do not change cuisine preference (D015). So a visit is never counted both as history and as an outcome.

The simulator supported this mechanism over "lowest been-to percentage" under its assumptions. The prior strength of 4 was a hypothesis.

### A.4 Restaurant score

Within the chosen cuisine:

```text
place_score =
    0.45 × quality_score
  + 0.30 × distance_score
  + 0.15 × context_fit
  + 0.10 × exploration_score
```

- `quality_score`: the fixture's fictional `quality_score` from place metadata; 0.5 when missing.
- `distance_score`: `1 - distance / 1,600 m`, so 1 at the anchor and 0 at the edge.
- `context_fit`: 1.0 when a meal type is given and the cuisine is the place's primary cuisine, otherwise 0.5. Sessions always pass a meal type and fixtures have primary cuisines, so in practice it is constant.
- `exploration_score`: a hash of the place ID and sequence number, scaled to `[0, 1]`. It acts as a deterministic tie-breaker, not a real measure of exposure.

The highest score wins; an exact tie goes to the lower place ID string.

Reason codes emitted: `nearby` (distance score above 0.7), `new_to_you` (always), and `highly_rated` (quality above 0.7). The codes `preferred_cuisine` and `many_options_remaining` appeared in the old design but are never emitted.

### A.5 Determinism and the candidate queue

The random draw is seeded from the session ID, the sequence number, and the policy version. At session creation the whole ranking is computed once and stored as the session's candidate queue: entry *n* is what the policy would propose after the first *n − 1* were declined. Another and "Been here already" take the next queue entry. Go and Not today close the session and empty the queue. Creating a session also empties the queues of the user's other sessions. A repeat request for the same meal window returns the existing session and its queue, whatever location it carries.

### A.6 Feedback semantics (D011, restaurant)

- **Confirmed positive visit (proposal-backed):** strong positive cuisine evidence (`alpha += 1`).
- **Confirmed negative visit (proposal-backed):** weak negative cuisine evidence (`beta += 0.25`).
- **Manual visit:** history for the progress screen; no cuisine update (D015).
- **Not interested:** hard exclusion of the place.
- **Been here already:** marks the place visited before Nosh, excludes it, feeds the history prior, and never counts toward the North Star (D018, D025).
- **Go:** intent only; not a visit or a rating.
- **Another:** no cuisine update. It may mean cuisine, distance, mood, or curiosity.
- **Not today:** timing only; closes the session; never updates preference.

The simulator treats a rejected proposal as cuisine feedback more strongly than this. That difference is deliberate and stays explicit.

### A.7 How preference is computed

There is no stored preference table. Each time a session is created, cuisine evidence is recomputed from place states and proposal-backed visits (`app/recommendations/priors.py`). The old design's materialized `cuisine_preference_state` was never built.

### A.8 Cold start

- With pre-Nosh history: the cuisine mix of "Been here already" places is a weak prior; those places are excluded.
- Without history: `Beta(1, 1)` for every cuisine, and `pool_value` favours cuisines with several eligible places.
- New place: neutral quality 0.5.

### A.9 Repetition

A place is never repeated within a session. The old design's rule against proposing the same place in consecutive meal windows was not implemented. Recent cuisine exposure is not tracked.

### A.10 Logged decision record

Stored today:

- on the session: policy version, meal-schedule version, and anchor source (`device`, `home`, `work`, or `legacy_context`; never the coordinate);
- on each proposal: place ID, cuisine ID, sequence number, total score, each score component, reason codes, and a snapshot holding the candidate count, chosen cuisine, sampled cuisine value, unvisited pool size, exclusion counts, session seed, and distance in metres.

The candidate place IDs themselves are not stored, only their count. The user's coordinates are not stored.

### A.11 Known defects

Found 2026-10-19 and confirmed 2026-10-20. `policy_v1` was meant to fix them; it was never built, so they remain:

- `highly_rated` comes from the fixtures' fictional `quality_score`.
- Cuisine samples are drawn in the order candidates are met, and the radius query sorts only by distance. Equal distances or reordered input can change the winner.
- `exclusion_counts` is always empty.
- `context_fit` does not depend on the meal type.

### A.12 Required invariants (as currently tested)

Automated tests cover:

- visited places are never eligible;
- Not interested places are never eligible;
- inactive and out-of-radius places are never eligible;
- a place is not repeated within a session;
- Not today does not change cuisine preference;
- duplicate responses do not change state twice;
- the same session and seed reproduce the same proposal;
- every result carries the policy version;
- an exhausted candidate set returns `no_candidates` safely;
- pre-Nosh history comes only from "Been here already", and outcomes only from proposal-backed visits.

Run the checks in `README.md` for current results.

## Appendix B — policy_v1 (historical, never built)

`policy_v1` (D024, 2026-10-20) was the planned successor to `policy_v0`. It would have ranked restaurants using live Google Places data (D021): hard filters for opening hours and the price ceiling, a review-count-adjusted quality floor, a hidden-gem boost, price fit, and a national-chain penalty, with candidates sorted by provider ID before sampling. **It was never built.** D032 superseded it, and D034 superseded the Google Places supply model it relied on. It is kept here only as history; none of its components is part of the dish policy.
