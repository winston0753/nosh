# Forage

*Working name.* A proactive restaurant-exploration app: at lunch and dinner it suggests a nearby restaurant you haven't tried, in a cuisine you're likely to say yes to, and hands off to directions or ordering. Goal: try as many good neighborhood restaurants as possible.

**Status: pre-design.** This repo currently holds the product pressure test and one validation spike. No app code yet.

## Read first

1. [docs/01-product-brief.md](docs/01-product-brief.md) — what works, what doesn't, fixes, where AI is load-bearing, phased scope
2. [docs/02-open-questions.md](docs/02-open-questions.md) — questions to settle before design
3. [docs/03-learning-map.md](docs/03-learning-map.md) — what each part teaches (product, SWE, agents/RAG, evals)
4. [docs/decisions/](docs/decisions/) — architecture decision records (ADRs)

## Spike: cuisine-selection policy simulation

Tests whether "propose the cuisine with the lowest been-to %" is a good way to maximize new restaurants tried. It isn't: it does worse than random, because low been-to % is confounded with low taste. A policy that learns from rejections (Thompson sampling × size of the unvisited pool) does best.

```bash
uv sync
uv run pytest -q
uv run python -m spike.cuisine_policy_sim --users 500            # with churn
uv run python -m spike.cuisine_policy_sim --users 500 --no-churn
```

| Policy (no churn, 500 users, 90 days) | New restaurants | Rejections / session |
|---|---|---|
| lowest been-to % (spec) | 64.3 | 1.64 |
| random | 76.1 | 1.08 |
| Thompson + history prior | 80.5 | 0.87 |
| oracle (upper bound) | 82.0 | 0.81 |

All assumptions are fields on `SimConfig` in [spike/cuisine_policy_sim.py](spike/cuisine_policy_sim.py).

## Layout

```
docs/                 brief, open questions, learning map, ADRs
spike/                throwaway experiments that answer one question each
tests/                pytest; policy invariants and simulator sanity checks
```

Planned once design starts: `api/` (FastAPI), `ingest/` (places pipeline), `agent/`, `evals/`, `ios/`.
