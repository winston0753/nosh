# Grounding dish recommendations in nearby places

November 1, 2026. Scope: dish recommendation, acceptance, nearby restaurant suggestion and map location; automatic delivery removed. Strategy research only.

## Can ChatGPT or Claude supply location and current restaurant knowledge?

### Takeaway
Their APIs can search the live web with supplied approximate location, substantially reducing manual lookup work. This is not automatic access to the iPhone's GPS, nor a guaranteed menu/restaurant database.

### Cited Findings
- OpenAI's web-search API accepts approximate country, city, region and timezone. Search responses include source annotations, and end-user displays must preserve visible, clickable citations. Search actions have tool-call costs. Responses API web search is an explicitly configured tool; the model can decide whether to invoke it. [Official OpenAI web-search documentation](https://developers.openai.com/api/docs/guides/tools-web-search)
- Claude's web-search API likewise accepts `user_location` with type `approximate` and city/region/country/timezone. It supports source citations, domain controls and search-use limits. These are search-localization inputs, not a device-location endpoint. [Claude web-search documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- Claude also supplies a separate tool for fetching page contents from specified URLs. Search discovery and reading a restaurant's actual menu can therefore be separate steps. [Claude web-fetch documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool)

### Inferences
- A Nosh app should call a supported API with tools enabled, not assume that wrapping a consumer ChatGPT/Claude chat grants that product's complete tool stack, account context or location behavior.
- Nosh still obtains foreground location with permission, or asks the user for an area/fallback spot. City-level web localization is insufficient to enforce a short walking radius. A backend's network location is not reliable evidence of the user's location.
- Model-only recall is appropriate for proposing dish concepts or synonyms, but weak evidence that a particular business currently exists, is the correct branch, or serves the dish. A cited search result improves traceability; it does not prove the cited page is current or that its statement supports the recommendation.
- Prefer sending only the area needed for web search. Keep precise coordinates out of general prompts and logs; supply them transiently only to a location service when needed. This is a proposed privacy design, not a claim that all providers automatically redact them.

### Gaps
- No user-device location flow or actual API was tested. No evidence establishes that consumer product behavior transfers unchanged to an API integration.
- There is no measured comparison of Claude versus OpenAI on SF dish-to-branch accuracy, cost, or latency. Do not choose a vendor based on an unsupported accuracy claim.

## What does a reliable restaurant lookup still need?

### Takeaway
Use models for food interpretation and evidence extraction; use live place records for establishment identity and map handoff. Require branch-specific menu evidence before presenting a dish as listed there.

### Cited Findings
- Google Places Text Search accepts food queries and returns Place objects. It supports location bias, rectangular restriction for categorical queries, field masks and `openNow`. A bias may return results outside its area; it is not a strict radius. Identical requests need not return identical results. [Google Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search)
- Google Maps URLs can show a place or launch directions. Google recommends a place ID when definitively linking to a particular establishment, avoiding the ambiguity of names alone. [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started)
- Google permits indefinite storage of place IDs while restricting caching of other Places content and requiring appropriate attribution. [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- Maps terms restrict scraping and creating content from Maps content, and specifically prohibit using that content to improve/train/test/validate/fine-tune ML/AI models. Feeding provider results to a model does not confer ownership of resulting labels or an unrestricted right to persist them. [Google Maps Platform terms, section 3.2.3](https://cloud.google.com/maps-platform/terms)

### Inferences
- Suggested flow: accepted dish concept → localized search candidates → resolve exact branch/place ID → inspect that branch's official menu where accessible → apply location/opening/budget checks → show one recommendation with honest evidence and map link. Absence of usable evidence should produce an uncertain candidate or another option, not fabricated certainty.
- Keep three claims distinct: **place found** (identity/address resolved); **dish listed** (branch-specific menu explicitly lists it, source inspected at a stated time); **available now** (only if there is actual current merchant evidence). A page checked today can itself be an old menu. Do not call inspection time a menu update time.
- A chain's generic menu, a review from years ago, a similarly named dish, a closed former location, or an article naming a different branch can all create plausible but wrong matches. Prefer independently accessible official merchant pages; still check branch and menu period.
- Use evidence categories and measured error rates, not an LLM's self-reported confidence score. Retain URLs/provenance only where rights permit; keep Google's IDs-only boundary and avoid retaining Google-derived menu labels, summaries or embeddings as Nosh-owned data.
- An even leaner experiment could send the accepted dish and chosen area to a Google Maps search. That delegates restaurant selection to Maps and needs less integration, but does not fulfill the stronger promise that Nosh itself selected one verified restaurant.

### Gaps
- Official API docs describe capabilities, not complete dish coverage or freshness guarantees. A local pilot must measure false positives, missing results and branch errors.
- Access to a public menu does not automatically establish unrestricted storage or redistribution rights; rights should be checked for each source before durable ingestion.

## Does the revised scope avoid maintaining a restaurant database?

### Takeaway
Yes: a no-delivery, live-lookup discovery product can avoid maintaining its own comprehensive restaurant catalog. It still needs a lightweight record of user intent, dish concepts, selected place IDs and outcomes, plus verification logic.

### Cited Findings
- Live localized search and stable place links exist as documented capabilities. They support an architecture that resolves restaurants on demand rather than copying a comprehensive catalog. [Google Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search), [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started)

### Inferences
- Compared with the previous automatic-delivery proposal, removing checkout, payment, courier integration and order-state handling materially simplifies feasibility. The remaining uncertainty is recommendation truthfulness, not fulfillment logistics.
- Compare against Nosh's actual accepted baseline: it already replaces its curated catalog with live Google Places. The new advantage is a dish-first experience and taste data, rather than newly eliminating a restaurant database.
- Three implementation strategies: model recall alone has lowest integration but inadequate current evidence; live web search with cited merchant evidence is viable for an early trial but variable in coverage; models plus Places and branch-specific merchant evidence provide clearer identity and location control while adding calls and integration work. None requires a proprietary worldwide restaurant catalog.
- Each additional search/fetch/verification step adds potential cost and waiting. Bound lookup work, show progress, and fail gracefully. No dollar or latency estimate is warranted without actual traces; measure cost per successful grounded recommendation and user-visible delay.
- Begin with a few dishes and one area, inspect results manually, record “place exists,” “right branch,” “dish listed,” “menu date known,” “within requested area,” and actual user outcome. An acceptance is intent, not proof of a meal or liking. This evaluates whether the simpler concept works before building a global ontology.

### Gaps
- No implementation or production policy change is authorized by this research. Nosh's current deterministic/no-LLM mealtime rule would require an explicit recorded decision before adopting runtime model search.
