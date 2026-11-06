# Nosh repository review — refreshed after correctness hardening

## 1. What does the restaurant catalog actually support?

### Takeaway

Use the existing Nosh canonical place UUIDs and PostGIS model. A real provider needs a bounded import/review/refresh process; the current 20 places are fictional development fixtures, and the now-working importer only seeds them. Public ratings are optional under the product contract. Identity, active status, location, normalized cuisine, evidence-backed quality, and source rights are the immediate data requirements.

Snapshot refreshed **2026-10-19 20:40 PDT / 2026-10-20 03:40 UTC**, after reading the current Git diff, revised AGENTS.md, canonical documents, hardening implementation and new tests. This replaces the October 16 draft; fixed issues are explicitly identified below. All existing user changes were preserved. Only this research note was edited by this researcher.

### Cited Findings

- D008 selects a small reviewed neighborhood catalog before broad ingestion. Product F4 tolerates missing rating/hours/photo/menu information; F6 requires factual, permitted-to-display information. [D008](/Users/winstontang/Downloads/nosh/DECISIONS.md:140), [Product](/Users/winstontang/Downloads/nosh/PRODUCT.md:114).
- Fixtures explicitly say the restaurants are fictional and only make the loop runnable locally. They are not a real reviewed neighborhood directory. [Fixtures](/Users/winstontang/Downloads/nosh/services/api/app/places/fixtures.py:1).
- `Place` has a local UUID, canonical name, geography point, address, status, timestamps, JSON metadata and cuisine/source associations. It already has a geography GiST index. `PlaceSource` has unique `(provider, provider_place_id)`, optional source update timestamp and last-seen timestamp. [Model](/Users/winstontang/Downloads/nosh/services/api/app/places/models.py:23), [Crosswalk](/Users/winstontang/Downloads/nosh/services/api/app/places/models.py:47).
- No explicit release/schema version, field-level provenance, license/attribution/retention rights, field freshness, merge/split lineage, manual-review state, or correction precedence exists in that source model. Generic metadata is not an enforced data contract. [Source schema](/Users/winstontang/Downloads/nosh/services/api/app/places/models.py:47).
- **Importer packaging is fixed.** It now lives in `services/api/jobs`, imports `app`, uses `echo=False`, and is guarded by import tests. However it still just calls the fixture loader. The loader inserts only missing fixed UUIDs, never refreshes existing fields/cuisines/source timestamps or detects closures. [Importer](/Users/winstontang/Downloads/nosh/services/api/jobs/ingest_places/importer.py:24), [Loader](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:19), [Import tests](/Users/winstontang/Downloads/nosh/services/api/tests/test_job_imports.py:1).
- Eligibility drops every place without a normalized cuisine. Missing-cuisine exclusions are not reported. Primary selection uses the first primary association, else first cuisine; exactly one primary is not enforced by the association schema. This needs an explicit admission/mapping step for a provider taxonomy. [Candidate construction](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:208), [Association schema](/Users/winstontang/Downloads/nosh/services/api/app/places/models.py:79).
- Quality is an unvalidated metadata float with neutral default 0.5. No typed rating/count/date/evidence source exists; the engine gives it 45% of within-cuisine score. [Quality read](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:237), [Weights](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/engine.py:24).
- A curated quality score above 0.7 produces `highly_rated`, which mobile translates into “Highly rated,” even without a public rating. For nearby places it may be hidden because the card shows the first two reasons; for farther places the unsupported phrase is visible. [Reason code](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/engine.py:137), [Card](/Users/winstontang/Downloads/nosh/apps/mobile/src/components/SuggestionCard.tsx:10).
- Hours are explicitly outside trusted eligibility unless curated data supports them. There is no existing hours model. Apple Maps opens a name/address search; the suggestion response lacks restaurant coordinates or an exact map-entity identifier. These are acceptable prototype simplifications but need real-branch verification. [Policy](/Users/winstontang/Downloads/nosh/RECOMMENDATIONS.md:33), [Handoff](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/index.tsx:95), [Response](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/schemas.py:18).

### Inferences

