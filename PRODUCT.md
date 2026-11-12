# Nosh Product Requirements

- **Status:** Requirements for the dish-first direction. **Almost nothing described here is built yet** (see §2)
- **Version:** 0.2 (replaces 0.1, the restaurant-first baseline of 2026-10-20)
- **Last updated:** 2026-11-10
- **Product name:** Nosh

This document says what Nosh should do. It does not say what the code does today. The decisions it relies on are in `DECISIONS.md`, which is the source of truth; where this document and `DECISIONS.md` disagree, `DECISIONS.md` wins.

Three kinds of statement appear below, and each is labelled:

- **Built** — the code does this today.
- **Accepted, not built** — agreed in `DECISIONS.md` (mostly D032–D043, dated 2026-11-10), but no code exists yet. None of D032–D043 is implemented.
- **Superseded / historical** — part of the old restaurant-first direction (version 0.1), kept only so readers can see what changed.

Anything not yet decided is listed in §17, "Open questions", which points to the list at the end of `DECISIONS.md`.

## 1. Product summary

Nosh suggests **one specific dish at one specific restaurant branch** (a branch is one physical location of a restaurant). It does this proactively, around the meal times the user has chosen. The aim is to help the person try dishes that are new to them and that they are likely to enjoy (D032).

The user can accept the suggestion (Go), ask for a different one (Another), or skip this meal (Not today). After the meal, Nosh asks what the user actually ate and whether they enjoyed it. A confirmed new dish adds to the user's journal and, when the dish comes from a country that is new to them, unlocks a cosmetic for their avatar (D039).

Nosh is not a search box or a list. It turns a recurring decision into one concrete suggestion and learns from what really happened.

**What changed from version 0.1 (superseded):** version 0.1 suggested one nearby restaurant the user had not visited, and counted confirmed, positively rated new restaurants. The unit is now a dish at a branch (D032), and the North Star counts confirmed personally-new dishes (D033).

## 2. What exists today

The code on `main` is a **restaurant-shaped prototype** from the old direction. It does not know what a dish is. In plain terms, today:

- **Sign-in and accounts.** Supabase email one-time-code sign-in works. Each user's data is kept separate. "Delete my data" removes the user's product data, but not their sign-in identity.
- **Meal schedule.** A short survey sets the meal schedule (weekday lunch by default, dinner optional), a 1–4 price ceiling per meal, and optional Home and Work spots. The price ceiling is stored but not used anywhere.
- **Suggestions.** The app asks the server for one suggestion per meal window. The server picks from **20 fictional San Francisco restaurants** (test data), within a fixed 1,600 m radius, using the old restaurant policy (`policy_v0`). The app always uses one hard-coded San Francisco point as the user's location; it never asks for the phone's location and never uses the saved Home/Work spots.
- **The card.** It shows a restaurant: name, cuisine, distance, address. Actions are Go, Another, Not today, and Been here already. Go opens Apple Maps with a name-and-address search. Go and Not today both end the session.
- **Exclusions.** Any restaurant marked visited or not interested is never suggested again.
- **Confirmation.** The user can confirm a restaurant visit with a positive or negative rating, and correct it later. A correction overwrites the old value; no history is kept. "No, I didn't go" and "Remind me later" are only on the phone; nothing is sent to the server.
- **Progress.** A screen counts confirmed, positively rated new restaurants (the old North Star, D002).
- **Notifications.** Not built. Two empty database tables exist; nothing sends anything.
- **Not built at all:** the dish catalog, menus, restaurant branches, dish offerings, dish ranking, the meal area, rewards, the avatar, the journal, and any outside data provider.

The restaurant prototype is useful as a working base (accounts, schedule, sessions, idempotent writes), but every user-facing feature in §8 must be rebuilt around dishes. For the code's exact shape, see `ARCHITECTURE.md`; for how to check that it works, run the checks in `README.md`.

## 3. Problem

People often eat the same few dishes even when they want variety, because:

- finding something new takes searching at the moment they are already hungry;
- restaurant lists say where to go, not what to order, so the person still falls back on a familiar dish;
- menus are long and hard to compare;
- nothing remembers which dishes the person has actually tried;
- accepting a suggestion does not prove the person ate it.

