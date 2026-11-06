# Live dish availability and delivery feasibility

Research date: November 1, 2026. US/San Francisco initial market assumed. This is exploratory strategy, not an accepted change to Nosh's phase-one scope. Source pages are current official documentation; access and commercial eligibility still require provider confirmation.

## Can Google Places resolve a dish into a nearby available meal?

### Takeaway
Google Places can find candidate restaurants from food-related text, but its documented response is a place record, not a verified, purchasable menu item. An ontology supplies semantic relevance; it does not supply item availability.

### Cited Findings
- Text Search accepts food-oriented queries, location bias/restriction, and field masks. Google's own examples include pizza and spicy vegetarian food. It returns Place objects; identical requests need not return identical results. This supports discovery, not a contractual guarantee that a named dish is sold now. [Text Search documentation](https://developers.google.com/maps/documentation/places/web-service/text-search)
- The documented Place schema has restaurant-level fields such as opening hours, price range, delivery, takeout, and servesVegetarianFood. It does not expose a structured menu-item catalog with item identifiers, item prices, stock, ingredient lists, modifiers, or checkout. A delivery boolean means the business supports delivery, not that it serves a particular address now. [Place resource](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)
- Places policy permits indefinite retention of place IDs, while restricting caching of other content and requiring attribution. [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- Google's terms prohibit scraping, disallowed caching, and creating content from Maps content, and specifically restrict using Maps content to train/test/validate/fine-tune AI models. Do not assume that extracting dish tags from Google reviews or summaries creates freely owned ontology content. [Google Maps Platform terms, section 3.2.3](https://cloud.google.com/maps-platform/terms)

### Inferences
- A query such as “laksa near me” can propose restaurants to investigate. It cannot safely support “say yes and this laksa arrives” without another availability and ordering layer.
- Prefer separating a reusable dish-concept graph (independently licensed/editorial knowledge) from merchant offerings (a particular dish variant at a location, price, service window, fulfillment channel, and last verification time).
- A restaurant being open is weaker evidence than its lunch menu being active; a menu listing is weaker than the item being in stock; stock is weaker than deliverability to this customer's address. These states must not collapse into one availability flag.
- Nosh's current IDs-only policy should remain a boundary; building a permanent dish-to-place graph from Google-derived content is not an obvious workaround. Use independently sourced merchant permission or appropriate licensed feeds for durable offerings.

### Gaps
- No live SF dish-search quality benchmark was run. Coverage, false positives, and dish-name ambiguity remain unmeasured.
- No source establishes that Google's consumer Maps dish features are all exposed through Places API.
- No commercial menu provider was validated for Nosh's desired rights, geography, freshness, and approximately $50 monthly budget.

## Can Nosh automate delivery through DoorDash or Uber Eats?

### Takeaway
Public documentation describes merchant integrations and courier dispatch, not unrestricted consumer access to every restaurant's menu and checkout. Partnership eligibility is a prerequisite to the seamless reel experience.

### Cited Findings
- DoorDash Marketplace API access is limited. Its documented purpose is managing partner menus/stores and receiving orders placed on DoorDash; it is not described as an open consumer marketplace browsing/ordering API. [DoorDash Marketplace overview](https://developer.doordash.com/en-US/docs/marketplace/overview/)
- DoorDash distinguishes Drive orders originating from the merchant from orders originating on its marketplace. [DoorDash FAQ](https://developer.doordash.com/en-US/docs/marketplace/faq/getting_started/)
- DoorDash Drive's tutorial currently warns that production access is restricted and that it cannot promise a certification timeline. It advises developers who have not completed development and submitted a production request to pause development. [Drive getting started](https://developer.doordash.com/en-US/docs/drive/tutorials/get_started/)
- Uber Eats' integration guide describes store management, menu synchronization, and receiving/fulfilling customer orders. It lists NDA/API licensing and partner approval prerequisites, and asks for an aligned business agreement for uses outside order fulfillment. [Uber Eats getting started](https://developer.uber.com/docs/eats/guides/getting-started)
- Uber Eats authentication requires explicit merchant authorization to connect stores and approval/whitelisting for production scopes. Regular menu and order operations concern connected stores. [Uber Eats authentication](https://developer.uber.com/docs/eats/guides/authentication)
- Uber Direct dispatches a courier to pick up an order at a store and deliver it; Uber explicitly distinguishes this from Eats marketplace APIs. [Uber Direct overview](https://developer.uber.com/docs/deliveries/overview)
- Uber's menu model includes location-specific menus, menu hours, items, categories, and modifiers, with potentially separate menus for delivery and pickup. These are the operational distinctions a simple dish graph does not contain. [Uber menu integration](https://developer.uber.com/docs/eats/guides/menu-integration)

### Inferences
- A courier API does not make a restaurant accept or prepare an order. Nosh still needs menu rights, an ordering channel, pricing/modifiers, payment/consent, merchant acceptance, and failure handling. Courier success alone cannot satisfy the product promise.
- Start with an external restaurant/order-page handoff and explicit customer checkout if testing dish demand. This sacrifices one-tap magic but avoids claiming an integration that Nosh does not have. Verify destination URLs; do not promise supported exact-item deep links without evidence.
- Direct relationships with a few restaurants could make controlled dish-to-delivery testing possible, but introduce merchant onboarding and operational work. That is a different business model from the current lightweight recommendation app.

### Gaps
- Nosh's eligibility, negotiated rights, fees, production approval timelines, and access to consumer ordering are unknown. Documentation does not prove approval will be granted.
- No delivery cost or gross-margin estimate is defensible without geography, order volume, contract terms, subsidy policy, and who pays fees.

## Does dish first reduce sustainable data overhead?

### Takeaway
It reduces dependence on a restaurant catalog only for a discovery-only product. For a product promising nearby meals or delivery, it adds a more granular and changeable data layer on top of venue resolution.

### Cited Findings
- The reviewed Google API is place-oriented, while Uber's merchant API separately models menus, items, modifiers, and changing availability. This is concrete evidence of distinct data responsibilities. [Google Place schema](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [Uber menu integration](https://developer.uber.com/docs/eats/guides/menu-integration)

### Inferences
- Compare against Nosh's actual accepted baseline: live Google Places plus stored identifiers and user-owned events. The proposed pivot cannot remove a comprehensive in-house restaurant database that the current plan has already retired.
- Reusable dish semantics can amortize across cities and remain relatively stable. Dish-to-merchant mappings, variant interpretation, availability, prices, and orderability remain local and frequently changing. Maintenance is shifted, not eliminated.
- Three viable scopes have sharply different burdens: (1) culinary discovery and saved interests—mostly ontology/editorial and preference work; (2) recommend a dish with verified nearby offering—ontology plus menu/venue resolution; (3) automatically deliver—everything in (2), plus commercial integrations and fulfillment operations.
- At the current budget, an initial experiment should limit geography and dish coverage, measure manual verification time per successful meal, and avoid “all dishes worldwide” as a prerequisite. The cost comparison should include curator/founder labor, not only API bills.
- Proposed pilot gates: measure how often an appealing dish has an actionable local offering, the number of stale/unavailable suggestions, time spent correcting matches, external checkout completion, and confirmed enjoyment. These are recommendations, not industry benchmarks.

### Gaps
- There is no defensible percentage reduction in overhead yet. A small measured pilot is needed to compare total labor and provider costs against current restaurant-first discovery.
