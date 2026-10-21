# Place data sources and map terms — findings (2026-10-20)

- **Status:** Research record supporting DECISIONS.md D021–D023 and D028. Root documents remain canonical.
- **Method:** Three web-research passes on 2026-10-20 against official documentation, pricing pages, and terms. No paid API request, legal review, or written provider clarification was obtained.
- **Not legal advice.** Items marked *Ambiguous* need written confirmation from the provider before a public launch.

## 1. Why this was researched

Phase one moved to suggesting a restaurant wherever the user is at meal time (D020). A pre-curated neighborhood catalog cannot cover that, so candidates must come from a live provider. The product also wants a quality signal (rating plus review count) used as a floor, opening hours, price, and chain detection, within a total budget of about $50/month (D028).

Expected volume for a cohort of fewer than 15 testers: about 15 users × 22 weekdays ≈ 330 sessions/month, with one candidate search per session (Another reuses the session's ranked list).

## 2. Summary

| Source | Rating | Review count | Hours | Price | Chain/brand | Cost at ~330 sessions/mo | May store | Verdict for phase one |
|---|---|---|---|---|---|---|---|---|
| Apple MapKit (on device) | No | No | No | No | No | Free | Place ID only | Coverage without quality |
| Apple Maps Server API | No | No | No | No | No | Free (25,000 calls/day) | Place ID only | Coverage without quality |
| Google Places API (New) | Yes | Yes | Yes | Yes | No (type `fast_food_restaurant` only) | ~$0 (inside free caps) | `place_id` only (lat/lng 30 days) | **Selected (D021)** |
| Foursquare Places API | Yes (Premium) | Yes (Premium) | Yes (Premium) | Yes (Premium) | `chains` (not national-only) | ~$6 ($20 minimum top-up) | `fsq_place_id` only | Rejected: signal co-mingling ban |
| Yelp Places API | Yes | Yes | Yes | — | — | $229/month minimum | Unverified | Rejected: cost |
| Overture Places | No | No | No | No | `brand` | Free | Licensed per source | Rejected: no quality or hours |

## 3. Apple

### MapKit (on device)

- `MKLocalSearch` and `MKLocalPointsOfInterestRequest` (filterable by `MKPointOfInterestCategory` and radius) return `MKMapItem`: name, phone, URL, point-of-interest category, time zone, address, location, and `identifier` / `alternateIdentifiers` (`MKMapItem.Identifier`, iOS 18+).
- No rating, review count, opening hours, price, or brand in the public API.
- No documented result limit; developer forums report `MKLocalPointsOfInterestRequest` often returns fewer results than `MKLocalSearch`.
- No per-call charge.
- A place opens in Apple Maps with `MKMapItemRequest(mapItemIdentifier:)` then `openInMaps()`.

### Apple Maps Server API

- Endpoints include `/v1/search` (`includePoiCategories`, `searchLocation`, pagination), `/v1/place/{id}`, `/v1/place/alternateIds`, geocoding, directions, and ETAs.
- The documented Place object has id, alternate IDs, name, coordinate, address lines, structured address, country, and display region. No rating, hours, or price.
- Quota: 25,000 calls per day per team (shared with MapKit JS); HTTP 429 above it.

### Apple terms (Developer Program License Agreement, Attachment 6)

- **§2.5 caching:** Map Data "may not be cached, pre-fetched, or stored … other than on a temporary and limited basis solely as necessary …, after which … You must delete any such Map Data."
- **§2.2:** Map Data may not be used "as part of any secondary or derived database."
- **Place IDs are exempt:** Apple's Place ID documentation states they "are exempt from the storage restrictions in Section 2.5" and may be used as a database primary key. Lookups "always return the most recent information"; a stored ID can fail to resolve.
- **§2.4 display:** "You may not surface Map Data … without displaying the corresponding Apple map … (e.g., if You surface an address result … You must display the corresponding map with the address result)." Whether this covers a list screen such as visit history is *Ambiguous, leaning yes*.

## 4. Google Places API (New)

### Fields and pricing (published October 2026)

| SKU | Includes | Price per 1,000 | Free per month |
|---|---|---|---|
| Nearby Search Pro | `primaryType`, location, display name | $32 | 5,000 |
| Nearby Search Enterprise | adds `rating`, `userRatingCount`, `regularOpeningHours`, `currentOpeningHours`, `priceLevel` | $35 | 1,000 |
| Nearby Search Enterprise + Atmosphere | adds atmosphere fields (e.g. delivery, takeout) | $40 | 1,000 |
| Place Details Essentials / Pro / Enterprise | ID-level / display fields / rating and hours | $5 / $17 / $20 | 10,000 / 5,000 / 1,000 |
| ID-only SKUs | `place_id` | Free | Unlimited |

The most expensive requested field sets the SKU for the whole request, so field masks must be explicit. Nearby Search returns at most 20 results per request.

### Terms

- **Storage:** `place_id` may be stored indefinitely. Latitude/longitude may be cached for up to 30 days. Everything else falls under ToS §3.2.3(a)–(b): no pre-fetching, indexing, storing, or caching of Google Maps Content, including copying "business names, addresses."
- **Use with a non-Google map: prohibited.** ToS §3.2.3(e): "Customer will not use the Google Maps Core Services with or near a non-Google Map … For example, Customer will not (i) display or use Places content on a non-Google Map … or (iii) link a Google Map to non-Google Maps Content or a non-Google Map." Service Specific Terms §14.2: "Customer must not use Google Maps Content from the Places API in conjunction with a non-Google map."
- **Mapless use: allowed.** Service Specific Terms §14.1: Places content may be used "without a corresponding Google Map."
- **Ranking and filtering without display: Ambiguous.** Attribution duties apply when content is displayed, but ToS §3.2.3(c) ("will not create content based on Google Maps Content") and §3.2.3(g) ("will not modify any of the Google Maps Core Services' search results") are not defined for filtering and re-ranking.
- **Derived values: Ambiguous, leaning prohibited.** No explicit derived-data exception exists. A cuisine bucket computed from `primaryType`, or a stored score that approximately reveals a rating, should be recomputed per request and not stored.
- **Places UI Kit any-map exception.** Service Specific Terms §15.1 lets Places UI Kit render "with or without any map, including a non-Google Map." The exception covers only the UI Kit component (with Google attribution), not server-side ranking. UI Kit ships as native SDKs; Expo would need a custom native module. Places UI Kit Query: 10,000 free per month, then $1.00 per 1,000.

### Consequence for Nosh

A design that ranks with Google data and then shows the chosen place on an Apple map, or hands off to Apple Maps, is "use in conjunction with a non-Google map" even if Apple's name and address are substituted. Phase one therefore uses Google end to end: a Google map on the card, Google attribution, and a Google Maps handoff (D021). Only `place_id` is persisted (D022).

## 5. Foursquare Places API

- **Pricing:** 500 free Pro calls per month (the "10,000 free" banner on the pricing page is stale; the price table and the June 1, 2026 change notice say 500). Pro $15.00 per 1,000; Premium $18.75 per 1,000 with no free band. Requesting any Premium field (rating, stats, hours, price, popularity) bills the whole call at Premium. Auto-recharge has a $20 minimum.
- **Co-mingling: the blocking issue.** Master Terms §7.5.7 prohibits users who "co-mingle any ranking and/or signal information obtained from the Foursquare Service" with their own or third-party signals. The AUP (§IV) prohibits combining, blending, or commingling datasets with Foursquare data. Ranking on Foursquare ratings together with Nosh's learned preferences fits this wording. §7.5.8 (no use "to develop or improve any point-of-interest or venue dataset") could also reach a stored Foursquare-to-Apple ID crosswalk.
- **Storage:** `fsq_place_id` may be cached indefinitely; other fields may not be cached on pay-as-you-go.
- **`chains`:** "an array, possibly empty, of chains"; Foursquare states "there is no hard-and-fast definition of a chain," covering both small local chains and national brands.
- **Unverified:** several Foursquare developer pages (usage guidelines, Visual Crediting Policy, billing) returned 404 during research.

## 6. Yelp and Overture

- **Yelp Places API:** no free tier; Base plan $229/month plus $5.91 per 1,000; 30-day, 5,000-call trial. Plan-by-field matrix and official caching terms were not verified.
- **Overture Places:** has `brand` (`brand.names`, `brand.wikidata`), `confidence`, `operating_status`, categories, websites, phones. No rating, review count, or opening hours. `operating_status` is not "open now."

## 7. iOS location without background permission

| Path | With "When In Use" only |
|---|---|
| User taps a notification that opens the app | Yes — the app is in the foreground. A terminated app is never relaunched for location updates. |
| WidgetKit widget | Yes, with conditions: `NSWidgetWantsLocation` in the widget Info.plist, user extends permission ("While Using the App or Widgets"), check `isAuthorizedForWidgetUpdates`; location arrives briefly while the widget is visible. Expo support via `@bacons/apple-targets` is experimental. |
| Notification service or content extension | No documented support. The Location Push Service Extension needs Always permission and a special entitlement. |
| App Intents / Live Activities | An intent that opens the app gets foreground location. Live Activity location techniques are unofficial and conflict with D010/D017 — avoid. |

Consequence: notifications are location-free nudges, and the suggestion is generated after the user opens the app (D023).

## 8. Not verified

- A documented MapKit search result limit; whether Apple Maps Server API search returns category, phone, or URL.
- Whether Google's §3.2.3(g) "modify search results" covers filtering and re-ranking.
- Whether storing derived scores is allowed by Google, Apple, or Foursquare.
- Whether Apple's §2.4 applies to list screens.
- Which Places UI Kit SKU a details render bills under.
- Foursquare's current usage guidelines and crediting policy (pages unavailable).
- Yelp's field-by-plan matrix and caching terms.

## 9. Sources

- Apple: [MKMapItem](https://developer.apple.com/documentation/mapkit/mkmapitem), [Place IDs](https://developer.apple.com/documentation/mapkit/identifying-unique-locations-with-place-ids), [Apple Developer Program License Agreement (Attachment 6)](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/), [Apple Maps Server API](https://developer.apple.com/documentation/applemapsserverapi), [Server API search](https://developer.apple.com/documentation/applemapsserverapi/-v1-search), [Location authorization](https://developer.apple.com/documentation/corelocation/requesting-authorization-to-use-location-services), [Location in widgets](https://developer.apple.com/documentation/widgetkit/accessing-location-information-in-widgets)
- Google: [Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms), [Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms), [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies), [Pricing](https://developers.google.com/maps/billing-and-pricing/pricing), [Data fields](https://developers.google.com/maps/documentation/places/web-service/data-fields), [Places UI Kit (iOS)](https://developers.google.com/maps/documentation/places/ios-sdk/places-ui-kit-overview)
- Foursquare: [Pricing](https://foursquare.com/pricing/), [Upcoming changes](https://docs.foursquare.com/developer/reference/upcoming-changes), [Master Terms](https://foursquare.com/legal/terms/developermasterterms/), [Places API EULA](https://foursquare.com/legal/terms/apilicenseagreement/), [AUP](https://foursquare.com/legal/terms/aup/), [Response fields](https://docs.foursquare.com/fsq-developers-places/reference/response-fields), [Data schema](https://docs.foursquare.com/places/docs/flat-file-data-schema)
- Yelp: [Pricing](https://business.yelp.com/data/resources/pricing/), [Places API intro](https://docs.developer.yelp.com/docs/fusion-intro)
- Overture: [Place schema](https://docs.overturemaps.org/schema/reference/places/place/)
- Expo / Apple SDK requirement: [App Store Connect minimum SDK 26](https://expo.dev/blog/app-store-connect-minimum-sdk-26), [Apple upcoming requirements](https://developer.apple.com/news/upcoming-requirements/), [Expo SDK 57](https://expo.dev/changelog/sdk-57)