Nosh must solve two problems: choosing a good dish to suggest, and finding out what the person really ate. A suggestion is not a success until the user confirms what they ate.

## 4. Product vision

Nosh should become a trusted meal-time habit: one small, well-timed suggestion of a worthwhile dish the user has not tried, at a place they can reach.

Over time, the journal and avatar make exploration visible and rewarding. Later extensions may include Nosh Meals and social features (§16); they are not part of this phase.

## 5. Product principles

1. **One concrete choice beats a directory.** Lead with one dish at one branch, not a list.
2. **Ground truth beats intent.** Go is intent, not a meal. Only a confirmed meal counts.
3. **Exploration must still produce worthwhile meals.** The goal is a new dish the user is glad they tried, not novelty alone. Enjoyment rate is the guardrail (D033).
4. **Menu evidence does not establish quality.** A menu shows that a dish is offered, not that it is good (D034). What quality signal the policy uses is undecided (§17).
5. **The meal-time path is deterministic.** Ranking at meal time makes no LLM call. LLMs may be used offline, to build the catalog and map menus, with their own evaluation sets (D006, D041).
6. **Explicit constraints are never overridden.** The policy never suggests something that breaks a constraint the user stated (DECISIONS.md open question 10).
7. **Interruptions must earn their place.** The user controls meal times and notifications.
8. **Privacy first.** No background location, geofencing, or continuous tracking. Location is a user-confirmed coarse meal area, checked with foreground location when the app is opened (D010, D017, D035). No calendar access.
9. **Keep data classes apart.** Nosh's shared catalog, content from outside sources, and personal data are stored separately; content from one source can be removed on its own (D034).

**Superseded from 0.1:** "Lead with a concrete restaurant" (now a dish at a branch); "Every recommendation must be reconstructable from stored provider IDs, with provider content fetched live" (the D022 supply model is superseded by D034; only the rule "do not store Google content other than place IDs" is kept).

## 6. Target users

### Primary user

The founder, dogfooding at weekday lunch. They want to try more new dishes, accept a scheduled meal-time suggestion, and will say what they actually ate.

### Secondary users

A small private TestFlight cohort of friends (D009). The first hand-verified data covers Downtown San Mateo (D042), so early testers need to eat there.

Not designed for: restaurants, delivery couriers, large groups, trip planners, or a public marketplace.

## 7. Jobs to be done

- **When I need to choose a meal,** suggest one specific dish nearby that I am likely to enjoy, so I do not have to search or read a menu.
- **When the suggestion is wrong,** let me get another one straight away.
- **When I do not want a suggestion,** let me skip without it being read as dislike of the food.
- **When I eat something new,** remember it and show me what I have discovered.
- **When I eat something other than what was suggested,** let me say so easily.
- **When I want control,** let me change my meal times, price ceiling, constraints, meal area, and notifications.

## 8. The target journey

This is the first complete loop to build (none of it is built in dish form):

1. The user signs in with an email code. *(Built.)*
2. Onboarding sets the meal schedule, price ceiling, explicit constraints, and dish preferences.
3. For each meal, the user confirms a coarse meal area (D035).
4. Before the meal, Nosh prepares one dish-at-a-branch suggestion from the published offering index (§10.3).
5. A notification names the dish when a meal area exists; otherwise it is a generic nudge (D035).
6. The app opens, rechecks the meal area with foreground location, and shows the dish card.
7. The user taps Go, Another, or Not today. Go is final for that meal (D037).
8. After the meal, Nosh asks what the user actually ate and whether they enjoyed it (D038).
9. If the dish is new to the user, they get an immediate discovery moment and journal entry; a dish from a country new to them also unlocks an avatar cosmetic (D039).
10. The user's taste profile updates from the confirmed meal.

## 9. Scope areas and requirements

Each area starts with its implementation status.

### 9.1 Account and private access

> **Status:** Built (email-code sign-in, per-user data, product-data deletion). Deleting the sign-in identity is not built (open question 18).

- Passwordless email sign-in (Supabase).
- Every preference, suggestion, response, meal, and reward belongs to one user.
- Sign-out and account deletion. Deletion covers new personal data too (meal area, dish experiences, rewards).
- Private TestFlight distribution (D009).

