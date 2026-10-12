# Nosh Recommendation System

- **Status:** Phase-one baseline
- **Version:** `policy_v0`
- **Last updated:** 2026-10-12

## 1. Objective

The recommendation system should increase **confirmed positively rated new restaurant visits** while minimizing repeated rejection and notification fatigue.

It must not optimize raw novelty, completion percentage, clicks, or Maps handoffs in isolation.

## 2. Design principles

- Apply eligibility rules before scoring.
- Keep meal-time decisions deterministic and reproducible.
- Separate cuisine preference from restaurant quality.
- Learn from explicit outcomes more strongly than ambiguous actions.
- Preserve exploration so the system can improve.
- Store enough evidence to replay every decision.
- Prefer a simple policy with good instrumentation over an opaque model.

## 3. Terminology

- **Context:** A user-defined location, radius, meal type, schedule, and time zone.
- **Session:** One decision opportunity for a context and meal window.
- **Candidate:** An eligible unvisited restaurant considered in a session.
- **Proposal:** The one restaurant shown at a specific sequence number.
- **Response:** Go, Another, or Not today.
- **Outcome:** Confirmed visit plus positive or negative rating.
- **Policy version:** Immutable identifier for filtering, priors, weights, and tie-breaking behavior.

## 4. Eligibility filters

A place is eligible only when all applicable rules pass:

1. The place is active.
2. Its location is within the context radius.
3. It is not confirmed visited.
4. It is not marked Not interested.
5. It has not already been proposed in the current session.
6. It has at least one normalized cuisine.
7. It satisfies any explicit supported constraint.

Opening hours, delivery availability, detailed dietary safety, and live capacity are not trusted phase-one filters unless the curated dataset explicitly supports them.

If no candidate is eligible, return `no_candidates` with reason codes. Do not relax privacy or user-exclusion rules automatically.

## 5. Phase-one policy

The policy has two levels:

1. select a cuisine worth exploring;
2. select the strongest eligible restaurant within that cuisine.

### 5.1 Cuisine score

For cuisine `c`:

```text
cuisine_score(c) = sampled_acceptance(c) × pool_value(unvisited_count(c))

pool_value(n) = 1 - exp(-n / 2)
```

`sampled_acceptance(c)` is drawn from a Beta posterior:

```text
theta_c ~ Beta(alpha_c, beta_c)
```

Initial phase-one prior:

```text
alpha_c = 1 + history_prior_strength × normalized_history_frequency(c)
beta_c  = 1 + history_prior_strength × (1 - normalized_history_frequency(c))
history_prior_strength = 4
```

If no onboarding history exists, use `Beta(1, 1)`.

The simulator supports this mechanism as preferable to lowest been-to percentage under its assumptions. The prior strength is still a hypothesis and must be versioned.

### 5.2 Restaurant score

Within the selected cuisine, compute:

```text
place_score =
    0.45 × quality_score
  + 0.30 × distance_score
  + 0.15 × context_fit
  + 0.10 × exploration_score
```

All components are normalized to `[0, 1]`.

- `quality_score`: curated score or Bayesian-adjusted source rating when licensed and available; use a neutral default when missing.
- `distance_score`: monotonic distance decay within the context radius.
- `context_fit`: supported match for meal type or explicit user constraint; otherwise neutral.
- `exploration_score`: deterministic tie-break preference for underexposed eligible places.

Do not claim the selected restaurant is objectively “best.” The UI may say why it was selected using stored reason codes such as `nearby`, `new_to_you`, `preferred_cuisine`, or `many_options_remaining`.

### 5.3 Tie-breaking

Tie-breaking must be stable for a given session seed and policy version. This allows decision replay while still varying exploration across sessions.

## 6. Feedback semantics

### Strong signals

- Confirmed positive visit: strong positive place outcome and positive cuisine evidence.
- Confirmed negative visit: negative place outcome; weak negative cuisine evidence.
- Explicit Not interested on a place: hard place exclusion.
- Manual Been state: visit history, not a quality signal.

### Ambiguous signals

