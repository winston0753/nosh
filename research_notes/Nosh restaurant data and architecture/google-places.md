# Google Places feasibility for Nosh

Research date: 2026-10-16. Primary documentation was fetched live; this assessment assumes a US/non-EEA billing address. Commercial negotiated terms could differ. No paid API requests or completeness/accuracy benchmark were run. This is engineering interpretation of published terms, not a legal opinion.

## Can Google populate Nosh's durable catalog and recommendation snapshots?

### Takeaway

Under published standard terms, Google Places is a poor source for Nosh's persistent restaurant database, offline suggestion cache, and reproducible ranking inputs. Its useful role is optional live display, while an independently licensed catalog and Nosh's own outcome data remain authoritative.

### Cited Findings

- Terms §3.2.3(a–c) restrict extraction, prefetching, indexing and storage; explicitly include saving business names, addresses and reviews; limit caching to stated exceptions; and prohibit creating content from Maps content. §3.2.3(d) also restricts directory substitutes and requires independent value; §3.2.3(g) restricts modifying search results. These are separate issues from API price. — [Maps Platform terms](https://cloud.google.com/maps-platform/terms)
- Service-specific terms §14 allow Places content without a map but prohibit its use in conjunction with a non-Google map. The §14.3 caching exception covers **latitude/longitude for 30 days**, not names, hours, ratings or reviews. General §3 permits specified Google identifiers. — [Service-specific terms](https://cloud.google.com/maps-platform/terms/maps-service-terms)
- Place IDs can be retained and reused; Google recommends refreshing IDs older than 12 months through an ID-only request, at no charge. IDs can change and one physical place can have multiple IDs. — [Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id)
- Nosh explicitly supports missing ratings/hours/photos; its accepted D008 selects a small reviewed catalog, and ranking permits neutral quality when licensed ratings are unavailable. The architecture requires durable places, source identifiers and timestamps, candidate snapshots, and offline cards. — [PRODUCT.md](/Users/winstontang/Downloads/nosh/PRODUCT.md), [D008](/Users/winstontang/Downloads/nosh/DECISIONS.md:140), [data model](/Users/winstontang/Downloads/nosh/ARCHITECTURE.md:211), [quality policy](/Users/winstontang/Downloads/nosh/RECOMMENDATIONS.md:86)
- Google's `rating` is a 1–5 aggregate based on user reviews; the API returns at most five reviews ordered by relevance. `currentOpeningHours` concerns the next seven days including today; regular hours describe a typical schedule. — [Place resource](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)

### Inferences

- Do not import Google stars into `metadata.quality_score`, persist Google rating-derived ranking snapshots, copy business details into PostGIS, or create a daily refresh job that treats a 30-day expiry as permission. Neither short TTL nor manual copying resolves the broader restrictions above.
- Keep three concepts separate: data-record confidence, public aggregate stars, and a Nosh user's confirmed positive/negative outcome. Confidence that a venue exists is not restaurant quality; Google stars are not personalized taste; a neutral prior is not an asserted rating.
- Retain Nosh canonical UUIDs and a provider-ID mapping. Persist open/licensed fields with provenance; use independently sourced coordinates for radius queries and Apple Maps destinations. This also avoids provider identity changes corrupting visit history.
- A recommendation service backed by licensed inputs and explicit user outcomes has substantial independent value, but that alone does not waive Google's storage restrictions.
- An independently sourced offline card can work without any Google request. Start with founder curation and neutral quality defaults; add paid data only if the pilot demonstrates a specific unmet need. This follows existing scope rather than expanding it.

### Gaps

- Exact permission for a custom Google-derived score retained without raw ratings is not granted in the reviewed documents. Do not assume it is permitted; obtain contractual clarification before using such scores.
- No direct empirical comparison of SF business accuracy, closures, ratings coverage, or matching quality was performed. Avoid claiming Google is proven more accurate than Overture in Nosh's neighborhoods.

## Is live Google enrichment compatible with the Apple Maps product?

### Takeaway

A mapless Google information surface is explicitly supported. A custom REST-powered Google card beside or connected to Apple Maps presents a policy question; Google's **Places UI Kit** has an explicit any-map exception and may be a better later display option, though it does not solve database storage.

### Cited Findings

- Service-specific §15.1 permits Places UI Kit with or without any map, including a non-Google map, overriding the non-Google-map prohibition. §15.2 still only permits 30-day latitude/longitude caching. — [Service-specific terms](https://cloud.google.com/maps-platform/terms/maps-service-terms)
- New integrations must clearly attribute Google Maps and visually separate its content from other content. Photos/reviews require author attribution and access to their source on Google Maps. Review ordering/filtering must be explained. Google's policy requires applicable terms/privacy notices; it does not license storing returned content. — [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- UI Kit is available on iOS through the PlacesSwift SDK; it has basic and advanced components for details/search, with advanced tiers allowing more customization. — [iOS UI Kit overview](https://developers.google.com/maps/documentation/places/ios-sdk/places-ui-kit-overview)
- Its compact detail view can show rating/count, address, place type, price, photo and open-now status. Full view can include hours, reviews, phone and website. It is a SwiftUI view; queries can use a place ID. Reloading the same place is billed again. — [iOS details component](https://developers.google.com/maps/documentation/places/ios-sdk/place-details-ui-kit)
- UI Kit billing is per request to its components, independent of displayed fields; Advanced Details/List/Search use the Pro SKU. — [SKU definitions](https://developers.google.com/maps/billing-and-pricing/sku-details)
- Google's Maps JavaScript policy explicitly says persisting an interaction-returned place name for use outside that session constitutes scraping. — [Maps JavaScript policies](https://developers.google.com/maps/documentation/javascript/policies)
- Nearby Search (New) returns no more than 20 results per request and defaults to popularity ordering, with distance ordering available. It is a discovery API, not a guaranteed exhaustive catalog export. Ratings and opening hours trigger Enterprise fields. — [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search)

### Inferences

- Do **not** state categorically that every external Apple Maps handoff violates Google terms. Published wording prohibits use with/near non-Google maps and explicitly linking a Google map to a non-Google map; it does not clearly settle every mapless-card/external-navigation flow. The defensible recommendation is to keep Apple coordinates independent and get clarification for a custom REST-card implementation.
- UI Kit merits a narrow prototype only after the open catalog and Milestone 3 are finished. It provides a lower-cost display route and clearer map compatibility, but embedding SwiftUI in Expo requires an implementation/compatibility assessment. No verified first-party React Native adapter was found in reviewed primary docs; do not silently change Expo versions.
- Suggested boundary: Nosh selects a place entirely from licensed local inputs; optional Google panel renders live by stored Google place ID; Google payloads never enter durable place metadata, offline persistence, log bodies, analytics events or recommendation snapshots. API outage or no matching Google ID leaves the original Nosh card usable.
- If using REST instead of UI Kit, fetch only when the user opens the details surface, use a fixed server-owned field mask and bounded retries/quota, and preserve attribution. This is a proposed architecture, contingent on permission for the exact Apple flow.
- Matching is a separate problem: a Google ID can attach to the wrong chain branch. Prefer reviewed mappings at pilot scale; do not assume name-only lookup is sufficient. Nearby Search's top-20 output cannot justify a “neighborhood completion” denominator.

### Gaps

- No account-specific contract, legal approval, SwiftUI/Expo integration, or visual attribution QA was performed. UI Kit data may not be extracted into Nosh's own card/cache merely because its display price is cheaper.
- The reviewed documents do not directly settle every external Apple Maps handoff flow. UI Kit's explicit any-map permission is stronger evidence than trying to interpret a custom API integration optimistically.

## What are realistic Google costs and implementation controls?

### Takeaway

For a small pilot, Google display cost can be modest; storage rights and architectural coupling are the bigger problems. Cost depends strongly on whether Nosh requests details for one displayed place or enriches every candidate.

### Cited Findings

- Since 2025-03-01, SKU-specific free usage replaced the old $200 monthly credit. — [Pricing changes FAQ](https://developers.google.com/maps/billing-and-pricing/faq)
- Global pay-as-you-go prices below are USD per 1,000 monthly requests after that SKU's free cap, within the first 100,000-event band. Usage is aggregated across projects attached to a billing account. — [Current price list](https://developers.google.com/maps/billing-and-pricing/pricing)

| SKU | Monthly free cap | $/1,000 beyond cap |
|---|---:|---:|
| Details Essentials, IDs only | Unlimited | $0 |
| Text Search Essentials, IDs only | Unlimited | $0 |
| Details Essentials | 10,000 | $5 |
| Details Pro | 5,000 | $17 |
| Details Enterprise | 1,000 | $20 |
| Details Enterprise + Atmosphere | 1,000 | $25 |
| Nearby Search Pro / Text Search Pro | 5,000 each | $32 |
| Nearby Search Enterprise / Text Search Enterprise | 1,000 each | $35 |
| Details Photos | 1,000 | $7 |
| UI Kit Query | 10,000 | $1 |
| UI Kit Pro | 5,000 | $5 |

- For Details (New), `displayName` and business status are Pro; ratings/count, current/regular hours, website, phone and price are Enterprise; reviews and meal-service attributes are Enterprise + Atmosphere. `name` is a resource identifier, not the business display name. Use explicit field masks; avoid `*`. — [Details field tiers](https://developers.google.com/maps/documentation/places/web-service/place-details)
- A request is billed once at the highest SKU its fields require, not the sum of all field tiers. Billing must be enabled. Places New rate quotas are per API method per project; hitting a quota stops service responses. — [Usage and billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)

### Inferences

Illustrative calculations, not forecasts. Assume 30 days/month, every user active daily, **two viewed cards/user/day** (one initial plus one Another), one live enrichment request per card, no cached Google content, US prices, no other account usage consuming free caps. Taxes, hosting, retries, reloads, photos and context autocomplete are excluded.

| Display approach | Requests at 50 users | Monthly cost at 50 | Requests at 500 users | Monthly cost at 500 |
|---|---:|---:|---:|---:|
| REST Details Enterprise (stars/hours) | 3,000 | $40 | 30,000 | $580 |
| REST Details Enterprise + Atmosphere (reviews) | 3,000 | $50 | 30,000 | $725 |
| UI Kit basic details | 3,000 | $0 | 30,000 | $20 |
| UI Kit advanced details | 3,000 | $0 | 30,000 | $125 |

Formula: `max(requests − free_cap, 0) × price_per_1000 / 1000`, using the published inputs above. These UI Kit numbers are display-only, not an equivalent license or API for extracting ratings.

Discovery is separate. Assuming one Nearby Search per user per day gives 1,500 / 15,000 calls for 50 / 500 users. Pro search adds $0 / $320. Enterprise search (ratings in result set) costs $17.50 / $490. Do not automatically add Details if Search already returns all information needed for a live surface. For a pre-reviewed independent catalog with matched Google IDs, recurring Google discovery calls can be zero; initial matching effort is additional.

Enriching **20 candidates per user daily** with Details Enterprise means 30,000 / 300,000 calls: $580 / $5,180 monthly. The larger estimate uses 99,000 paid calls at $20/1,000, then 200,000 at $16/1,000. It still does not confer permission to warehouse ratings. UI Kit is not a shortcut for extracting those candidate scores.

Operational proposal: fixed allowed field masks, per-user abuse limits, request timeouts, capped retries, a circuit breaker/fallback, billing alerts plus enforceable API quotas, and API keys restricted to the actual server/app and enabled APIs. Record request counts, status, latency and SKU identifiers without response bodies or precise user coordinates. Do not add provider-wide nightly rating refresh as a cost optimization.

### Gaps

- User engagement, Another frequency, reopened-card count and initial matching volume are unknown; actual spend can be lower or higher. A free cap is per SKU/account, not per user or project. Negotiated discounts and subscriptions were not modeled.
- Official pages can contain stale generated summaries: the usage page still mentions the historical $200 credit with its 2025 expiry. The current pricing table and pricing-change FAQ are the authoritative inputs for these calculations.
