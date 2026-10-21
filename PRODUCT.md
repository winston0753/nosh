# Nosh Product Requirements

- **Status:** Phase-one baseline
- **Version:** 0.1
- **Last updated:** 2026-10-20
- **Product name:** Nosh

## 1. Product summary

Nosh is a proactive restaurant-discovery app that helps a person try more good restaurants wherever they are at meal time. Around their meal window, it presents one nearby restaurant the person has not tried, supports a low-friction request for another option, hands accepted suggestions to Maps, and later asks whether the visit happened and was good.

The product is intentionally different from restaurant search products that begin with a blank search box or a long list. Nosh reduces a recurring decision to one timely recommendation and learns from the outcome.

## 2. Problem

People often default to familiar restaurants even when they want more variety because:

- discovery products require active searching at the moment the person is already hungry;
- long lists create comparison work rather than resolve the decision;
- saved places are disconnected from meal timing and location;
- recommendations often lack personal visit history;
- accepting a suggestion does not prove that the person actually visited.

Nosh must solve both the recommendation problem and the ground-truth problem. A suggestion is not a successful outcome until the user confirms that the visit occurred and reports whether it was good.

## 3. Product vision

Nosh should become a trusted meal-time habit: a small, context-aware prompt that reliably surfaces a worthwhile place the user has not tried.

The long-term product may support free-text cravings, natural-language meal logging, group preferences, calendar-aware timing, and a conversational concierge. Phase one is designed to determine whether the core suggestion-and-confirmation loop is valuable before those capabilities are built.

## 4. Product principles

1. **One useful choice beats a ranked directory.** Lead with a concrete restaurant.
2. **Ground truth beats inferred intent.** Confirm visits rather than treating a tap as a visit.
3. **Novelty must not sacrifice quality.** The objective is a new restaurant the user liked, not novelty alone.
4. **Interruptions must earn their place.** Notification frequency and timing are user-controlled.
5. **The meal-time path is deterministic.** It must not depend on an LLM response.
6. **Every recommendation must be reconstructable from what we may store.** Store place identifiers, ranks, Nosh-owned score components, and the policy version; provider content is fetched live and not stored (D022).
7. **Privacy grows with demonstrated value.** Do not request background location or calendar access in phase one.

## 5. Target users

### Primary user

The founder, dogfooding the product at weekday lunch wherever they happen to be.

Characteristics:

- wants to try more local restaurants;
- repeatedly decides where to eat near home or work;
- is willing to mark places they have already been when Nosh suggests them;
- accepts a scheduled meal-time prompt;
- will confirm whether an accepted suggestion became a real visit.

### Secondary users

A small private TestFlight cohort of friends with similar restaurant-discovery behavior.

Phase one is not designed for restaurants, delivery couriers, large social groups, tourists planning full trips, or a broad public marketplace.

## 6. Jobs to be done

- **When I need to choose a meal,** suggest one nearby place I am likely to enjoy so that I do not have to search.
- **When the suggestion is wrong,** let me get another option immediately without restarting the flow.
- **When I visit somewhere new,** remember it and show my neighborhood progress.
- **When I do not want a suggestion,** let me decline without incorrectly changing my food preferences.
- **When I want control,** let me change my meal windows, price ceiling, fallback spots, or notification setting.

## 7. Phase-one user journey

1. The user creates an account using passwordless email authentication.
2. A short survey sets the meal schedule (weekday lunch by default; dinner optional), a typical per-meal price ceiling, and optional Home and Work fallback spots (D020, D026).
3. At meal time, a notification nudges the user; it names no restaurant (D023).
4. When the user opens the app, it uses the device's current foreground location (or a fallback spot) and creates a suggestion from live place data (D021).
5. The app displays one restaurant with cuisine, distance, a Google map, and a short factual reason.
6. The user chooses Go, Another, or Not today, or marks the place Been here already (D025).
7. Go opens the restaurant in Google Maps.
8. After the meal window, the app asks whether the visit occurred.
9. A confirmed visit receives a simple positive or negative rating.
10. The visit history and progress update only after confirmation.

## 8. MVP features and requirements

### F1. Account and private access

- Support passwordless email sign-in.
- Keep every preference, suggestion, response, and visit scoped to one user.
- Allow sign-out and account-data deletion.
- Private TestFlight distribution is sufficient for phase one.

### F2. Meal schedule and location (D020)

> Implementation status: the current code still uses dining contexts (a fixed map point, radius, and schedule per context). D020 replaces them.

