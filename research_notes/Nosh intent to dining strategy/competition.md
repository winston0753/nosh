# Competitors and the intent to meal opportunity

Research checked October 28, 2026. These are verified advertised capabilities, not a hands-on exhaustive product audit. Product effectiveness and retention are not established by marketing descriptions.

## What capabilities already overlap with the proposed direction?

### Takeaway
Saved restaurants, friend-based discovery, taste matching, and even reminders when near a saved place already exist. Nosh should not position any of those individually as unique. A more focused hypothesis is that a specific, timely commitment with people the user already knows can turn unfulfilled dining intent into completed meals.

### Cited Findings
- Beli's developer description advertises ranked lists and maps of visited and want-to-try restaurants, friends' dining activity, personalized recommendations, a taste profile, and a friend match score. This establishes overlap in both wishlists and social taste data. It does not establish its current feature set exhaustively. [Beli developer listing](https://apps.apple.com/us/app/beli/id1478375386)
- Google Maps allows users to create lists of places they want to visit, share lists, and follow other people's lists. A shared wishlist alone offers limited differentiation. [Google Maps help](https://support.google.com/maps/answer/7280933?co=GENIE.Platform%3DDesktop&hl=en)
- Mapstr explicitly describes proximity alerts for places marked “To try,” with always-on geolocation permission if required. Its FAQ also documents friend maps and private messages. This directly overlaps with the hypothesis that a nearby saved-place reminder is novel. [Mapstr FAQ](https://en.mapstr.com/faq)
- Mapstr's developer listing advertises saved-place proximity alerts, friend maps, personalized matching, and Google Maps/CSV/KML imports. These are advertised features, not independently verified conversion outcomes. [Mapstr developer listing](https://apps.apple.com/us/app/mapstr-save-follow-places/id917288465)
- Yelp's October 21, 2025 announcement describes restaurant/business question answering based on reviews, photographs, business information, and websites, plus natural-language search. Yelp is actively reducing discovery friction; treating it as only a static directory understates the incumbent. [Yelp official announcement](https://www.yelp-press.com/press-releases/press-release-details/2025/Yelp-Expands-AI-Features-to-Make-Local-Discovery-More-Conversational-Visual-and-Seamless/default.aspx)

### Inferences
- A mealtime nudge is a plausible initial acquisition/engagement wedge, not a demonstrated defensible moat. Incumbents can implement notifications; defensibility would need evidence of a habit, trusted coordination workflow, concentrated distribution, or valuable current intent and commitment data.
- A positioning hypothesis with sharper distinction: “We help you actually go to places you already want to try.” A stronger social variant: “One place, one time, with someone you want to eat with.” Neither is proven whitespace or product-market fit.
- Competition includes the existing group chat and doing nothing. Nosh must improve completed plans with less coordination work, not simply generate another restaurant list.

### Gaps
- No competitor retention, nudge-to-visit conversion, active local-user density, or willingness-to-pay data was verified.
- The reviewed sources do not prove that Beli, Yelp, Google Maps, or Mapstr lack mealtime scheduling, mutual-wishlist matching, or commitment workflows. Avoid absence claims.
- Meli was not needed for the conclusion; Mapstr provides a direct, primary-source feature overlap.

## Can Nosh use existing wishlists without recreating the data burden?

### Takeaway
Existing lists can seed intent, but importing is a product capability that must be validated, not assumed. Nosh can start with a few user-selected places and still test the value proposition without requiring a user's entire dining history or an automatic sync partnership.

### Cited Findings
- Mapstr documents Google Maps list import through the phone share sheet and file import through Google Takeout. This proves that at least one product advertises a migration path; it does not establish an officially supported Google API available to Nosh or permission to copy arbitrary third-party content. [Mapstr FAQ](https://en.mapstr.com/faq)
- Google Maps' official list help documents user-facing sharing and following; this page does not document a developer API for retrieving all private saved lists. [Google Maps help](https://support.google.com/maps/answer/7280933?co=GENIE.Platform%3DDesktop&hl=en)

### Inferences
- Separate three resources: restaurant metadata supplied by a provider, accumulated taste/review history, and Nosh-native future intent/availability/commitments. Only the third is necessary to validate a plan-making product. This is a strategic distinction, not a legal ownership conclusion.
- Begin with “pick three nearby places you would actually go to this week,” optionally entered from user-shared place links. That is a proposed experiment, not a claim that every source link resolves reliably or that imports have been implemented.
- A whole-library migration can recreate the onboarding friction the pivot is meant to avoid. Measure time to first actionable suggestion and first completed meal before investing in bulk imports.
- A Nosh intent or availability signal becomes useful immediately to that user or pair; it need not wait for a citywide ratings corpus. It can also go stale quickly, so asking for “available today” may be more valuable than permanent taste inference.

### Gaps
- No reliable public Beli wishlist API, OAuth export integration, or supported Nosh import mechanism was verified. Do not promise any.
- Provider licensing and permissible handling of imported metadata require a separate implementation review. Nosh's accepted ID-only policy should remain in force while testing strategy.

## Which competitive implications should guide the first test?

### Takeaway
Test whether timing and a concrete commitment add value before broad stranger matching or sophisticated personalization. Existing friends, partners, coworkers, or a small recurring community provide trust and density without requiring a citywide network from day one.

### Cited Findings
- Beli already advertises friend taste matching; Mapstr already advertises friend maps and nearby saved-place alerts. The proposed test should therefore measure completed plans rather than novelty of those features. [Beli developer listing](https://apps.apple.com/us/app/beli/id1478375386) [Mapstr developer listing](https://apps.apple.com/us/app/mapstr-save-follow-places/id917288465)

### Inferences
- Compare a solo saved-place nudge with a specific invitation among an existing pair: same quality of candidate, explicit meal time, and an accept/decline deadline. Determine whether companionship is the actual blocker or whether timing/price/distance is sufficient.
- Make the useful unit a pair or a small existing group. A stranger marketplace adds simultaneous availability, mutual comfort, budget, location, and place-preference constraints; solving historical-data cold start by introducing network cold start may worsen the problem.
- “Both saved the identical restaurant” may be too restrictive. Test a union of wishlists with mutual acceptance rather than hard intersection. One person wanting a place and another being happy to join can be sufficient.
- Keep a solo fallback so one user's value does not depend entirely on others installing or replying. A shared plan link can be tested manually before a full invitation feature.
- Long-term moat hypothesis: locally dense repeat groups, reliable attendance, and a trusted routine. These must be earned through repeated completed meals; a growing count of saved restaurants alone does not establish them.

### Gaps
- These are design hypotheses and strategic judgments, not demonstrated causal findings. No adoption or effect-size estimates are justified by the sources reviewed.
