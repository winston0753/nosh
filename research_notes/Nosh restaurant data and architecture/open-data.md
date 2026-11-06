# Overture and alternative restaurant data sources for Nosh

Research checked 2026-10-16. Scope: official documentation and published licenses, plus Nosh's PRODUCT.md, DECISIONS.md, ARCHITECTURE.md, and RECOMMENDATIONS.md. No restaurant extract, local coverage benchmark, provider signup, or production import was performed. Recommendations below are proposals, not implementation changes or empirical coverage findings.

## What can Overture actually supply?

### Takeaway

Overture Places is a promising durable restaurant identity and factual-information source. It is not a source of consumer restaurant ratings. Use it to assemble a small reviewed catalog, with Nosh-owned IDs and explicit unknown values, before considering a separate licensed ratings product.

### Cited Findings

- The current Place schema includes point geometry, names, addresses, taxonomy, basic category, websites/socials/phones, brand, sources, confidence, and operating status. Fields are largely optional. It has no consumer rating, review-count, opening-hours, or price field. Operating status describes continued operation, temporary hiatus, or permanent closure; it does not mean open at the current time. Confidence concerns existence, not whether food is good. — [Current Place schema](https://docs.overturemaps.org/schema/reference/places/place/)
- As checked, the current release is `2026-09-23.1`, published September 25, using schema `v2.0.0`. October 21 is a proposed future release. Releases are monthly; breaking schema changes have quarterly windows. Public data releases are retained for at most 60 days, while published changelogs and bridge files remain available. — [Release calendar and retention](https://docs.overturemaps.org/release-calendar/)
- The September guide says `categories` was removed in September 2026; current ingestion should use `taxonomy` and `basic_category`. It also explicitly acknowledges duplicates, junk records, and incomplete properties. Confidence is a relative filtering signal, not calibrated across providers. Matching promotes one provider's record rather than merging every provider's attributes. — [Places guide](https://docs.overturemaps.org/guides/places/)
- Taxonomy contains primary category, hierarchy, and alternatives; a restaurant subclass can roll up through the hierarchy. The separate July taxonomy page still describes a transition period in which the old field coexists. Prefer the current v2 schema and September guide over that older transition text. — [Taxonomy page, July update](https://docs.overturemaps.org/guides/places/taxonomy/), [Place v2 schema](https://docs.overturemaps.org/schema/reference/places/place/)
- Overture documents downloading spatial subsets using DuckDB with spatial/HTTP extensions and querying cloud-hosted Parquet; a full-world download is unnecessary. — [DuckDB access](https://docs.overturemaps.org/getting-data/duckdb/)

### Inferences

- A missing cuisine is an ingestion-review issue: Nosh's eligibility requires normalized cuisine. A generic `restaurant` category must not be mistaken for a cuisine or silently dropped. Map supported categories deterministically to Nosh cuisines, keep raw categories, and put ambiguous records in a review queue.
- Check the whole food taxonomy against the product boundary. Restricting to a literal primary string ending in `restaurant` can miss eligible casual eateries, while importing all food/drink can admit groceries, bars, or non-meal businesses.
- Store source confidence as `existence_confidence`, separate from `quality_score`. Do not feed it into Nosh's 45%-weighted quality component. Keep missing dining quality neutral (currently 0.5), or apply a documented editorial quality prior only when backed by actual editorial judgment. Verifying an address is not an editorial judgment that the restaurant is good.
- Monthly open-data refresh plus manual closure corrections fits the pilot. It does not create real-time opening-hours guarantees, which PRODUCT.md already excludes.
- Release retention means reproducibility should store the permitted input subset, manifest, transform version, and candidate snapshots locally under an appropriate retention policy. The provider's 60-day public hosting limit is not itself a license ban on storing the data; do not confuse these concepts.

### Gaps

- No measured SF Mission restaurant recall, false-positive rate, coordinate accuracy, duplicate rate, or cuisine completeness. Global counts cannot establish suitability for the two intended neighborhoods.
- No import runtime/storage estimate was measured. Local extraction and review effort may be more important than compute cost.

## Can the catalog be retained and used offline?

### Takeaway

The open licenses are compatible with storing a durable catalog and rendering an offline card, subject to their notices. License by source and release, not by a blanket “Overture” label. Do not transfer the permissions for open data to a commercial API's richer fields.

### Cited Findings

- Current attribution identifies Meta, Microsoft, PinMeTo, Krick, RenderSEO, DAC, and BrightQuery Places under CDLA Permissive 2.0, and Foursquare under Apache 2.0 with a NOTICE file. — [Overture attribution](https://docs.overturemaps.org/attribution/)
- The newer September Places guide additionally lists AllThePlaces under CC0, and states that Places contains no OpenStreetMap data and no ODbL share-alike obligation. This differs from other Overture themes and from older assumptions about Overture generally. The attribution page and guide are not completely synchronized; record actual release sources. — [Places guide](https://docs.overturemaps.org/guides/places/)
- CDLA permits use, modification, and sharing; sharing data requires making the license text available with it. Exact relevant phrase: “makes available the text of this agreement with the shared Data.” — [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/)
- Foursquare's NOTICE requires providing the Apache license, marking modifications where applicable, and preserving attribution/NOTICE. Exact phrase: “preserve attribution to Foursquare, including preserving the full content of this NOTICE.txt file.” It recommends the NOTICE in developer documentation for API-form distribution. — [Foursquare OS Places NOTICE](https://opensource.foursquare.com/places-notice-txt/)
- OSM allows reuse subject to credit and ODbL, with share-alike obligations for derivative databases. Its copyright page requires attribution and making clear that data is available under ODbL. Exact phrase: “Provide credit to OpenStreetMap by displaying our attribution notice.” — [OSM copyright](https://www.openstreetmap.org/copyright)

### Inferences

- Preserve `provider`, provider record ID, release ID, schema version, upstream `sources`, source timestamp, fetched timestamp, license identifier, license/NOTICE version, and import batch. For each canonical field, record whether it came from the source or a manual override. A compact source snapshot plus override metadata is sufficient for this pilot; a universal provenance platform is unnecessary.
- Nosh's license screen could say “Place data: Overture Maps Foundation and its contributors,” followed by the applicable CDLA text and Foursquare Apache license/NOTICE with a transformation notice. That is a proposed implementation, not a statement that this one sentence alone satisfies every license. Expose the same notices with shared data/API documentation where applicable.
- Keep the offline suggestion payload restricted to fields whose retention/display rights were recorded. Open-data restaurant name/address/coordinates/cuisine can be part of that cache; a future commercial photo, star rating, or review cannot inherit those rights merely because it is attached to the same Nosh place.
- OSM can be useful, but introducing it into the canonical database adds derivative-database/share-alike analysis. Separate tables are operationally useful but are not by themselves a legal exemption. For this small pilot, use Overture plus independent curation first, and add OSM only if measured incremental value justifies the obligations.

### Gaps

- This is an engineering interpretation of published terms, not confirmation of a negotiated contract. No custom provider agreement has been reviewed.
- Preserve release-specific license evidence because official pages can lag each other or change. Source metadata fields may be null, so a reviewed license registry per provider/release is needed rather than relying exclusively on each record's optional `sources.license` value.

## How should IDs, updates, and duplicates work?

### Takeaway

Retain the existing Nosh UUID as the canonical identity. GERS and other provider IDs belong in crosswalks; they are useful but cannot replace Nosh's identity and visit-history continuity.

### Cited Findings

- GERS commits to stable IDs for Places, but name changes, sufficiently large moves, and splits/merges can change identifiers. General old-to-new mappings for split/merge are not published. Removed IDs therefore require rematching. All IDs changed to UUIDs in the June 2025 switchover, with a one-off crosswalk. — [GERS ID stability](https://docs.overturemaps.org/gers/stability/)
- Changelog values distinguish additions/removals/changed/unchanged records. Removal does not prove closure: it can represent source removal or merging. `sources` and `confidence` are excluded from change detection, so an unchanged row can have changed provenance/confidence. — [Data changelog](https://docs.overturemaps.org/gers/changelog/)
- Places bridge files cover all included source providers and map source IDs to GERS IDs. A GERS ID can have multiple source rows. Since August 2026, bridge files partition by `provider`, replacing older `dataset` partition paths. — [Bridge files](https://docs.overturemaps.org/gers/bridge-files/)

### Inferences

- Start with exact `(provider, provider_place_id)` matches. For genuinely new source records, generate conservative match candidates using nearby location plus normalized name, street address, phone, and website. Resolve uncertain branch/multi-tenant matches manually. Proximity alone must never merge neighboring restaurants.
- Keep aliases/retired source IDs so visited exclusions survive provider merges and renames. A new business replacing an old business at the same address should be a new Nosh place; a rename should preserve history if continuity is verified. Make those product identity rules explicit.
- Refresh a small complete neighborhood extract monthly. For a pilot this is simpler than elaborate global delta processing and catches source/confidence changes omitted from the changelog. Compare it with the previous allowed snapshot; stage changes before applying.
- A missing source row becomes `needs_review`/stale, not automatically permanently closed. A credible explicit closure can deactivate future recommendations while retaining historical visits and proposals.
- Manual corrected fields should survive later provider refreshes until a reviewer removes the override. Use one transaction per reviewed import batch and a reversible batch audit, not destructive database resets.

### Gaps

- Neither provider identity matching nor a GERS join guarantees no duplicates. The pipeline needs deliberate duplicate-review tests using same-name chain branches, nearby different businesses, restaurant replacement, rename, move, provider disappearance, and return.

## Is Foursquare, OSM, or another source better?

### Takeaway

Foursquare OS Places is the strongest alternative to benchmark against Overture, not an automatically superior source. Overture already includes some Foursquare data, so compare incremental coverage and completeness before paying the cost of a second pipeline. Commercial Foursquare is a plausible later route to licensed richer attributes, with explicit contract review.

### Cited Findings

- Foursquare OS schema includes identity, coordinates, address, categories, contact/socials, and record-created/refreshed/closed dates. The refresh date means any one reference was refreshed, not all fields verified; created/closed dates are database events, not guaranteed business opening/closure dates. Deltas include merge and a surviving-ID redirect. Consumer ratings, hours, and price are absent from the OS schema. — [Foursquare OS schema](https://docs.foursquare.com/data-products/docs/places-os-data-schema)
- Current direct OS access uses a Places Portal account and token with an Iceberg catalog; the legacy public S3 delivery has been deprecated. The official page links alternative Hugging Face/Snowflake offerings. — [Access FSQ OS Places](https://docs.foursquare.com/data-products/docs/access-fsq-os-places)
- The September 2026 release notes show continuing monthly changes and deletions/merges. Do not assume an old public-bucket example is the current access path. — [Foursquare OS release notes](https://docs.foursquare.com/data-products/docs/fsq-os-places-release-notes)
- Foursquare's separate Pro/Premium schema includes hours, price, a consumer rating on a 0–10 scale, and a `veracity_rating` for completeness/currentness/reliability. The latter is not dining quality. — [Foursquare Pro/Premium schema](https://docs.foursquare.com/data-products/docs/places-pro-and-premium)
- Foursquare offers commercial flat-file packages with richer attributes, including ratings/hours, and delivery cadence options. No public price or durable-use permission for Nosh's particular rating use was established in this research. — [Commercial flat-file offering](https://docs.foursquare.com/data-products/docs/places-flat-file-overview)
- OSM restaurant tagging supports names, cuisine, hours, contact/address and other optional attributes, with separate tags for restaurants, cafes, and fast food. It is not a consumer-star-review corpus. — [OSM restaurant tagging](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Drestaurant)
- OSM directs bulk users to extracts and read-only alternatives such as Overpass rather than treating the editing API as a production POI backend. — [OSM API policy](https://operations.osmfoundation.org/policies/api/)
- Yelp's official Places FAQ allows content caching up to 24 hours and indefinite business-ID storage, and says analysis is not permitted for Places integrations. This is a poor default for a permanent ratings corpus and stored scoring snapshots. — [Yelp FAQ](https://docs.developer.yelp.com/docs/places-faq)
- The well-known SF restaurant LIVES dataset is historical (2016–2019), explicitly no longer updated. It points users to a newer inspections dataset; its old inspection scores cannot serve as present dining ratings. — [DataSF historical inspection dataset](https://data.sfgov.org/Health-and-Social-Services/Restaurant-Scores-LIVES-Standard/pyih-qa8i?row_index=0)

### Inferences

- Direct Foursquare may improve coverage, fields, source dates, or identity redirects, but measure unique reviewed restaurants added beyond Overture. Its OS data and Overture must not count as two independent votes for the same restaurant when they share an upstream record. Bridge files can reduce duplicate work.
- Don't average provider stars into one number. A Foursquare 0–10 derived score, a five-star consumer average, a veracity score, an editorial prior, and a Nosh positive visit are different signals. If later licensed, retain scale, count where meaningful, source, timestamp, and method; calibrate separately and version any policy using them.
- Restaurant-owned sites and direct owner confirmation are practical sources of missing cuisine, address, and hours for a small review set. Record the URL/date and permission context, use factual verification, and avoid importing text/photos/reviews wholesale. Do not build a broad crawler or infer durable rights from public visibility.
- Prefer first-party confirmed positives for Nosh's product learning, which already matches the North Star. Missing external stars should not block external testing once the catalog is reviewed and operationally usable.
- A commercial provider should explicitly authorize permanent server storage, offline client display, derived ranking, candidate/score snapshots, Apple Maps handoff, refresh/expiry behavior, deletion, and attribution before using its ratings in this architecture. Buy a dataset license if that is the desired usage; an inexpensive request price is not a storage license.

### Gaps

- No source was measured as better in SF. Overture's Foursquare subset is not established as the entire direct Foursquare dataset.
- Foursquare Personalization API retention rules were found, but they refer to that product. Do not apply them uncritically to the current Places API or OS dataset. A durable rich-data agreement remains unverified.
- The newer SF inspection URL redirected to a page labeled 2024–Present but yielded no substantive table in the web tool. Its current fields, completeness, and license were not verified; therefore it is only a possible audit source, not a recommended new import dependency.
- No Tripadvisor contract or dataset evaluation was performed; it did not emerge as a better immediate fit than the curated/open-data approach.

## What should Nosh do next, and what would make the decision evidence-based?

### Takeaway

Proceed with the existing accepted D008 strategy: a real, small, reviewed neighborhood catalog. Use Overture to reduce manual enumeration, evaluate Foursquare only for incremental value, retain neutral quality until there is real evidence, and keep provider calls out of meal-time ranking.

### Cited Findings

- Nosh's PRODUCT F4 explicitly requires a small reviewed dataset and tolerance for absent rating/hours/photo/menu data. D008 accepts curated data first. RECOMMENDATIONS.md permits neutral quality defaults. The current architecture already has Nosh place UUIDs and provider crosswalks. — Local canonical files: `/Users/winstontang/Downloads/nosh/PRODUCT.md`, `DECISIONS.md`, `RECOMMENDATIONS.md`, `ARCHITECTURE.md`.
- The coordinator's repository review reports 20 fictional fixtures, an insert-only loader, and no provider-refresh/closure workflow. Treat this as repository-review input, not a fresh independent code inspection in this note.

### Inferences

Proposed bounded pilot, deliberately not a new nationwide ingestion system:

1. Fix two public neighborhood areas and representative contexts/radii. Define eligible restaurants, cafes, bars-with-food, counter-service venues, and exclusions before extraction. Do not send private home/work coordinates to source services; extract the public area once.
2. Download a release-pinned Overture Places subset with DuckDB; retain source and license manifest. Optional separate Foursquare subset is a benchmark, not an assumed mandatory second production source.
3. Normalize names/addresses and map taxonomy through a versioned deterministic table. Validate coordinates, required card fields, IDs, and source dates. Unknown cuisine/status/identity should produce an explicit review reason.
4. Build a small independent review list from actual neighborhood knowledge, direct restaurant verification and observed venues. Review all proposed pilot entries if the catalog is only about 100–200 places; otherwise stratify by neighborhood, cuisine, source, confidence band, chains/independents, and recent change. The 100–200 range is an effort estimate, not a count or success benchmark.
5. Measure source precision (eligible real restaurants / inspected source records), recall against the independent list, duplicate rate, missing-card-field and missing-cuisine rates, location error/Maps handoff correctness, stale/closed rate, and overlap/incremental unique coverage. Review a sample of missing/low-confidence records so a high confidence threshold does not silently erase smaller restaurants.
6. Approve only reviewed rows into the existing PostGIS catalog. Use source timestamp plus `verified_at`, correction reason, and reviewer/batch metadata. Keep editorial verification separate from a subjective quality prior and from user visits.
7. Run idempotent imports and monthly refresh dry-runs; review source deletions/renames/moves. Add an administrative deactivation/correction path. No Kafka, distributed ETL, pgvector, LLM classifier, or meal-time provider call is necessary.

Proposed pilot acceptance gates (product choices to agree, not measured results): all active rows have verified name, navigable location/address and normalized cuisine; no known duplicate or closed recommendations; all source licenses/notices are represented; imports can be retried without duplicating places or changing history; a refresh handles merge, missing source, rename and manual override safely. Each tester context should retain enough unvisited eligible supply for several weeks plus Another choices; set the count using chosen schedule and expected sessions, not a universal global completeness percentage. Suppress neighborhood-completion percentages unless the denominator is actually credible.

The main decision rule: choose the cheapest-to-maintain combination that passes these neighborhood gates. If Overture plus small manual corrections passes, do not add another source. If it misses many important local venues, direct Foursquare or independently collected entries can fill measured gaps. If the pilot demonstrates poor quality outcomes even with correct places, then evaluate a licensed consumer-rating source against Nosh's actual positive-visit outcomes.

### Gaps

- No acceptance gate is claimed passed. No source cost/coverage benchmark was run and no provider license was purchased. Open data avoids per-call licensing charges for its data, but curation, storage, compute, updates, and support remain real costs; no dollar budget has been fabricated.