- An onboarding survey sets the meal schedule: weekday lunch by default, dinner opt-in, active days, local window, and IANA time zone.
- The local time window must end after it starts on the same day; overnight windows are not supported in phase one (D016).
- Suggestions use the device's current foreground location, requested with when-in-use permission at the moment the app is opened (D017).
- Users may save optional Home and Work spots, used only when location permission is denied or a fix is unavailable.
- Do not collect continuous or background location.

### F3. Prior visit history (D025)

> Implementation status: the current code has a bulk onboarding classification step (D018). D025 replaces it.

- The suggestion card offers a secondary Been here already action.
- A place marked Been here already was visited before Nosh: it is excluded from future suggestions and never counts toward the North Star, even after a later Nosh visit (D018).
- Never count a restaurant as visited solely because it was suggested.

### F4. Place data (D021, D022)

> Implementation status: the current code reads a 20-place fictional fixture catalog. D021 replaces it with live Google Places data; the fixtures remain test data (D027).

- Candidates, ratings, hours, price level, and types come live from Google Places at suggestion time.
- Store only the provider place identifier and Nosh-owned data; never store provider names, addresses, ratings, hours, or types.
- Tolerate missing rating, hours, price, and photos; a missing value is neutral, never a positive claim.

### F5. Suggestion generation

- Generate exactly one current suggestion per user and meal window.
- Exclude visited, not-interested, closed, out-of-range, over-budget, and already rejected-in-session places.
- Save the ranked place identifiers, chosen place, Nosh-owned score components, and ranking-policy version (D022).
- Return an explicit no-candidate state instead of repeating an invalid option.
- Complete without an LLM call.

### F6. Suggestion card

- Show restaurant name, primary cuisine, approximate distance, address, a factual reason, and the place on a Google map with Google attribution (D021).
- Show only data the product is allowed to store and display.
- Display Go, Another, and Not today as the primary actions.
- Avoid presenting an unsupported claim such as “best” or “perfect for you.”

### F7. Notifications

- Respect the configured days, local meal window, time zone, and enabled state.
- The meal-time notification is a nudge that names no restaurant; the suggestion is created when the user opens the app (D023).
- Never send more than one initial notification for the same user and meal window.

### F8. Response handling

- Go records intent and opens Google Maps (D021).
- Another returns the next eligible proposal in the same session.
- Not today closes the session and is treated as timing feedback, not cuisine rejection.
- Every write is idempotent so retries cannot create duplicate responses.
- Phase one treats Another as ambiguous, weak feedback; it must not create a strong cuisine dislike.
- Been here already marks the place visited before Nosh, excludes it, and returns the next proposal; it is not recorded as Another (D025).

### F9. Visit confirmation

- Ask whether an accepted suggestion resulted in a visit.
- Support Yes, No, and Remind me later.
- If Yes, collect a simple positive or negative rating.
- Allow correction of an accidental confirmation.
- Only a confirmed visit updates visited status and the primary outcome metric.

### F10. History and progress

- List confirmed visits in reverse chronological order.
- Show confirmed new restaurants by month.
- Show simple cuisine or neighborhood completion only where the denominator is reliable.
- Do not turn completion percentage into the ranking rule.

### F11. Preferences and controls

- Enable or disable lunch, dinner, and all notifications.
- Change meal windows, days, price ceiling, and Home and Work spots.
- View and edit Been and Not interested place states.
- Provide account deletion and a plain-language summary of stored data.

## 9. Core data events

The client and server must record these distinct events:

- meal schedule created or changed;
- suggestion session created;
- place proposed;
- notification delivered when known;
- suggestion viewed;
- Go selected;
- Another selected;
- Not today selected;
- Maps handoff attempted;
- visit confirmation requested;
- visit confirmed or denied;
- visit rating recorded or corrected;
- notifications disabled.

An acceptance, a Maps handoff, and a confirmed visit are different states and must never be conflated.

## 10. Success metrics

### North Star

**Confirmed positively rated new restaurants per monthly active user.**

A qualifying outcome requires:

- the restaurant was previously unvisited;
- the user confirmed the visit;
- the user rated the result positively.

### Funnel metrics

- eligible meal windows;
- notifications sent and opened;
- suggestion sessions viewed;
- Go, Another, and Not today rates;
- accepted suggestions with a completed confirmation;
- confirmed visits;
- confirmed positive new visits.

### Guardrails

- Another actions per engaged session;
- notification disable or mute rate;
- duplicate or invalid recommendation rate;
- confirmation prompt completion rate;
- negative rating rate;
- sessions with no eligible candidate;
- API and notification failures.

### Initial validation targets

