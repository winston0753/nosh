# Learning map

What each part of Nosh teaches, and how it lines up with the build sequence on your AI-engineering roadmap.

## Product development

| Skill | Where it shows up here |
|---|---|
| Problem framing | Separating the *objective* (new good restaurants) from the *proxy* (been-to %) — the core lesson of the simulation |
| North Star + guardrail metrics | New 👍 restaurants / month; guardrails: rejections per session, notification mute rate |
| Funnel thinking | Nudge → open → accept cuisine → accept place → go/order → confirm. Measure drop-off per step |
| Cold start | Onboarding swipe gives history and a taste prior on day one |
| Ground truth design | Turning "did they actually eat there?" into a one-tap confirmation that also yields a rating |
| Decision records | `docs/decisions/` — write down *why*, not just what |
| Dogfooding → TestFlight → store | Evidence gates between phases |

## Software engineering

| Skill | Where it shows up here |
|---|---|
| Data modeling | Places, cuisines (many-to-many), visits, proposals/responses (event log), users, neighborhoods |
| Ingestion pipeline | FSQ OS Places parquet → filter by area → normalize → Postgres; monthly refresh, handle closures |
| Licensing-aware caching | What you may store (FSQ, place IDs) vs. must fetch live (Google display fields) |
| Scheduling and background work | Precompute the next suggestion before the meal window; local notifications on device |
| API design | FastAPI + Pydantic; idempotent event endpoints (offline phone → retries) |
| Testing | Unit tests on policy invariants (already in `tests/`), simulator as a regression test in CI |
| iOS | Notification categories + actions, deep links / universal links, location permissions |

## Agentic systems and RAG — roadmap build sequence

| Roadmap step | Nosh version |
|---|---|
| 1. Agent loop from raw API calls, no framework | Concierge agent with tools: `search_places`, `get_history`, `log_meal`, `free_slots(calendar)`. Hand-roll the loop, retries, and tool-error handling |
| 2. MCP server for a tool you use | Expose your food history + restaurant universe as an MCP server; ask Claude "where haven't I been near the office that's open now?" |
| 3. Tracing + eval harness, then LangGraph and compare | Langfuse on every LLM call; evals per the table in the brief; rebuild the concierge in LangGraph using `interrupt()` for your yes/no turns; compare code size, latency, failure handling |
| 4. Deploy with Docker + CI | Containerized API, GitHub Actions running tests + simulator + eval suite on every PR |

Retrieval fundamentals you'll touch: chunking menus/reviews, hybrid search (BM25 + pgvector), reranking, recall@k / nDCG on a labeled craving set.

Agent security you'll touch: prompt injection via restaurant descriptions and reviews (untrusted text inside your retrieval corpus), tool permissions (the agent may read your calendar but never place orders).

## Evals — lean into the stats edge

- **Offline policy evaluation:** the simulator, with paired comparisons on common users and confidence intervals (started in `spike/`).
- **Sample sizes:** how many labeled cravings you need for recall@10 to have a useful CI.
- **Judge calibration:** hand-label ~50 explanations, measure LLM-judge agreement before trusting it.
- **Online:** TestFlight A/B on notification design; pre-register the metric.

## Resume line this earns (if phases 1–2 ship)

> Built a proactive restaurant-exploration agent: bandit cuisine policy (+25% new restaurants vs. coverage heuristic in simulation, paired 95% CI); hybrid-search RAG for free-text cravings (recall@10 = X); MCP server over personal meal history; Langfuse tracing and an eval suite running in CI.

(The +25% is the no-churn simulation result: 80.5 vs 64.3. Replace X with your measured number.)