### 9.2 Onboarding and preferences

> **Status:** Partly built in restaurant form — the meal schedule and price-ceiling survey exist. Dish preferences and explicit constraints are not started.

- Set the meal schedule: weekday lunch by default, dinner optional, active days, local time window, IANA time zone (an internationally standard time-zone name such as `America/Los_Angeles`). Windows end after they start on the same day; no overnight windows (D016, D020).
- Set a per-meal price ceiling (D026). How it applies to dish offerings is open (§17).
- Collect explicit constraints. Which ones, and their wording, are open (§17). Once given, the policy never overrides them.
- Learn initial dish preferences so the first suggestions are sensible. How onboarding asks about dishes is not decided (open question 20).

### 9.3 Dish catalog

> **Status:** Not started.

The dish catalog is Nosh's own shared list of dishes (D040).

- Three levels: **dish**, **variant**, **alias**. A variant eats differently (a regional style, a different main protein, a different preparation). An alias is just another name. Only dishes and variants have IDs. Variants are one level deep.
- IDs are permanent. A merge leaves a redirect; a split never moves a user's past meals.
- Every catalog fact is marked as generated, reviewed, or source-backed. The catalog is versioned.
- How one restaurant prepares a dish belongs to that restaurant's offering, not the catalog.
- A menu item that names only the dish is recorded at dish level, not guessed into a variant.
- Target size about 10,000 dishes, built deliberately with the founder hands-on. LLMs may help offline, with an evaluation set (D041).
- Cuisine comes from the catalog.
- Each dish's home country for rewards: **Proposed, awaiting confirmation** (D039). Catalog work must not depend on it until confirmed.

### 9.4 Restaurant and menu acquisition; the published offering index

> **Status:** Not started. No source is selected. Today's code reads 20 fictional fixture restaurants only.

An **offering** is one dish (or variant) that one branch serves. The **published offering index** is Nosh's stored list of reviewed offerings (D034).

- The index is built offline, in this order: sources → adapters → branch match → source-backed menu items → mapping to the dish catalog → review → published offering.
- Meal-time ranking reads only published offerings.
- Live place status and opening hours can make an offering ineligible right now. They never prove that a restaurant serves a dish. Which provider supplies them is open (§17).
- Content from outside sources is tagged with its source, retrieval date, and expiry, and each source's content can be purged on its own.
- Google content other than place IDs is not stored (kept from D022).
- Whether a source's content may be stored, processed, and displayed is measured by the source experiment (§12), never assumed.

### 9.5 Recommendation

> **Status:** Not started in dish form. Today the server ranks fictional restaurants with `policy_v0`; `policy_v1` (D024) was never built and is superseded.

- Suggest one dish at one branch, chosen from published offerings that are eligible now.
- Never break an explicit constraint.
- A restaurant the user has been to does **not** exclude its dishes; "Been here" is only a familiarity signal (D036). Today's code does the opposite.
- Ranking is deterministic, versioned, and makes no LLM call (D006, D041).
- Save what was proposed, its rank, and the policy version so a suggestion can be explained later.
- Return a clear "nothing available" state instead of repeating an invalid option. What the user sees then, and whether any rule may be relaxed, is open (question 23).
- The balance between familiar and exploratory dishes, the quality signal, and the meaning of each response for the policy are open (§17). `RECOMMENDATIONS.md` describes the policy.

### 9.6 Scheduled delivery and the meal area

> **Status:** Not started. Today there is no notification sender, and the app uses a hard-coded San Francisco point instead of any real location.

The **meal area** is roughly where the user will be for a given meal, confirmed by the user and stored as a coarse cell (an area, never an exact point) (D035).

- The user confirms a meal area for each meal.
- When the app opens, foreground location (only while the app is in use) rechecks the area.
- With a meal area, a notification may name the dish. Without one, it is a generic nudge.
- Respect the configured days, window, time zone, and on/off setting. Never send more than one initial notification per user and meal window.
- The app works without notifications.
- No background location, geofencing, or continuous tracking (D010).
- Cell size, how the area is confirmed and changed, how long it is kept, whether Home/Work spots remain, and notification timing and content are open (§17).

