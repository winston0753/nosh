"""policy_v0: Thompson-sampling cuisine selection + deterministic restaurant scoring.

All functions are pure (no I/O). The caller fetches data and passes it in.
The session_seed makes sampling deterministic and replayable.
"""

from __future__ import annotations

import hashlib
import math
import random
import uuid
from collections import defaultdict

from app.recommendations.types import (
    CandidatePlace,
    CuisineStats,
    NoCandidatesResult,
    RecommendationOutcome,
    RecommendationResult,
    ScoredPlace,
)

POLICY_VERSION = "policy_v0"
HISTORY_PRIOR_STRENGTH = 4.0
WEIGHT_QUALITY = 0.45
WEIGHT_DISTANCE = 0.30
WEIGHT_CONTEXT_FIT = 0.15
WEIGHT_EXPLORATION = 0.10


# --------------------------------------------------------------------------- #
# Cuisine scoring (Thompson sampling)
# --------------------------------------------------------------------------- #


def _pool_value(unvisited: int, scale: float = 2.0) -> float:
    """Non-linear value of a cuisine's remaining unvisited pool."""
    return 1.0 - math.exp(-unvisited / scale)


def _beta_params(stats: CuisineStats) -> tuple[float, float]:
    """Compute Beta(alpha, beta) from the onboarding prior plus confirmed outcomes.

    Without any pre-Nosh onboarding history the prior is the neutral Beta(1, 1)
    (RECOMMENDATIONS.md §5.1); otherwise it is Beta(1 + 4f, 1 + 4(1 - f)).
    """
    if stats.history_frequency is None:
        alpha, beta = 1.0, 1.0
    else:
        alpha = 1.0 + HISTORY_PRIOR_STRENGTH * stats.history_frequency
        beta = 1.0 + HISTORY_PRIOR_STRENGTH * (1.0 - stats.history_frequency)
    alpha += stats.confirmed_positive_visits
    beta += 0.25 * stats.confirmed_negative_visits
    return alpha, beta


def _sample_cuisine_score(rng: random.Random, stats: CuisineStats) -> float:
    alpha, beta = _beta_params(stats)
    theta = rng.betavariate(alpha, beta)
    return theta * _pool_value(stats.unvisited_count)


def select_cuisine(
    rng: random.Random,
    candidates: list[CandidatePlace],
    stats_by_cuisine: dict[uuid.UUID, CuisineStats],
    already_proposed: set[uuid.UUID],
) -> tuple[uuid.UUID, float] | tuple[None, None]:
    """Return (cuisine_id, sampled_score) for the highest-scoring cuisine, or (None, None)."""
    cuisine_unvisited: dict[uuid.UUID, int] = defaultdict(int)
    for c in candidates:
        if c.place_id not in already_proposed:
            cuisine_unvisited[c.cuisine_id] += 1

    eligible = [cid for cid, count in cuisine_unvisited.items() if count > 0]
    if not eligible:
        return None, None

    scores: dict[uuid.UUID, float] = {}
    for cid in eligible:
        stats = stats_by_cuisine.get(cid)
        if stats is None:
            stats = CuisineStats(cuisine_id=cid, slug="", unvisited_count=cuisine_unvisited[cid])
        else:
            stats = CuisineStats(
                cuisine_id=stats.cuisine_id,
                slug=stats.slug,
                confirmed_positive_visits=stats.confirmed_positive_visits,
                confirmed_negative_visits=stats.confirmed_negative_visits,
                history_frequency=stats.history_frequency,
                unvisited_count=cuisine_unvisited[cid],
            )
        scores[cid] = _sample_cuisine_score(rng, stats)

    winner = max(eligible, key=lambda cid: (scores[cid], str(cid)))
    return winner, scores[winner]


# --------------------------------------------------------------------------- #
# Place scoring (deterministic)
# --------------------------------------------------------------------------- #


def _distance_score(distance_meters: float, radius_meters: float) -> float:
    """Monotonic decay: 1.0 at center, ~0 at radius edge."""
    if radius_meters <= 0:
        return 0.0
    ratio = min(distance_meters / radius_meters, 1.0)
    return 1.0 - ratio


