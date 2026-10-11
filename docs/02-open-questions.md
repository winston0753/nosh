# Open questions (answer before design)

Each question names what it blocks and the cheapest way to answer it.

| # | Question | Blocks | How to answer |
|---|---|---|---|
| 1 | **North Star:** new restaurants tried per month, or *good* new restaurants (rated 👍)? Does a bad new place count? | Objective, rating UX | Decide; write it in an ADR. Lean: count 👍 only, or the app optimizes for novelty over quality. |
| 2 | **Ground truth:** which capture methods ship in v1 (onboarding swipe, next-meal confirm, quick log)? | Data model, onboarding | Phase-0 diary: how often would you actually confirm? |
| 3 | **Neighborhoods:** office at lunch + home at dinner? Radius per mode (walk / drive / delivery)? | Data ingestion, been-to % denominator | Map both areas with FSQ OS Places; count restaurants per cuisine within 0.5 / 1 / 3 mi. |
| 4 | **Data sources and cost ceiling:** FSQ OS Places as the universe + Google Places live for the shown card? Monthly budget? | Architecture, licensing | Pull FSQ for both areas; spot-check 30 places against reality; price Google calls at expected volume. |
| 5 | **Cuisine taxonomy:** how granular? ("Chinese" vs "Sichuan / Cantonese / Taiwanese") | Been-to %, policy, LLM normalization task | Look at FSQ category labels for your areas; pick a level where each cuisine has ≥3 places. |
| 6 | **Who is user #2?** Just you, friends, or a market? | App Store, privacy, onboarding effort | Ask 5 friends whether they'd keep a daily nudge. Listen for "I'd mute it." |
| 7 | **Eating with others:** dinner with a partner or coworkers — whose history counts? | Data model | Defer to v2, but don't make the schema single-user-only. |
| 8 | **Notification design:** one decision per notification? What do Another / Not today / Snooze do exactly? | iOS work, policy signals | Paper prototype; then TestFlight A/B (cuisine-first vs place-first). |
| 9 | **Mobile stack:** native SwiftUI or Expo (React Native, TypeScript)? | Phase 3 | SwiftUI: full platform access (content extensions, App Clips, Live Activities), new language. Expo: TypeScript (on your roadmap), notification actions supported, less platform depth. Lean Expo unless you want iOS as a skill. |
| 10 | **Dietary and price constraints?** | Filtering | Decide what v1 ignores. |
| 11 | **Snooze vs. skip semantics:** are they signals about cuisine? (They shouldn't be.) | Policy | Treat as timing signals only; the simulator already does. |