**Superseded:** D023's "notifications never name a restaurant" (now: a dish may be named when a meal area exists). D021's Google map and Google Maps handoff were superseded before being built; which map the card shows and which maps app Go opens is open (§17). Today Go opens Apple Maps.

### 9.7 Suggestion sessions and actions

> **Status:** Partly built in restaurant form — one session per user and meal window, Go / Another / Not today / Been here already, idempotent responses. System supersession and the stale-offering notice are not started.

- One suggestion session per user and meal window (D037).
- **Go** records intent and hands off to a maps app. Go is final for that window; there is no "change my pick".
- **Another** shows the next suggestion in the same session.
- **Not today** ends the session for that meal. It is timing feedback, not dislike of the food.
- The system may replace an unanswered proposal (for example the location changed or the offering went stale). This is recorded separately from user responses, with a reason.
- An accepted proposal is never replaced silently. If it goes stale, the user sees a notice.
- Every write is idempotent: a retry never creates a duplicate.
- What Another, Not today, and "Been here" teach the dish policy is open (§17). D011's conservative reading of Another was written for restaurants.

### 9.8 Actual-meal confirmation and corrections

> **Status:** Not started in dish form. Today the user confirms a restaurant visit with a rating; corrections overwrite it; "No" and "Remind me later" are not sent to the server.

A **dish experience** is the record that the user ate a particular dish at a particular branch (D038).

- After the meal, ask what the user actually ate and whether they enjoyed it. "Tried" and "enjoyed" are recorded separately (D033).
- If the user ate something other than the suggestion, they say so here. How they pick the dish, and what happens when it is not in the catalog, are open (§17).
- Confirming is one operation: it saves the dish experience, checks whether the dish is new to the user, and adds any rewards, all together. A retry cannot create a second reward.
- Corrections are added as new records; nothing is overwritten.
- Changing whether a dish was enjoyed never changes whether it was new, or any reward.
- Changing which dish was eaten re-checks both the old and the new dish.
- Retracting an experience invalidates its reward.
- The taste profile is derived from dish experiences.

### 9.9 Rewards, avatar, and journal

> **Status:** Not started.

- A dish new to the user gets a journal entry and an immediate discovery moment. A new variant does too (D039). Whether a new variant also counts toward the North Star is open (question 22).
- An avatar cosmetic unlocks only for a dish from a country new to the user.
- The avatar is always computed from currently valid rewards, so a retraction removes the cosmetic.
- **Proposed, awaiting confirmation:** each dish has exactly one home country for unlocks, plus optional secondary associations that never unlock anything.
- What the avatar, its cosmetics, and a journal entry look like is open (§17).

### 9.10 Legacy restaurant data

> **Status:** Not started. Today the restaurant data is live, not frozen.

- Restaurant visits and place states recorded before the pivot become read-only history (D036).
- They are not converted into dish experiences and earn no rewards after the fact.
- "Been here" keeps its meaning (the user had been to the restaurant before Nosh) and becomes a familiarity signal only.
- What the app shows for this history, and when the old write endpoints are retired, are open (§17).

## 10. Core events to record

The server must record these as distinct events:

- meal schedule, constraints, or meal area created or changed;
- suggestion session created;
- dish offering proposed;
- proposal replaced by the system (with a reason), separate from any user response;
- notification sent, when known;
- Go, Another, Not today selected;
- maps handoff attempted;
- confirmation requested;
- dish experience confirmed, corrected, or retracted;
- reward granted or invalidated;
- notifications turned off.

Go, a maps handoff, and a confirmed meal are different things and must never be merged.

**Status:** today's code records restaurant proposals, responses, and visits only.

## 11. Success metrics

### North Star (D033, accepted, not built)

**Confirmed personally-new dishes tried per active user.**

A dish counts when the user confirmed eating it and had not had it before. Enjoyment is not part of the count; it is a guardrail. The period that defines "active" and any target values are open (§17, question 14), as is whether a new variant of a dish already tried counts (question 22).

**Historical (superseded, D002):** "confirmed positively rated new restaurants per monthly active user". Today's progress screen still shows this.

### Funnel

- eligible meal windows;
- notifications sent and opened;
- sessions viewed;
- Go, Another, and Not today rates;
- accepted suggestions with a completed confirmation;
- confirmed dish experiences;
- confirmed personally-new dishes.

