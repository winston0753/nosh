# Social dining and wishlist activation

## Is nearby shared-wishlist dining a promising first wedge?

### Takeaway
The insight is useful: saved desire often needs timing and company to become action. My recommendation is a solo-capable saved-place nudge with an optional invitation to an existing friend, then a concentrated coworker circle. An open marketplace of nearby strangers multiplies the cold-start problem instead of removing it. These are strategic judgments, not measured market outcomes.

### Cited Findings
- Timeleft asks people to choose a date and neighborhood and specify language, budget and dietary preference; it assembles a small group and books a public restaurant. Its product coordinates a committed occasion, rather than requiring all users to happen to be simultaneously hungry nearby. It includes a post-event connection flow and invitations to existing connections. — [Timeleft official how it works](https://timeleft.com/how-it-works/)
- Timeleft describes public vetted venues, groups, reporting and blocking, and moderation as parts of its social-dining experience. These are product and operations requirements for stranger dining, not restaurant-ranking features. These are the company's own descriptions, not an independent effectiveness assessment. — [Timeleft safety](https://timeleft.com/blog/safety-starts-before-the-dinner/)
- Pie already provides public, friends-only and private plans, with share links controlled by host settings, including sharing to Messages. — [Pie share plans](https://support.getpie.app/hc/en-us/articles/47745364762772-Share-Your-Plan)
- Pie notifies people about invitations, new plans, changes, reminders and RSVPs; a Maybe does not hold a place. — [Pie notifications](https://support.getpie.app/hc/en-us/articles/54013721871636-Notifications-on-Pie-What-You-ll-Get-Pinged-About)

### Inferences
- A nudge is a useful wedge, but neither notification delivery nor group coordination is intrinsically a moat. The potential advantage is repeated successful conversion of personal restaurant intent into a real outing with minimal effort.
- Nearby stranger matching requires geographic overlap, overlapping availability, acceptable budget, acceptable food, willingness to meet strangers, and reciprocal commitment. Requiring an identical saved restaurant adds another constraint. A citywide user count is less meaningful than people available in a small area during a specific meal window.
- Do not model those constraints as independent or claim a numerical match rate without observing the cohort. The qualitative conjunction alone explains the liquidity risk.
- Compare entry points: (1) solo saved-place activation has no network prerequisite; (2) friend pairs bring trust and can succeed with two users but still require scheduling; (3) coworkers have repeated proximity and meal timing but attendance varies; (4) scheduled stranger dinners aggregate demand over time but require hosting and trust operations; (5) instant nearby strangers need the most simultaneous density and trust.
- For a solo founder on a tight budget, start with the first two; use one office or coworking community as a later focused test. Do not launch all five modes together.
- Exact wishlist intersection is attractive when it exists, but should be a bonus. A practical group choice can be one person's saved place that everyone else accepts, within everyone's hard constraints. Rotate whose wish is fulfilled instead of waiting for a restaurant saved by all participants.
- The promise can be: “You already know where you want to go. Nosh helps make it happen.” That changes the unresolved question from “Will I like this restaurant?” to “Can I do this now, and with whom?”

### Gaps
- No evidence collected establishes that users' main reason for not using saved restaurants is lack of company. It could be cost, distance, occasion mismatch, reservations, companions' preferences, or merely aspirational saving.
- No reliable match-success, retention, notification-fatigue, or willingness-to-pay estimate exists for this Nosh variant yet. Competitor feature descriptions do not validate demand for Nosh.

## What would the smallest useful social flow look like?

### Takeaway
Use an explicit, expiring meal opportunity and a concrete invitation. Avoid passive proximity discovery and a permanent social feed. Keep a solo outcome useful when friends decline.

### Cited Findings
- Timeleft's explicit date/neighborhood choice illustrates how a product can gather availability before making a group. — [Timeleft how it works](https://timeleft.com/how-it-works/)
- Pie's invitation and plan-update notifications illustrate that a concrete plan already provides a meaningful notification object. — [Pie notifications](https://support.getpie.app/hc/en-us/articles/54013721871636-Notifications-on-Pie-What-You-ll-Get-Pinged-About)

### Inferences
- Proposed flow: user opens a scheduled nudge; confirms “free for lunch until 1”; foreground location or a manually chosen area identifies feasible saved places; one place is proposed; user can go solo or send “Want to try X at 12:15?” through an existing messaging app. A human-operated test can do this without building in-app chat.
- Friend invitation should initially work without requiring the recipient to install Nosh or import their history. A later lightweight web response is a product proposal, not a currently implemented capability.
- Existing friends can opt into a small private circle, but availability must expire after the meal window. Coarse area and availability are sufficient for discovery; disclose precise meeting venue only as part of the agreed plan. Do not show live maps of people or infer background movement.
- “Nearby right now” cannot be promised under foreground-only location when an app has not recently been opened. Use recent opt-in availability or a chosen meeting area, explicitly time-limited. This preserves the spirit of Nosh's no-background-location decision.
- Matching can produce a proposal before every participant has opened Nosh only if prior availability/location declarations are sufficiently fresh. Otherwise say “near your chosen lunch area,” not “near you.”
- A group visit should have per-person confirmation; one person's Go or attendance cannot establish everyone attended. Confirmation remains useful, but a positive-new-restaurant score is no longer the only plausible outcome.
- Social scope would require an explicit new decision. This analysis does not authorize implementing it or changing existing privacy assumptions.

### Gaps
- No current implementation audit of invitation links, shared lists, circles or expiring availability was performed in this research strand. Treat all as proposed capabilities.

## What alternatives and experiments reduce historical-data dependence?

### Takeaway
Test activation of intent before introducing more data collection. The strongest alternative directions are saved-place rescue, dining pairs, and a recurring small-circle lunch ritual.

### Cited Findings
- Scheduled social meals and lightweight shareable plans are established product patterns, as illustrated by the official sources above; their existence does not establish Nosh's differentiation or commercial viability. — [Timeleft](https://timeleft.com/how-it-works/); [Pie](https://support.getpie.app/hc/en-us/articles/47745364762772-Share-Your-Plan)

### Inferences
- **Saved-place rescue:** Start with three to five places a person already wants to try, not their entire dining history. Nudge when they explicitly indicate a feasible meal window. This needs intent and feasibility, not a trained taste model.
- **Dining pair:** One partner or friend, a handful of saved places, and a weekly “finally try one” slot. Test whether someone will make a firm plan rather than keep saving.
- **Lunch circle:** One office/coworking community, one designated weekday, opt in before lunch, a single proposal plus clear cutoff. A small venue or neighborhood concentrates participation; it is not a citywide matching marketplace.
- **Bring one wish:** Each group member contributes one place; rotate the person whose choice is attempted subject to budget/time constraints. This resolves low list overlap and avoids preference surveys.
- **Occasion rescue:** Ask which saved places are for quick solo lunches versus dinners with company. One lightweight occasion tag may make saving actionable without asking users to rate dozens of past restaurants.
- **Commit later:** If the saved place cannot work now, offer a chosen future day rather than losing the intention to Not today forever. User-selected reminders fit a privacy-preserving direction better than background geofences.
- Run a two-week concierge test with roughly 10–15 participants as a proposed practical sample, not a statistically powered experiment. Recruit people with genuinely neglected saved restaurants. Ask each for a few existing saves, an available area/window and optional one friend. Do not ask for exhaustive backfill.
- Vary solo concrete nudge versus concrete nudge plus invitation among comparable meal opportunities; if possible alternate assignment within users. Record opportunity, reason skipped, invitation sent, friend acceptance, confirmed visit, and whether they would have gone anyway. This is directional evidence, not causal proof with such a small sample.
- Primary learning: did Nosh help a desired meal happen that otherwise likely would not, did people return for a second use without chasing, and was timing, company, or restaurant feasibility the binding obstacle? Count confirmed visits separately from taps and RSVP intentions.
- Set continuation criteria in advance based on founder priorities; for example, repeated unprompted use by several participants and visits across more than one social circle. These are suggested decision rules, not industry benchmarks.
- If people appreciate reminders but rarely act, diagnose the barrier before building ranking. If invitations work but wishlist overlap rarely matters, build plan formation rather than a matching engine. If only strangers are desired, test scheduled hosted events separately because that is a different operating business.

### Gaps
- Willingness to pay and defensibility remain untested. Operating a useful concierge trial does not prove software can reproduce the same results at low cost.