def _exploration_score(place_id: uuid.UUID, sequence_number: int) -> float:
    """Deterministic tie-breaker based on place_id and sequence to prefer underexposed places."""
    h = hashlib.md5(f"{place_id}:{sequence_number}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def score_place(
    candidate: CandidatePlace,
    radius_meters: float,
    sequence_number: int,
    meal_type: str | None = None,
) -> ScoredPlace:
    quality = candidate.quality_score
    distance = _distance_score(candidate.distance_meters, radius_meters)
    context_fit = 1.0 if (meal_type and candidate.is_primary_cuisine) else 0.5
    exploration = _exploration_score(candidate.place_id, sequence_number)

    total = (
        WEIGHT_QUALITY * quality
        + WEIGHT_DISTANCE * distance
        + WEIGHT_CONTEXT_FIT * context_fit
        + WEIGHT_EXPLORATION * exploration
    )

    reason_codes = []
    if distance > 0.7:
        reason_codes.append("nearby")
    reason_codes.append("new_to_you")
    if quality > 0.7:
        reason_codes.append("highly_rated")

    return ScoredPlace(
        candidate=candidate,
        quality_score=quality,
        distance_score=distance,
        context_fit=context_fit,
        exploration_score=exploration,
        total_score=total,
        reason_codes=reason_codes,
    )


def select_best_place(
    candidates: list[CandidatePlace],
    cuisine_id: uuid.UUID,
    radius_meters: float,
    sequence_number: int,
    already_proposed: set[uuid.UUID],
    meal_type: str | None = None,
) -> ScoredPlace | None:
    """Score all eligible places in the cuisine and return the best."""
    eligible = [
        c for c in candidates if c.cuisine_id == cuisine_id and c.place_id not in already_proposed
    ]
    if not eligible:
        return None
    scored = [score_place(c, radius_meters, sequence_number, meal_type) for c in eligible]
    return max(scored, key=lambda s: (s.total_score, str(s.candidate.place_id)))


# --------------------------------------------------------------------------- #
# Top-level recommendation
# --------------------------------------------------------------------------- #


def _make_rng(session_id: uuid.UUID, sequence_number: int) -> random.Random:
    """Deterministic RNG from session + sequence. Same inputs => same output."""
    seed_str = f"{session_id}:{sequence_number}:{POLICY_VERSION}"
    seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_int)


def recommend(
    *,
    session_id: uuid.UUID,
    candidates: list[CandidatePlace],
    stats_by_cuisine: dict[uuid.UUID, CuisineStats],
    already_proposed: set[uuid.UUID],
    radius_meters: float,
    sequence_number: int,
    meal_type: str | None = None,
) -> RecommendationOutcome:
    """Return the next proposal for a session, or a NoCandidatesResult."""
    exclusion_counts: dict[str, int] = {}

    rng = _make_rng(session_id, sequence_number)

    cuisine_id, cuisine_sample = select_cuisine(rng, candidates, stats_by_cuisine, already_proposed)
    if cuisine_id is None or cuisine_sample is None:
        return NoCandidatesResult(
            reason_codes=["no_eligible_candidates"],
            exclusion_counts=exclusion_counts,
            policy_version=POLICY_VERSION,
        )

    scored = select_best_place(
        candidates, cuisine_id, radius_meters, sequence_number, already_proposed, meal_type
    )
    if scored is None:
        return NoCandidatesResult(
            reason_codes=["no_eligible_candidates"],
            exclusion_counts=exclusion_counts,
            policy_version=POLICY_VERSION,
        )

    stats = stats_by_cuisine.get(cuisine_id)
    cuisine_slug = stats.slug if stats else ""
    unvisited_pool_size = sum(
        1 for c in candidates if c.cuisine_id == cuisine_id and c.place_id not in already_proposed
    )

    return RecommendationResult(
        proposal=scored,
        chosen_cuisine_id=cuisine_id,
        chosen_cuisine_slug=cuisine_slug,
        cuisine_sample=cuisine_sample,
        unvisited_pool_size=unvisited_pool_size,
        candidate_count=len(candidates),
        exclusion_counts=exclusion_counts,
        policy_version=POLICY_VERSION,
        session_seed=f"{session_id}:{sequence_number}",
    )
