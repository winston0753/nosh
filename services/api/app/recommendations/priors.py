"""Pure construction of per-cuisine preference evidence for ``policy_v0``.

Two independent evidence sources feed the cuisine Beta posterior:

1. **Pre-Nosh onboarding history** — places the user classified as Been during
   onboarding (``was_visited_before_nosh = TRUE``).  Their primary-cuisine
   frequencies form the weak history prior.  Places that became visited only
   through a Nosh confirmation or a manual edit are *not* history.
2. **Confirmed proposal outcomes** — rated visits that confirm a Nosh proposal.
   Manual visits (no proposal) do not update cuisine preference (D015).

Keeping the sources separate guarantees a post-Nosh visit is never counted
both as onboarding history and as a confirmed outcome.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Mapping

from app.recommendations.types import CuisineStats


def build_cuisine_stats(
    cuisine_slugs: Mapping[uuid.UUID, str],
    pre_nosh_cuisine_ids: Iterable[uuid.UUID],
    proposal_outcomes: Iterable[tuple[uuid.UUID, str | None]],
) -> dict[uuid.UUID, CuisineStats]:
    """Return evidence for every catalog cuisine.

    ``pre_nosh_cuisine_ids`` holds one primary-cuisine entry per pre-Nosh place.
    ``proposal_outcomes`` holds one ``(cuisine_id, rating)`` per confirmed
    proposal-backed visit; unrated entries are ignored.

    With no pre-Nosh history every cuisine gets ``history_frequency=None``
    (neutral prior).  With history, cuisines absent from it get ``0.0``.
    """
    history = Counter(pre_nosh_cuisine_ids)
    total_history = sum(history.values())

    positives: Counter[uuid.UUID] = Counter()
    negatives: Counter[uuid.UUID] = Counter()
    for cuisine_id, rating in proposal_outcomes:
        if rating == "positive":
            positives[cuisine_id] += 1
        elif rating == "negative":
            negatives[cuisine_id] += 1

    cuisine_ids = set(cuisine_slugs) | set(history) | set(positives) | set(negatives)
    stats: dict[uuid.UUID, CuisineStats] = {}
    for cuisine_id in cuisine_ids:
        frequency = history[cuisine_id] / total_history if total_history else None
        stats[cuisine_id] = CuisineStats(
            cuisine_id=cuisine_id,
            slug=cuisine_slugs.get(cuisine_id, ""),
            confirmed_positive_visits=positives[cuisine_id],
            confirmed_negative_visits=negatives[cuisine_id],
            history_frequency=frequency,
        )
    return stats