- Smallest useful data pipeline: one neighborhood export → staging with provider/release/schema version → normalized category/cuisine mapping → deduplication and human review → canonical upsert. Keep provider IDs as crosswalks to Nosh IDs, preserving user history across provider churn. Never infer restaurant quality from existence confidence.
- Add import counts for input rows, inactive records, invalid geometry, duplicate candidates, missing/unknown cuisine, held-for-review and admitted records. This separates nominal coverage from recommendation-ready coverage.
- Add field source, checked-at, rights/attribution and override precedence for the few fields actually used. Keep quality source separate from quality value. Missing rating stays unknown; a curated score should yield a curated reason, not a public-review claim. Validate any numeric quality as finite and 0–1.
- A repeatable batch command and reviewed JSON/CSV are enough initially. No new service, large-scale ingestion platform, vector database or meal-time LLM is justified.
- Add review/reconciliation for missing IDs, closures, relocations and merges. Absence from one release should not automatically delete a canonical place or erase visit history.
- Any restrictive provider content must be considered in database storage, recommendation snapshots, offline mobile persistence and map presentation together. Provider researchers supply current external terms; this note makes no independent legal conclusion.

### Gaps

No real source import, restaurant accuracy/coverage audit, licensed payload, current-hours check or geospatial load benchmark was performed. Provider choice cannot be proven by the synthetic fixture. The source researchers separately verified Overture/Google schema and terms.

## 2. What should stay, what was fixed, and what remains worth improving?

### Takeaway

Retain Expo/strict TypeScript, FastAPI modular monolith, PostGIS, pure deterministic policy and transactional intent/visit semantics. The hardening pass materially improved correctness. Remaining work should focus on five bounded areas: real source contract; ranking evidence/replay; shared auth and cache isolation; durable idempotent writes; and explicit context/location lifecycle plus targeted verification.

### Cited Findings

**Fixed since the initial October 16 review — do not present these as current defects:**

- Schedule creation/PATCH now enforce valid time, IANA zone, unique strict-integer days and same-day nonempty windows; session keys are checked for real date, matching meal and active weekday. Arbitrary distance from today is explicitly undecided in D016, not an accidentally missing decided contract. [Validation](/Users/winstontang/Downloads/nosh/services/api/app/contexts/validation.py:22), [PATCH merge](/Users/winstontang/Downloads/nosh/services/api/app/contexts/service.py:52), [Session validation](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:68), [D016](/Users/winstontang/Downloads/nosh/DECISIONS.md:284).
- Onboarding now has an owned-context/radius-checked endpoint and sets pre-Nosh provenance. Place-state writes use atomic `INSERT ON CONFLICT` and preserve the provenance flag by OR. [Atomic upsert](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:105), [Onboarding route](/Users/winstontang/Downloads/nosh/services/api/app/places/router.py:1).
- No-history cuisine prior is now Beta(1,1); only flagged pre-Nosh places form the prior; manual visits are excluded from learned outcomes, resolving the D015 mismatch and double counting. [Pure priors](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/priors.py:25), [Evidence query](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:372), [Beta parameters](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/engine.py:42).
- Response replay now returns the original action result, including the Another-generated next proposal, even if session state moved on. Visit pagination now uses timestamp plus unique ID. [Replay](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:453), [Pagination](/Users/winstontang/Downloads/nosh/services/api/app/visits/service.py:151).
- Confirmation UI freezes the first request, rejects incomplete proposal links, blocks double taps, shows saving/failure and only acknowledges the server-stored success/rating. Seven screen tests now supplement 36 date-helper tests. Do not repeat the old claim that all mobile tests are date helpers. [Hook](/Users/winstontang/Downloads/nosh/apps/mobile/src/hooks/useVisitConfirmation.ts:54), [Screen guard](/Users/winstontang/Downloads/nosh/apps/mobile/app/confirmation/[sessionId].tsx:39), [Screen tests](/Users/winstontang/Downloads/nosh/apps/mobile/src/__tests__/confirmationScreen.test.tsx:1).
- Import packaging and JWT documentation were corrected. Mobile is to use project URL and publishable key; the API already validates asymmetric JWKS without a shared secret for new projects. [Importer](/Users/winstontang/Downloads/nosh/services/api/jobs/ingest_places/importer.py:1), [Auth config](/Users/winstontang/Downloads/nosh/.env.example:29).

