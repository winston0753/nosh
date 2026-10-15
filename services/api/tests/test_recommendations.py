"""Unit tests for the recommendation engine (pure functions, no DB)."""

from __future__ import annotations

import uuid

from app.recommendations.engine import (
    POLICY_VERSION,
    _distance_score,
    _pool_value,
    recommend,
)
from app.recommendations.types import (
    CandidatePlace,
    CuisineStats,
    NoCandidatesResult,
    RecommendationResult,
)


def make_place(
    place_id: uuid.UUID | None = None,
    cuisine_id: uuid.UUID | None = None,
    distance: float = 500.0,
    quality: float = 0.7,
) -> CandidatePlace:
    return CandidatePlace(
        place_id=place_id or uuid.uuid4(),
        cuisine_id=cuisine_id or uuid.uuid4(),
        cuisine_slug="test",
        distance_meters=distance,
        quality_score=quality,
        is_primary_cuisine=True,
    )


# --------------------------------------------------------------------------- #
# Pool value
# --------------------------------------------------------------------------- #


def test_pool_value_increases_with_count():
    assert _pool_value(1) < _pool_value(3) < _pool_value(10)


def test_pool_value_approaches_one():
    assert _pool_value(100) > 0.99


def test_pool_value_zero_places():
    assert _pool_value(0) == 0.0


# --------------------------------------------------------------------------- #
# Eligibility: visited and not-interested places are never candidates
# These are enforced before calling recommend() by build_candidates().
# The engine trusts the passed candidate list.
# --------------------------------------------------------------------------- #


def test_recommend_returns_no_candidates_when_empty():
    result = recommend(
        session_id=uuid.uuid4(),
        candidates=[],
        stats_by_cuisine={},
        already_proposed=set(),
        radius_meters=1600,
        sequence_number=1,
    )
    assert isinstance(result, NoCandidatesResult)
    assert result.policy_version == POLICY_VERSION


def test_recommend_returns_result_with_eligible_candidates():
    cid = uuid.uuid4()
    candidates = [make_place(cuisine_id=cid) for _ in range(3)]
    result = recommend(
        session_id=uuid.uuid4(),
        candidates=candidates,
        stats_by_cuisine={},
        already_proposed=set(),
        radius_meters=1600,
        sequence_number=1,
    )
    assert isinstance(result, RecommendationResult)
    assert result.policy_version == POLICY_VERSION
    assert result.proposal.candidate in candidates


def test_already_proposed_place_not_returned():
    cid = uuid.uuid4()
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    candidates = [
        make_place(place_id=p1, cuisine_id=cid),
        make_place(place_id=p2, cuisine_id=cid),
    ]
    result = recommend(
        session_id=uuid.uuid4(),
        candidates=candidates,
        stats_by_cuisine={},
        already_proposed={p1},
        radius_meters=1600,
        sequence_number=2,
    )
    assert isinstance(result, RecommendationResult)
    assert result.proposal.candidate.place_id != p1


def test_all_proposed_returns_no_candidates():
    cid = uuid.uuid4()
    p1 = uuid.uuid4()
    candidates = [make_place(place_id=p1, cuisine_id=cid)]
    result = recommend(
        session_id=uuid.uuid4(),
        candidates=candidates,
        stats_by_cuisine={},
        already_proposed={p1},
        radius_meters=1600,
        sequence_number=2,
    )
    assert isinstance(result, NoCandidatesResult)


# --------------------------------------------------------------------------- #
# Determinism: same inputs produce same output
# --------------------------------------------------------------------------- #


def test_recommend_is_deterministic():
    session_id = uuid.uuid4()
    cid = uuid.uuid4()
    candidates = [make_place(cuisine_id=cid) for _ in range(5)]
    stats = {cid: CuisineStats(cuisine_id=cid, slug="test", unvisited_count=5)}

    r1 = recommend(
        session_id=session_id,
        candidates=candidates,
        stats_by_cuisine=stats,
        already_proposed=set(),
        radius_meters=1600,
        sequence_number=1,
    )
    r2 = recommend(
        session_id=session_id,
        candidates=candidates,
        stats_by_cuisine=stats,
        already_proposed=set(),
        radius_meters=1600,
        sequence_number=1,
    )
    assert isinstance(r1, RecommendationResult)
    assert isinstance(r2, RecommendationResult)
    assert r1.proposal.candidate.place_id == r2.proposal.candidate.place_id


# --------------------------------------------------------------------------- #
# Not today does not change cuisine preference (enforced in feedback semantics)
# This test verifies that the engine produces different results when stats differ.
# --------------------------------------------------------------------------- #


def test_high_positive_visits_increases_cuisine_probability():
    """A cuisine with many confirmed positive visits should be sampled higher on average."""
    cid_liked = uuid.uuid4()
    cid_neutral = uuid.uuid4()

    stats = {
        cid_liked: CuisineStats(
            cuisine_id=cid_liked,
            slug="liked",
            confirmed_positive_visits=20,
            unvisited_count=5,
        ),
        cid_neutral: CuisineStats(
            cuisine_id=cid_neutral,
            slug="neutral",
            confirmed_positive_visits=0,
            unvisited_count=5,
        ),
    }
    session_id = uuid.uuid4()
    candidates = [
        make_place(cuisine_id=cid_liked),
        make_place(cuisine_id=cid_neutral),
    ]

    liked_count = 0
    for seq in range(100):
        result = recommend(
            session_id=session_id,
            candidates=candidates,
            stats_by_cuisine=stats,
            already_proposed=set(),
            radius_meters=1600,
            sequence_number=seq,
        )
        if isinstance(result, RecommendationResult) and (
            result.proposal.candidate.cuisine_id == cid_liked
        ):
            liked_count += 1

    # The liked cuisine should win more than 60% of the time
    assert liked_count > 60, f"Expected >60 wins for liked cuisine, got {liked_count}"


# --------------------------------------------------------------------------- #
# Distance score
# --------------------------------------------------------------------------- #


def test_distance_score_one_at_center():
    assert _distance_score(0, 1600) == 1.0


def test_distance_score_zero_at_radius():
    assert _distance_score(1600, 1600) == 0.0


def test_distance_score_monotonically_decreasing():
    scores = [_distance_score(d, 1600) for d in [0, 400, 800, 1200, 1600]]
    assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------- #
# Policy version is always set
# --------------------------------------------------------------------------- #


def test_policy_version_in_result():
    result = recommend(
        session_id=uuid.uuid4(),
        candidates=[make_place()],
        stats_by_cuisine={},
        already_proposed=set(),
        radius_meters=1600,
        sequence_number=1,
    )
    assert isinstance(result, RecommendationResult)
    assert result.policy_version == "policy_v0"