### Guardrails

Enjoyment rate is the guardrail D033 names. The rest of this list is proposed for measurement and is not a recorded decision.

- enjoyment rate of confirmed new dishes (a falling rate means exploration is producing poor meals);
- Another per engaged session;
- notification turn-off rate;
- suggestions that break a constraint or were invalid (target: zero);
- confirmation completion rate;
- sessions with nothing to suggest;
- accepted offerings that turned out stale;
- API and notification failures.

### Validation targets

**Targets are not yet set (open question 14 in `DECISIONS.md`).**

**Historical (version 0.1, restaurant-based, no longer apply):** at least five testers complete onboarding; a median of two confirmed positive new restaurants per active tester in four weeks; at least 60% of Go actions confirmed; fewer than 20% of testers turn off notifications in four weeks; zero suggestions of a visited or not-interested place.

## 12. San Mateo pilot and source experiment

> **Status:** Accepted (D042), not started. No source is selected.

- **Downtown San Mateo** is the first hand-verified offering index.
- Neighborhoods in San Francisco, San Jose, and New York City are comparison samples only.
- A source-comparison experiment runs about 40 restaurants (10 per area) through each vendor trial and through crawling restaurants' own websites.
- It measures: correct branch, menu presence, item detail, freshness, mapping accuracy, review minutes, cost per usable offering, and license rights to store, process, and display.
- Pass/fail thresholds are set before any results are looked at.
- Datafiniti, MealMe, and RelevantData are candidates, not selected. Nothing about their coverage, prices, or licenses is assumed.
- Until the experiment reports, the only supply is the hand-verified San Mateo index.

## 13. Budget

> **Status:** Open (D043).

D028's target of about $50/month is superseded. The new figure is decided after the source experiment. For planning only: about $50–75/month on hand-verified data, more if a paid feed is used. This is not a quote; no vendor price was confirmed.

## 14. Edge cases

### Supply and eligibility

- No published offerings in the meal area, or none eligible now.
- An offering's menu evidence has expired, or the branch closed, moved, or changed its menu.
- Live status says closed while the menu says the dish exists (live status wins for eligibility; it never proves the dish exists).
- One restaurant appears under several source records, or a menu item maps ambiguously.
- A menu item names only the dish, not a variant (record at dish level).

Expected: explain the shortage, never reuse an invalid option silently, and replace only unanswered proposals.

### Time and notifications

- The phone changes time zone; daylight-saving time skips or repeats an hour.
- Lunch and dinner windows are close together.
- The meal schedule or meal area changes after a suggestion was prepared.
- A notification is opened after the meal window, delivered twice, or permission is denied or revoked.

Expected: use the schedule's IANA time zone, deduplicate by user and meal window, and keep the app usable without notifications.

### Responses and confirmation

- The user taps Another until nothing is left.
- The user taps Go, then eats elsewhere or eats a different dish.
- The user eats a dish without any suggestion.
- The user confirms the wrong dish, changes enjoyment, or retracts.
- Two devices respond to the same suggestion; a retry arrives after a newer response.

Expected: keep the full event history, make writes idempotent, append corrections, and recompute novelty and rewards from the facts.

### Connectivity

- The device is offline when a notification is opened.
- The server saves a response but times out before replying.
- The maps app cannot find the place.
- App and server versions differ.

Expected: keep session and proposal IDs on the device, queue writes with idempotency keys, and reject unsupported app versions gracefully. (Today the app does not queue writes.)

### Privacy and account state

- The user deletes their account while scheduled work is pending.
- Precise coordinates appear in logs.
- Test and real data mix.

Expected: never log precise coordinates, tokens, or email addresses; store only the coarse meal area; cancel pending work on deletion; keep test and production separate.

## 15. Non-goals for this phase

Do not build:

