# 0001 — Deterministic decision core, LLM at the edges

- **Status:** Proposed
- **Date:** 2026-10-11

## Context

The core flow (nudge → cuisine → restaurant → go/order) is a state machine with a recommendation policy. It runs at a fixed moment (meal time) on a phone, where latency and reliability matter. The project also has a goal of demonstrating RAG, agents, tracing and evals, which creates a temptation to route every step through an LLM.

## Decision

The meal-time decision (which cuisine, which restaurant, when to nudge) is computed by deterministic code and a learned policy, precomputed before the meal window. LLMs are used only where the input or output is natural language: craving search (RAG), taxonomy normalization, meal logging, explanations, and the conversational concierge.

## Consequences

- Notifications never wait on a model call; the core works offline and costs nothing per nudge.
- The policy is testable with ordinary unit tests and the simulator.
- Each LLM component has a narrow job and its own eval, which makes the eval suite meaningful rather than one end-to-end vibe check.
- The "agentic" part is the concierge and the tools, not the notification flow. Be explicit about this in interviews — it shows judgment.

## Alternatives considered

- **LLM-driven conversation for the whole flow:** more "agentic" on paper; adds latency, cost and nondeterminism to a yes/no flow, and is hard to evaluate.
- **No LLM at all:** simplest, but misses the genuine language problems (free-text cravings, messy categories, logging) and the learning goals.