- Go: intent only; do not treat as a visit or positive rating.
- Another: weak negative evidence for the proposed place. It may mean cuisine, distance, mood, or curiosity, so phase one does not apply a full cuisine rejection.
- Not today: timing signal only; never update cuisine or place preference.
- Notification dismissal: no preference update.

The current simulator models proposal rejection as cuisine feedback more strongly than the phase-one product should. This difference must remain explicit until real response data explains what Another means.

## 7. Updating preference state

Phase one should derive preference state from an append-only response and outcome history where practical. A materialized `cuisine_preference_state` may cache:

- cuisine ID;
- user ID;
- alpha and beta parameters;
- source event watermark;
- policy version that produced the state.

Recomputation from source events must be possible. Manual state edits require an audit event.

Suggested initial updates:

- confirmed positive visit: `alpha += 1.0`;
- confirmed negative visit: `beta += 0.25`;
- Another: no cuisine update in `policy_v0`;
- Not today or dismiss: no cuisine update.

These values are hypotheses. Any change creates a new policy version.

## 8. Cold start

### New user with onboarding history

- Use visited cuisine frequency as a weak taste prior.
- Exclude places marked Been or Not interested.
- Preserve exploration across cuisines with unvisited supply.

### New user without onboarding history

- Use uniform cuisine priors.
- Prefer cuisines with multiple eligible places rather than tiny categories.
- Use neutral place-quality defaults where data is missing.
- Ask for confirmation quickly so real outcomes replace priors.

### New place

- Use neutral quality and a small exploration component.
- Do not over-rank it solely because it has no history.

## 9. Diversity and repetition controls

- Never repeat a place within a suggestion session.
- Avoid proposing the same place in consecutive meal windows unless the user explicitly saved it for later.
- Track recent cuisine exposure and use it only as a bounded tie-breaker.
- Do not enforce diversity by suggesting a cuisine with poor acceptance evidence.
- Keep lunch and dinner contexts separate because location and intent differ.

## 10. Logged decision record

Every proposal stores:

- policy version;
- dining-context version;
- candidate place IDs;
- exclusion counts by reason;
- chosen cuisine and sampled acceptance value;
- unvisited pool size;
- each place score component;
- final score;
- deterministic session seed or replay token;
- reason codes shown to the user;
- creation timestamp.

Do not store unnecessary precise user coordinates in the candidate snapshot.

## 11. Offline evaluation

### Simulator

Retain the existing paired-user simulator to test mechanisms and regressions. It is not a forecast.

Report:

- confirmed or simulated new restaurants;
- positive outcome rate when modeled;
- proposals and Another actions per session;
- cuisine acceptance rate;
- no-candidate rate;
- mute/churn proxy;
- paired confidence intervals against the current production policy.

### Logged-session replay

Once real events exist:

- verify filter invariants against historical states;
- replay deterministic score components;
- compare candidate rankings without claiming causal lift;
- use counterfactual evaluation only after propensities are logged correctly.

### Human-labeled checks

Create a small review set containing expected eligible and ineligible places for representative contexts. Verify distance, visit state, exclusions, cuisine normalization, and factual reason codes.

## 12. Online evaluation

Phase one uses observation, not automated A/B testing.

Track by policy version:

- Go rate;
- Another actions per session;
- completed confirmation rate;
- confirmed positive new visits;
- negative visit rate;
- notification disable rate;
- no-candidate rate.

Do not promote a policy because it increases Go taps if it lowers confirmed positive outcomes or increases notification disabling.

## 13. Required invariants

Automated tests must prove:

- visited places are never eligible;
- Not interested places are never eligible;
- inactive and out-of-radius places are never eligible;
- a place is not repeated within a session;
- Not today does not change cuisine preference;
- duplicate response events do not update state twice;
- the same session and replay seed reproduce the same proposal;
- every proposal references an immutable policy version;
- exhausted candidate sets return `no_candidates` safely.

## 14. Future recommendation capabilities

These are outside phase one:

- contextual bandits using time, weather, companions, or calendar state;
- hybrid retrieval for free-text cravings;
- menu and review embeddings;
- learned place-quality models;
- group preference aggregation;
- causal online experimentation;
- LLM-written explanations;
- automatic dietary or allergen inference.

Each capability must define its ground truth, failure modes, and evaluation set before implementation.
