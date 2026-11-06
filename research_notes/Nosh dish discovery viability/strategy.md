# Nosh dish discovery product strategy

Research date: November 1, 2026. Strategic assessment, not an accepted change to the product. Initial US/San Francisco context assumed. Recommendations and pilot sizes below are judgments, not validated market benchmarks.

## Does this reduce overhead and improve sustainability?

### Takeaway
A reusable dish-concept catalog can be more geographically portable and slower-changing than restaurant operating facts. However, compared with Nosh's actual accepted plan—live Google Places rather than an owned restaurant catalog—it adds a new knowledge layer. Concept-only inspiration can avoid local inventory maintenance; local dish finding adds menu matching; automatic delivery adds transactional and operational dependencies. These are three different products and cost profiles.

### Cited Findings
- Nosh D021/D022/D027 already specify live Google Places, storage of provider IDs and Nosh-owned data only, and retirement of curated restaurant data. The comparison must be with this accepted baseline, not the old fictional fixtures. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md)
- Current architecture reuses Expo, FastAPI and PostgreSQL and explicitly defers a separate vector database, microservices and other infrastructure. [ARCHITECTURE.md](/Users/winstontang/Downloads/nosh/ARCHITECTURE.md)
- Current product excludes delivery, ordering, payment, menu ingestion, free-text cravings, embeddings and advanced dietary guarantees. The request authorizes investigating those directions, not silently implementing or accepting them. [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md)
- The earlier intent-to-dining report proposed a separate direction and is labeled a strategy proposal, not an accepted product change. [Prior research](/Users/winstontang/Downloads/nosh/reports/Nosh%20intent%20to%20dining%20strategy.md)

### Inferences
- **Concept inspiration only:** technically feasible with bounded scope; avoids own restaurant inventory entirely but also abandons the promise that accepting produces a meal. User must still find, cook or order the suggestion. Test whether this is valuable enough to repeat.
- **Dish-first nearby recommendation:** promising product direction, but unlikely to lower overall operating work relative to accepted live-Places Nosh. It needs both durable dish knowledge and volatile dish-to-menu mappings. Data labor and quality assurance may dominate hosting cost.
- **Automatic dish delivery:** highest overhead. Even a perfect graph cannot supply merchant acceptance, available variants, current total price, address eligibility, payment consent or failed-order support. A courier integration alone does not solve restaurant ordering.
- Semantic portability is the real benefit: one concept and its relationships can be reused in many cities. Operational portability is not automatic; each city still needs obtainable instances.
- Do not budget in API dollars alone. Measure minutes spent maintaining concepts, resolving menus and repairing failed suggestions per fulfilled meal, and paid-provider expense per completed meal.

### Gaps
- Actual provider licensing, access, local menu coverage and delivery integration terms are covered by the availability researcher; none can be assumed from generic search access.
- There is no evidence yet of repeat user demand, willingness to pay or sustainable unit economics for Nosh's dish-first variant.

## What is the differentiated product and how should it learn?

### Takeaway
The user-facing promise should be a good unfamiliar meal the person actually enjoys. The ontology is useful infrastructure, but neither a graph nor semantic similarity establishes preference or a moat. First-party observed outcomes and dependable local fulfillment are more credible differentiation hypotheses.