**Strengths to retain:**

- Correctly indexed geography radius filtering and eager cuisine loading. [Query](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:62), [Index](/Users/winstontang/Downloads/nosh/services/api/app/places/models.py:44).
- Locked session creation/response transitions, ownership checks, DB uniqueness, Go-is-intent, and exact-proposal acceptance required for visit confirmation. Fresh integration checks cover these including six concurrent-database tests. [Sessions](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:50), [Responses](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:160), [Visits](/Users/winstontang/Downloads/nosh/services/api/app/visits/service.py:17).
- Backend local bypass is explicitly restricted and production auth fails closed, validating signature/expiry/issuer/audience/role/subject. [Configuration](/Users/winstontang/Downloads/nosh/services/api/app/config.py:111), [JWT validation](/Users/winstontang/Downloads/nosh/services/api/app/auth/dependencies.py:124).

**Residual findings, revalidated against the hardening work:**

1. **Recommendation evidence and replay remain incomplete.** Snapshot stores candidate count, winner distance, one cuisine sample and seed, not candidate IDs/features or priors. Exclusion counts are always empty. This cannot fully reconstruct old decisions once catalog/user state changes. Cuisine RNG draws follow input order. SQL orders only by distance, so equidistant/co-located candidates have no stable secondary ordering. A fresh pure-function probe with the identical set and seed but reversed input still changes winner. [Snapshot](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:347), [RNG iteration](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/engine.py:71), [Distance-only ordering](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:77), [Required decision record](/Users/winstontang/Downloads/nosh/RECOMMENDATIONS.md:178).
2. **Ranking explanation does not match evidence.** `context_fit=1.0` for any provided meal type plus primary cuisine, so the same restaurant gets equal lunch/dinner fit without meal data. `highly_rated` uses curated numeric quality, discussed above. Exploration is a hash of place ID/sequence, not observed exposure tracking. [Scoring](/Users/winstontang/Downloads/nosh/services/api/app/recommendations/engine.py:113).
3. **Mobile shared authentication/cache isolation remain unfinished.** Today the hook is a local UUID adapter stored in SecureStore, with independent token state per invocation. The global QueryClient persists across sign-out, keys such as `['contexts']` are not user-scoped, and sign-out does not clear/cancel queries. Account switching can retain another local user's cached data; this is code inspection, not evidence of a deployed Supabase leak. Address it as part of real auth. [Hook](/Users/winstontang/Downloads/nosh/apps/mobile/src/hooks/useAuth.ts:22), [QueryClient](/Users/winstontang/Downloads/nosh/apps/mobile/app/_layout.tsx:5), [Query key](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/index.tsx:40), [Sign-out](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/settings.tsx:17).
4. **Durable offline behavior remains absent.** Existing response keys are stable proposal+action identities and proposal-backed visits are deduplicated. The new confirmation hook preserves its request within that component lifetime; it is not a durable outbox. Global mutations still retry once, while context-create has no event ID and manual visits without proposal have no uniqueness/idempotency identity. Lost acknowledgments can duplicate those creates. The current confirmation UI guards against manual/missing-proposal writes, so do not conflate this API gap with the now-fixed confirmation screen. [Response keys](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/index.tsx:60), [Retry setting](/Users/winstontang/Downloads/nosh/apps/mobile/app/_layout.tsx:5), [Context create](/Users/winstontang/Downloads/nosh/services/api/app/contexts/service.py:14), [Visit creation](/Users/winstontang/Downloads/nosh/services/api/app/visits/service.py:82).
5. **Context/location lifecycle needs a decision before D017.** The form still hardcodes one location/radius/all days and main screen chooses the first enabled context, not an explicitly selected active one. D017 now accepts foreground use-time location with saved-anchor fallback, explicitly not yet implemented; its API contract is undecided. Another re-reads current context but session retains original `context_version`. Session creation does not check `disabled_at`; ownership lookup returns disabled contexts. Define context changes, disabled contexts, location freshness and frozen decision origin together rather than tacking transient coordinates onto the old workflow. [Form](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/contexts/new.tsx:36), [Selection](/Users/winstontang/Downloads/nosh/apps/mobile/app/(app)/index.tsx:46), [D017](/Users/winstontang/Downloads/nosh/DECISIONS.md:306), [Another](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:286), [Original version](/Users/winstontang/Downloads/nosh/services/api/app/suggestions/service.py:117), [Ownership lookup](/Users/winstontang/Downloads/nosh/services/api/app/contexts/service.py:40).

