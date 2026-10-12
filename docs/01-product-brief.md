# Nosh — product brief and pressure test (v0, pre-design)

*Historical pre-design brief. The product was subsequently named Nosh.*

## TL;DR

- **Good project, wrong center of gravity.** The core is a recommender + notification UX + data-capture problem. As specified, no step in the flow needs an LLM, so on its own it would **not** close the "RAG agent + tracing + eval suite" gap. It can, once the LLM is put where language is actually the problem (below).
- **Biggest risks, in order:** (1) knowing what the user actually ate, (2) the been-to % objective, which is confounded with taste, (3) notification friction, (4) data licensing and the delivery handoff.
- **The been-to % policy as written loses to picking cuisines at random** in simulation (64 vs 76 new restaurants over 90 days; a rejection-learning policy gets 80). See [Simulation](#simulation-is-lowest-been-to--a-good-policy).
- **Recommended shape:** deterministic decision core, LLM only at the language edges, eval suite built on a user simulator. Python backend first, TestFlight before App Store.

## The idea as proposed

At lunch and dinner (not breakfast) the app nudges the user:

1. In the mood for lunch? → **no**: snooze, or "not today".
2. In the mood for *{cuisine}*? → **no**: shuffle to another cuisine (not randomly — prefer cuisines with a low *been-to %*).
3. Recommend the best nearby restaurant of that cuisine the user hasn't tried.
4. Accept → delivery or pickup → hand off to Grubhub (or similar) for that restaurant.

Goal: maximize the number of distinct neighborhood restaurants the user tries. Target: iOS App Store.

## What works

1. **Real problem, and you're user #1.** You can dogfood daily, which is the cheapest user research there is.
2. **Push, not pull.** Most food discovery waits for you to open an app. A proactive nudge at decision time is a genuine angle.
3. **The objective is measurable.** "Distinct new restaurants tried per month" is a clean North Star, which makes the whole system evaluable. Rare for consumer AI ideas.
4. **Been-to % is a great *user-facing* feature.** "You've tried 3 of 14 Thai places near the office" is a collection mechanic (neighborhood Pokédex). It may be the hook that makes people keep the app. It's a weak *decision rule* (below), but a strong UI.
5. **Decision reduction.** One suggestion beats a list of 40 when you're hungry.
6. **It maps onto your roadmap** — FastAPI/Postgres backend, an MCP server, retrieval, Langfuse, evals with real statistics, LangGraph human-in-the-loop. See [03-learning-map.md](03-learning-map.md).

## What doesn't work, and the fix

### 1. The app doesn't know what you ate (ground truth)

It only sees *intent*: you accepted a suggestion and tapped Order. It doesn't know whether you went, and it never sees meals eaten outside the app. Every metric — been-to %, "hasn't tried", the objective itself — rests on this.

**Fix (cheapest first):**
- **Onboarding import:** swipe through ~40 nearby places: *been / not been / not interested*. Seeds the visit history and a taste prior.
- **Next-meal confirmation:** "Did you end up at Lers Ros?" 👍 / 👎 / didn't go. One tap; also gives you a **rating**, which you need anyway — "try new places" only works if the new places are good.
- **Quick log** for off-app meals ("had pho at that place on Castro"), which is a good LLM job (see below).
- **Later, optional:** automatic visit detection with Core Location. Requires *Always* location permission, costs battery, and draws App Review and privacy scrutiny. Not v1.

### 2. Been-to % is confounded with taste

You've been to fewer places in cuisines you like less. So "lowest been-to %" often means "the cuisine you avoid", and the app keeps leading with it. Three more problems:
- **No learning:** a rejection doesn't change been-to %, so a disliked cuisine stays first forever.
- **Small denominators:** 2 Ethiopian places, one visit = 50%. The metric is noise for small cuisines.
- **% is the wrong unit:** for "try as many as possible", 30 unvisited Chinese places is a bigger pool than 2 unvisited Peruvian ones, even though Chinese has the higher been-to %.

**Fix:** score each cuisine as *P(you accept it now) × value of its best unvisited options*, and learn P(accept) from every shuffle — each rejection is a free label. That's a (contextual) bandit; Thompson sampling is the simple version. Treat your history frequency as evidence of *taste*, not only of depletion. Keep been-to % for display.

### 3. A two-question chain is high friction

"Hungry?" then "{cuisine}?" then the restaurant then delivery/pickup is four decisions. Each step loses people. An iOS notification shows a few action buttons and each tap is one turn; a multi-step flow *inside* a notification needs a Notification Content Extension, which is hidden behind a long-press most users never do.

**Fix:** the notification *is* the "are you hungry" question, so fold it in. One notification, one decision:

> **Lunch? Try Thai → Lers Ros** · new to you · 0.4 mi
> [Go] [Another] [Not today]

"Another" re-suggests in place; "Not today" doubles as the skip signal (learn skip days, e.g., team-lunch Tuesdays). Hypothesis to A/B in TestFlight: a concrete place converts better than an abstract cuisine.

### 4. Ordering handoff has no API, and the branch is muddled

Grubhub's developer API is for merchants and POS / online-ordering providers, not consumer apps placing orders. As far as I know, DoorDash and Uber Eats are similar — their developer products are merchant- or logistics-side. So you can only **link out**, and matching a place from your data source to its page on a delivery app is a fuzzy entity-matching problem without a search API.

Also, the spec routes *pickup* to Grubhub; delivery is the case that actually needs a delivery app. The real fork is **"go there"** (Apple Maps directions) vs **"order"** (pickup or delivery). And delivery changes the candidate set: delivery radius ≠ walking distance.

**Fix (v1):** Go → Apple Maps. Order → the restaurant's own site/order link when known, otherwise the delivery app's search. Infer mode from context (weekday lunch at the office ≈ walk).

### 5. "Best" restaurant collides with data licensing

- **Google Places:** you may store only place IDs indefinitely; names, ratings, photos and so on can't be cached, so every display is a billable call, with required attribution and a public Terms/Privacy page.
- **Yelp:** paid plans after a trial (reportedly from ~$229/month). Many indie apps shut down after the 2024 pricing change.
- **Foursquare Open Source Places:** 100M+ POIs, Apache 2.0, refreshed monthly, granular categories, storable in your own DB. Core fields only (name, location, categories) — richer attributes are paid tiers — and coverage quality varies.

**Fix:** FSQ OS Places as the restaurant universe in your own Postgres (you can compute been-to % over it), plus live Google Places calls only for the one card being shown. Define "best" explicitly: Bayesian-averaged rating (so 4.9 from 8 reviews doesn't beat 4.6 from 900), open now, distance, your own past ratings.

### 6. "Nearby" is two neighborhoods, and fixed-time nags fail

Lunch is near the office, dinner near home — two universes, two been-to maps. A noon nag during a meeting gets swiped away and trains you to ignore it.

**Fix:** configurable meal windows; calendar-aware timing (nudge at the first free 30 minutes in the window). That's a good, legitimate agent job.

### 7. The LLM isn't load-bearing in the spec

The flow is a state machine. An LLM generating "Are you in the mood for lunch?" adds latency, cost and nondeterminism, and nothing else. Interviewers will spot an LLM bolted onto a deterministic flow. The decision at noon should be precomputed and deterministic.

**Fix:** put the LLM where language is the actual problem — see [Where AI is load-bearing](#where-ai-is-actually-load-bearing).

### 8. App Store is the last mile, not the first

Fine as a goal, but it adds the $99/year developer program, privacy policy and nutrition label, location-permission justification, and review. A solo Swift app + backend + LLM layer is a lot alongside a new job. Ship to TestFlight for yourself and a few friends first; the App Store follows evidence that people keep it.

## Simulation: is lowest been-to % a good policy?

`spike/cuisine_policy_sim.py` simulates 500 users for 90 days (lunch + dinner). Each user has a hidden per-cuisine taste and a pre-app history that follows that taste. Every policy uses the same restaurant recommender (best unvisited); only the cuisine choice differs. Same users across policies, so the deltas are paired.

**Without churn** (rejections never make users mute the app):

| Policy | New restaurants (90d) | Δ vs spec | Rejections / session | Cuisine accept rate |
|---|---|---|---|---|
| random | 76.1 ± 0.9 | +11.7 ± 0.9 | 1.08 | 44% |
| **lowest been-to % (spec)** | **64.3 ± 1.4** | — | **1.64** | **31%** |
| weighted by (1 − been-to %) | 74.0 ± 0.9 | +9.6 ± 0.8 | 1.18 | 41% |
| Thompson sampling × unvisited pool | 79.8 ± 0.8 | +15.4 ± 1.0 | 0.91 | 49% |
| Thompson + history-as-taste prior | 80.5 ± 0.8 | +16.2 ± 1.0 | 0.87 | 51% |
| oracle (knows true taste; upper bound) | 82.0 ± 0.8 | +17.6 ± 1.0 | 0.81 | 53% |

**With churn** (each rejection adds 1 point of per-session probability of muting the app), the learning policy finds ~2× as many new restaurants as the spec (51.2 vs 24.4), because the spec's rejections drive users to mute it.

**Takeaways**
- The spec policy is worse than random, and it rejects ~2× as often as the learning policies.
- The learning policies close ~90% of the gap between the spec and the oracle without knowing taste.
- History frequency is better used as *taste* evidence than as depletion evidence.

**Caveats:** toy model. Taste is static, sessions are independent, churn is a made-up hazard. The direction is robust to the churn assumption (both tables); the magnitudes are not a forecast. Next step for the simulator: replace synthetic users with your own two-week meal diary.

## Where AI is actually load-bearing

| Capability | Why it needs a model | Technique | How you'd eval it |
|---|---|---|---|
| Craving search: "something spicy and brothy, not heavy" | Free text → restaurants | RAG over menus/descriptions: hybrid search (BM25 + pgvector) + reranking | recall@k / nDCG on a hand-labeled set of ~100 cravings |
| Cuisine taxonomy normalization | "Asian Fusion", "Noodle House" → your taxonomy | Structured outputs, batch at ingestion | Accuracy vs. labeled sample; confusion matrix |
| Natural-language meal logging | "pho w/ coworkers at the place on Castro" → place_id | Tool calling + entity resolution against your DB | Exact-match accuracy; human review of misses |
| "Why this place" explanations | Grounded summary of reviews/menu | RAG with citations | Faithfulness via a calibrated LLM judge |
| Concierge agent ("plan my lunches this week") | Multi-step, tools, calendar | Agent loop → LangGraph with `interrupt()` for your yes/no | Task success + tool-call correctness, traced in Langfuse |
| Cuisine policy | Not an LLM job | Bandit (this spike) | Offline policy eval on the simulator, paired CIs |

## Proposed scope, by phase

| Phase | What | Proves |
|---|---|---|
| 0. Validate (≈2 weeks) | Meal diary: what you ate, would you have accepted the suggestion? Pull FSQ OS Places for your two areas. Settle open questions. | Problem and data exist |
| 1. Core | FastAPI + Postgres/pgvector; ingestion + taxonomy normalization; policy service; simulator in CI; **MCP server over your food history** (use it from Claude) | Backend + MCP |
| 2. Language layer | Craving RAG, NL logging, Langfuse tracing, eval suite; rebuild the agent in LangGraph and compare | RAG, agents, evals |
| 3. iOS | Local notifications with actions, one-screen card, TestFlight with you + a few friends | Real usage data |
| 4. App Store | Only if TestFlight users keep it | Retention |

Phases 1–2 are portfolio-ready before any Swift is written.

## Landscape (light)

Beli (been / want-to-try lists and rankings), Google Maps saved lists, Yelp collections, and delivery apps' own recommendations all overlap. The ones I know of are pull-based; the proactive nudge plus neighborhood-completion mechanic is the gap. Verify before positioning claims.

## Sources

- [Google Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies) — caching limits, attribution, Terms/Privacy requirements
- [Yelp API report card (supergood.ai)](https://supergood.ai/api-report-card/yelp) — Yelp pricing and 2024 change (third-party summary)
- [Foursquare OS Places on Hugging Face](https://huggingface.co/datasets/foursquare/fsq-os-places) and [schema](https://docs.foursquare.com/data-products/docs/places-os-data-schema)
- [FSQ OS Places overview (openplacesapi.com)](https://openplacesapi.com/blog/fsq-os-places-free-place-search) — size, license, refresh cadence
- [Grubhub for Developers](https://grubhub-developers.zendesk.com/hc/en-us) — merchant/POS partner integration API