- delivery, pickup, payment, reservations, or order placement;
- integrations with Grubhub, DoorDash, Uber Eats, or restaurant POS systems;
- automatic meal or visit detection, background location, geofencing, or continuous tracking;
- calendar access or meeting-aware timing;
- public App Store launch or Android launch;
- social feeds, following, shared lists, group voting, or partner profiles;
- restaurant accounts, promoted listings, advertising, or monetization;
- spending tracking or budgeting;
- an LLM call in the meal-time path; LLM-written explanations on the card;
- free-text craving search with RAG (retrieval-augmented generation), menu embeddings, or review summarization;
- a conversational concierge, MCP server, LangGraph workflow, or autonomous agent;
- photo uploads, review hosting, or public user-generated content;
- nationwide ingestion before the San Mateo pilot and source experiment;
- real-time opening-hours guarantees or allergen guarantees;
- microservices, Kafka, Redis, Celery, a graph database, a vector database or vector service, pgvector (D013), or an event platform (D041);
- automatic experimentation or a feature-flag platform;
- Nosh Meals and social features (future extension points only; §16).

**Moved into scope (no longer non-goals):** menu ingestion and offline processing (D034), and offline LLM use for catalog generation and menu mapping, each with an evaluation set (D041).

## 16. Future extension points

Mentioned only so that today's design does not block them. No tables, services, or infrastructure are built for them now (D032).

- **Nosh Meals** — a possible later product extension.
- **Social features** — for example sharing discoveries with friends.

## 17. Open questions

These are not decided. The full, canonical list is "Open questions" at the end of `DECISIONS.md`; numbers below refer to it.

1. One home country per dish, and how it is chosen for contested origins (Q1, D039).
2. The monthly budget (Q2, D043).
3. Which sources, the experiment's pass/fail thresholds, and each source's rights (Q3, D042).
4. Who supplies live place status and hours, and what their terms require of the card (Q4).
5. Which map the card shows and which maps app Go opens (Q5).
6. Policy balance between familiar and exploratory dishes (Q6).
7. What restaurant quality signal, if any, the policy uses (Q7).
8. How the price ceiling applies to dish offerings (Q8).
9. What Another, Not today, and "Been here" teach the dish policy (Q9).
10. Which explicit constraints onboarding collects and their wording (Q10).
11. Meal-area cell size, confirmation, retention, and the fate of Home/Work spots (Q11).
12. Notification timing, content, and actions (Q12).
13. How the user reports "I ate something else", including dishes not in the catalog (Q13).
14. What "active user" means, and any target values (Q14).
15. What the app shows for frozen restaurant history; when old endpoints are retired (Q15).
16. What the avatar, cosmetics, and journal entries are (Q16).
17. Catalog review process, evaluation sets and pass marks, version numbering (Q17).
18. Deleting the sign-in identity (Q18).
19. Where unfinished tester-readiness work and the Fly.io deployment fall in the new milestone order (Q19).
20. What onboarding asks about dishes, and how the answers shape a new user's first suggestions (Q20).
21. Whether the same dish or branch may be suggested again in a session or in back-to-back meal windows (Q21).
22. Whether a new variant of a dish already tried counts as a personally-new dish (Q22).
23. What the user sees when nothing is eligible, and whether any rule may be relaxed (Q23).
24. Planned schema details: variants, system-superseded proposals, correction events, and the existing proposal columns (Q24).
25. What happens to a published offering when the content behind it expires or is purged (Q25).

## 18. Exit criteria for this phase

These criteria are proposed, not a recorded decision. They extend the "Definition of MVP done" in `IMPLEMENTATION_HANDOFF.md`, which covers the first complete loop. Proposed: this phase is complete when:

- the first complete loop works for the private cohort in Downtown San Mateo: dish onboarding → dish-and-branch suggestion → scheduled delivery → actual-dish confirmation → immediate discovery reward → updated profile with a minimal avatar and journal;
- all core events in §10 are recorded and auditable;
- the rules "never break a constraint", "never silently replace an accepted proposal", and "a retry never creates a second reward" are covered by automated tests;
- the North Star and guardrails can be calculated;
- the source experiment has reported, so supply and budget can be decided.

## 19. Naming decision

The product name is **Nosh** (D001). It is short, food-native, works as an action, and conveys the desired approachable cue.

Rejected candidates were Forage, Tuck, Crumb, Morsel, Savor, and Bite. The name has not yet been checked for trademarks, domains, App Store conflicts, or social handles. That check is required before public launch or investment in brand assets.