### Inferences

Proposed bounded work packages in priority order:

1. Real reviewed neighborhood data with source/rights/refresh/taxonomy rules. Keep neutral missing quality and make admission counts visible.
2. Sort stable cuisine/candidate IDs before consuming RNG, snapshot sufficient permitted normalized features/priors plus policy/data/taxonomy versions, record exclusions, and use provenance-backed reasons. Keep meal fit neutral until supported. The hardening retained `policy_v0` for restoring documented priors and explicitly notes old dev decisions cannot be replayed bit-for-bit; future behavior changes should have an immutable version.
3. Shared Supabase session owner, secure token persistence/refresh, per-user cache namespace and clear/cancel on sign-out/deletion. Complete the already-planned context controls and D017 foreground location contract.
4. Persist suggestion and outbox before sending; stable event ID and frozen payload per logical action; acknowledge/remove only on server result, reconcile conflicts and reauthenticate on 401. Extend dedupe to other creates before queuing them. Preserve the already-correct response and proposal-backed-visit semantics.
5. Add targeted auth-switch/outbox/real-provider-contract tests and CI `alembic check` (currently only migration round-trip), and consider generated OpenAPI types or a drift check. Finish EAS/icons/staging as Milestone 3 requires; do not start Milestone 4 notifications early. Avoid speculative dependency upgrades or architecture replacement.

Lower-priority query improvements: push onboarding limit into SQL (currently slices after loading all nearby places), join place names for visit history rather than fetching per row, and measure real catalog plans before adding indexes/caches. No load evidence justifies a rewrite. [Onboarding query](/Users/winstontang/Downloads/nosh/services/api/app/places/service.py:255), [History serialization](/Users/winstontang/Downloads/nosh/services/api/app/visits/service.py:178), [CI migration steps](/Users/winstontang/Downloads/nosh/.github/workflows/ci.yml:91), [Manual client types](/Users/winstontang/Downloads/nosh/apps/mobile/src/api/types.ts:1).

Fresh reproducer (existing production engine; no code changes):

```python
import uuid
from app.recommendations.engine import recommend, score_place
from app.recommendations.types import CandidatePlace
p1 = CandidatePlace(uuid.UUID(int=1), uuid.UUID(int=101), 'a', 100, 0.5, True)
p2 = CandidatePlace(uuid.UUID(int=2), uuid.UUID(int=102), 'b', 100, 0.5, True)
args = dict(session_id=uuid.UUID(int=1), stats_by_cuisine={}, already_proposed=set(),
            radius_meters=1000, sequence_number=1, meal_type='dinner')
a = recommend(candidates=[p1,p2], **args)
b = recommend(candidates=[p2,p1], **args)
print(a.proposal.candidate.cuisine_slug, b.proposal.candidate.cuisine_slug)
# October 19 output: a b (same set/seed; reversed list)
p3 = CandidatePlace(uuid.UUID(int=3), uuid.UUID(int=101), 'a', 100, 0.8, True)
print(score_place(p3,1000,1,'dinner').reason_codes)
# ['nearby', 'new_to_you', 'highly_rated']
print(score_place(p3,1000,1,'lunch').context_fit, score_place(p3,1000,1,'dinner').context_fit)
# 1.0 1.0
```

### Gaps