### Cited Findings
- DoorDash's July 29, 2025 engineering article describes embeddings plus consumer, merchant and item profiles. Item profiles include ingredients, taste profiles and dietary classifications; consumer inputs include order history and time of day; it describes explainable recommendations and editable preferences. It also distinguishes factual extraction in code from LLM narrative synthesis. These are first-party descriptions, not independently measured success. [DoorDash engineering](https://careersatdoordash.com/blog/doordash-profile-generation-llms-understanding-consumers-merchants-and-items/)
- DoorDash's June 11, 2026 announcement describes natural-language restaurant search, personalized context and suggested carts reflecting dietary preferences, budget, group size or past orders; the release specifies initial availability in select iOS areas. This is evidence of competing product capability, not exhaustive coverage or proof of efficacy. [Ask DoorDash](https://about.doordash.com/en-us/news/ask-doordash)
- Google researchers show that implicit interaction feedback contains bias and that directly training on it can produce suboptimal recommendations. Their evidence concerns Google Drive, so applying it to food is an inference. [Qin et al., KDD 2020](https://research.google/pubs/attribute-based-propensity-for-unbiased-learning-in-recommender-systems-algorithm-and-case-studies/)
- Nosh already distinguishes Go intent, ambiguous Another, timing-only Not today, confirmed visit, and outcome rating; its objective explicitly rejects optimizing clicks alone. [RECOMMENDATIONS.md](/Users/winstontang/Downloads/nosh/RECOMMENDATIONS.md)

### Inferences
- Define four separate jobs: ontology defines entities/relationships; semantic retrieval finds meaning-related candidates; recommender chooses which person should see which eligible candidate now; fulfillment resolves a specific obtainable menu item. Combining their names obscures missing capabilities.
- A yes to a dish is valuable stated intent but may reflect the photo, familiarity, current appetite, novelty or expected price. It is not evidence the person ate or liked it. Keep proposed, interested, purchased/visited, ate, liked, and would-eat-again separate. Unknown outcomes stay unknown.
- A dislike can concern preparation, ingredient, texture, price or a bad restaurant instance. Do not propagate a single negative meal to a whole cuisine. Ask one optional reason when useful.
- Build a graph of dish concepts, aliases and variants with separately sourced descriptors; store specific restaurant offers and user outcomes as distinct entities. Typical ingredients are not guaranteed ingredients. Recipe-level or menu-item evidence is needed for strict dietary/allergen claims.
- Cross-cuisine recommendations should bridge a few user-relevant traits while allowing diversity. Shared ingredients alone may miss cooking method, texture and intensity. An appealing explanation is a hypothesis to test, not proof that similarity causes enjoyment.
- A public ontology is reproducible infrastructure. A credible moat hypothesis is a high-quality, rights-cleared and corrected dataset of which culinary transitions lead to good meals for particular people, plus distribution and fulfillment reliability. That moat only exists if enough users repeatedly contribute reliable feedback.
- Positioning suggestion: 'Discover your next favorite dish, from something you already love.' 'Ontology and semantic search' describes implementation, not the benefit.

### Gaps
- No research in this pass establishes that a graph beats simple tags, user-selected interests or a human curator for Nosh.
- No basis to claim competitors lack cross-cuisine personalization or that ontology infrastructure alone is defensible.

## What should Nosh test and reuse before committing?

### Takeaway
Run a small local discovery experiment with a bounded graph and verified meal options. Compare it with simple dish recommendations and the existing restaurant-first concept. Require confirmed enjoyment and manageable maintenance work before expanding the ontology or taking on delivery.

### Cited Findings
- Authentication, meal schedules, user ownership, idempotent writes, sessions, transactional response handling and confirmation already exist; current-location flow and live provider work remain on the roadmap. [IMPLEMENTATION_HANDOFF.md](/Users/winstontang/Downloads/nosh/IMPLEMENTATION_HANDOFF.md)
- D023 currently permits only location-free nudges, with current foreground location after open. A notification promising a locally available dish would need an explicit change or a trustworthy declared location/availability basis. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md)
- D013 defers vectors pending a defined embedding use case/evaluation set; deterministic meal-time recommendations remain a constraint. [DECISIONS.md](/Users/winstontang/Downloads/nosh/DECISIONS.md)

### Inferences
- Suggested bounded trial, purely illustrative: 20–50 dish concepts from 4–6 cuisines actually obtainable in one neighborhood; 10–15 consenting users over 2–3 weeks. Seed with 3–5 foods they already enjoy and explicit constraints. This is qualitative feasibility work, not a powered causal study.
- First test the local mapping burden: can the founder reliably find a current, affordable specific menu item for each suggested concept without excessive manual work? Track stale or wrong matches and per-option verification minutes. If supply cannot be supported, stop the local promise before building a global graph.
- Then alternate comparable meal opportunities between (a) simple dish/tag recommendations and (b) graph-informed cross-cuisine recommendations, using the same available supply and comparable presentation. Restaurant-first suggestions can be a separate concept test; do not change both framing and ranking and claim to identify the cause of lift.
- Measure acceptance, availability after acceptance, actual eating, positive rating, would-eat-again, repeat voluntary use, notification fatigue, decision effort, cost and operator minutes. Primary proposed outcome: confirmed positively rated new dishes per active user, with repeat enjoyment as an additional measure. New restaurant counts would no longer be the central metric; a new dish at a familiar restaurant can succeed.
- Stop or simplify if the graph does not improve decisions over tags; stop the local-fulfillment promise if availability/maintenance defeats the experience; stop expansion if users like the idea but do not repeatedly eat the suggestions. Continue only if verified meals happen, people return voluntarily, and maintenance fits a pre-agreed founder budget. Set numeric thresholds before trial; none are established industry standards.
- In a first pilot, let the user review the actual dish, merchant, price and handoff before purchase. Separate the benefit of dish discovery from the appeal of delegated delivery. Otherwise delivery convenience may account for apparent recommendation success.
- Existing PostgreSQL tables can represent a small graph with IDs and edges. A separate graph database, vector service or live LLM is unnecessary to test this. Offline, reviewed enrichment is a possible future choice subject to rights and recorded decisions. Reuse the app and backend; extend domain types rather than rebuilding.
- Keep research separate from accepted canonical decisions. If the user chooses a pivot, explicitly record the new outcome definition, repeat-restaurant policy, dish/variant identity, source rights, notification semantics and fulfillment scope before implementation.

### Gaps
- The actual cohort size, baseline engagement rate and acceptable maintenance budget are unknown. Proposed trial dimensions are practical starting points, not prescriptions or statistical power estimates.