These are phase-one hypotheses, not established benchmarks:

- at least five testers complete onboarding;
- a median of at least two confirmed positive new restaurants per active tester in a four-week period;
- at least 60% of Go actions receive a completed visit confirmation;
- fewer than 20% of testers disable notifications during the first four weeks;
- zero recommendations of a place already confirmed as visited or marked Not interested.

## 11. Edge cases

### Candidate availability

- No restaurants exist within the selected radius.
- Every nearby restaurant is visited, rejected in the current session, inactive, or Not interested.
- A cuisine contains only one or two restaurants, making completion percentages unstable.
- The same restaurant has duplicate provider records or multiple cuisine labels.
- A place closes, moves, changes its name, or is temporarily unavailable.
- A restaurant lies exactly on the radius boundary.

Expected behavior: explain the shortage, offer a fallback spot when location is unavailable, and never silently reuse an invalid candidate.

### Time and notifications

- The phone changes time zone.
- Daylight-saving time creates a missing or repeated local hour.
- Lunch and dinner windows are configured close together.
- A suggestion was generated before the user changed a meal window or radius.
- The notification is opened after the meal window.
- Notification permission is denied, provisional, or later revoked.
- A notification is delivered twice or an action is replayed.
- The user disables dinner but not lunch.

Expected behavior: use the context's IANA time zone, version scheduled work, deduplicate by context and meal window, and keep the in-app experience functional without notifications.

### User responses

- The user taps Another repeatedly until candidates are exhausted.
- Another means “wrong restaurant,” “wrong cuisine,” “too far,” or simply curiosity.
- The user taps Go and then does not visit.
- The user visits without tapping Go.
- The user confirms the wrong restaurant or changes a rating.
- Two devices respond to the same suggestion.
- A retry arrives after a newer response.

Expected behavior: preserve the event history, make writes idempotent, allow correction, and avoid treating ambiguous actions as strong preference labels.

### Connectivity and external handoff

- The device is offline when a notification is opened.
- The API times out after recording a response but before returning it.
- Google Maps is unavailable or the place no longer resolves.
- The app is terminated when a notification action occurs.
- The mobile app and API schema versions differ.

Expected behavior: keep the current session and proposal identifiers, queue response writes, use idempotency keys, explain that card details need a connection (provider content may not be cached, D022), and reject unsupported client versions gracefully.

### Privacy and account state

- A user deletes a fallback spot or changes their meal schedule after visits exist.
- A user deletes their account while scheduled jobs are pending.
- An email link is opened on a different device.
- Precise home or work coordinates appear in logs or analytics.
- Test data and real user data coexist.

Expected behavior: minimize stored precision where possible, redact coordinates from logs, cancel pending work on deletion, and keep test and production environments separate.

## 12. Explicit phase-one non-goals

Do not build the following in phase one:

- delivery, pickup, payment, reservation, or order placement;
- direct integrations with Grubhub, DoorDash, Uber Eats, or restaurant POS systems;
- automatic visit detection, background location, geofencing, or continuous tracking;
- calendar access or automatic meeting-aware timing;
- public App Store launch or Android launch requirements;
- social feeds, following, shared lists, group voting, or partner profiles;
- restaurant accounts, promoted listings, advertising, or monetization;
- monthly spend tracking or budgeting;
- free-text craving RAG, menu embeddings, review summarization, or LLM explanations;
- a conversational concierge, MCP server, LangGraph workflow, or autonomous agent;
- photo uploads, menu ingestion, review hosting, or user-generated public content;
- nationwide place ingestion or perfect place-provider entity matching;
- real-time opening-hours guarantees;
- advanced dietary-allergen guarantees;
- microservices, Kafka, Redis, Celery, or a separate vector database;
- automatic experimentation or a complex feature-flag platform;
- optimization for completion percentage alone.

## 13. MVP exit criteria

Phase one is complete when:

- the complete onboarding-to-confirmed-visit loop works for the private TestFlight cohort;
- all core events are captured and auditable;
- invalid recommendation invariants are covered by automated tests;
- the product can run for four weeks without manual database repair;
- the initial success and guardrail metrics can be calculated;
- user feedback is sufficient to decide whether to expand place data, improve notification timing, or add language-based discovery.

## 14. Naming decision

The product name is **Nosh**. It is short, food-native, works as an action, and conveys the desired approachable consumption cue.

Rejected candidates were Forage, Tuck, Crumb, Morsel, Savor, and Bite. The name Nosh has not yet been checked for trademarks, domains, App Store conflicts, or social handles. That validation is required before public launch or investment in brand assets.