Cache isolation, duplicate non-proposal creates, disabled contexts and context-version evolution are based on clear code paths, not fresh device/network fault injection. The SQL input-order risk is specifically tied/equidistant or externally reordered input, not a claim that ordinary unequal-distance queries randomly reorder. No current cloud deployment, real device, TestFlight build or push scheduler was tested.

Product questions already acknowledged by hardening remain: a mistaken onboarding Been flag is irreversible without audited correction; classifying a previously Nosh-confirmed place as Been can remove North Star credit. D018 accepts the present rule, so treat this as a decision to revisit with usability evidence, not an unacknowledged coding defect. [D018](/Users/winstontang/Downloads/nosh/DECISIONS.md:324), [Open questions](/Users/winstontang/Downloads/nosh/notes.md:48).

## 3. What verification was freshly run?

### Takeaway

All fresh executable code/compatibility checks passed on October 19, including online Expo checks and real integration/migration checks on disposable port 5433. This verifies the foundation, not real source coverage, offline readiness or complete product behavior. Tests ran against the user's uncommitted hardening workspace.

### Cited Findings

Commands followed [README verification](/Users/winstontang/Downloads/nosh/README.md:145) using existing environments; UV used `/private/tmp/nosh-review-oct19-uv`, npm network checks used `/private/tmp/nosh-review-oct19-npm`. The following are actual tool results from this review, not copied historical counts:

- Root `uv run --frozen --offline pytest tests/ -q`: **12 passed, 0.10s**. Root `uv lock --check --offline`: **pass**, 15 packages.
- API `uv run --frozen --offline pytest tests/ -q -m 'not integration'`: **148 passed, 46 deselected, 1.71s**. Two dependency/test-key warnings, no failures.
- API `ruff check app/ jobs/ tests/`: **pass**; `ruff format --check app/ jobs/ tests/`: **58 already formatted**; `mypy app/ jobs/ --strict`: **no issues in 46 source files**. API offline lock check: **pass**, 86 packages.
- Integration: `DATABASE_URL=postgresql+asyncpg://nosh:nosh_dev@localhost:5433/nosh_test APP_ENVIRONMENT=test AUTH_LOCAL_DEV=true uv run --frozen --offline pytest tests/ -q -m integration`: **46 passed, 148 deselected, 15.36s**. Includes downgrade/upgrade round-trip and six concurrent-database cases. No development database writes; only disposable 5433. [Integration tests](/Users/winstontang/Downloads/nosh/services/api/tests/test_integration.py:1).
- Additional `DATABASE_URL=postgresql+psycopg2://nosh:nosh_dev@localhost:5433/nosh_test uv run --frozen --offline alembic check`: **pass**, “No new upgrade operations detected.”
- Mobile `npm run typecheck`, `npm run lint`: **pass**. `npm test -- --runInBand`: **43 tests, 2 suites passed, 1.199s**. Both date helper and confirmation-screen suites passed. [Screen suite](/Users/winstontang/Downloads/nosh/apps/mobile/src/__tests__/confirmationScreen.test.tsx:1).
- Network-enabled `npx --no-install expo install --check`: **Dependencies are up to date**. Network-enabled `npx --yes expo-doctor`: **18/18 passed**. No offline caveat on these fresh successful runs.
- `git diff --check`: **pass** before and after checks. Git status remained the user's hardening changes and existing report/research directories; no product files, dependencies, canonical docs, migrations, staging, commits or pushes were changed by this review.

### Inferences

The new tests materially strengthen the previous foundation, particularly priors/provenance, concurrency, replay, pagination, validation and confirmation state. They do not establish correctness of an external catalog or coverage of auth switching/offline/restart flows. Keep the current stack and invest next in observable source quality and completing Milestone 3.

### Gaps

- `npm ci` and `uv sync` were not repeated; existing installed environments and lock consistency were used. Therefore this is not a clean-machine install reproduction.
- No remote CI run was triggered or cloud status inspected; the workflow file was reviewed and its executable gates re-run locally.
- No provider corpus, production secrets, performance benchmark, live iOS/device test, build signing, deployment, or notification delivery was part of this read-only review.
