"""Cuisine prior and evidence provenance for policy_v0 (pure functions, no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.recommendations.engine import _beta_params
from app.recommendations.priors import build_cuisine_stats
from app.recommendations.types import CuisineStats

THAI = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
TACO = uuid.UUID("00000000-0000-0000-0000-0000000000a2")
RAMEN = uuid.UUID("00000000-0000-0000-0000-0000000000a3")
CATALOG = {THAI: "thai", TACO: "mexican", RAMEN: "japanese"}


def test_default_cuisine_stats_use_neutral_beta_1_1() -> None:
    assert _beta_params(CuisineStats(cuisine_id=THAI, slug="thai")) == (1.0, 1.0)


def test_no_onboarding_history_gives_every_cuisine_beta_1_1() -> None:
    stats = build_cuisine_stats(CATALOG, [], [])
    assert set(stats) == set(CATALOG)
    for s in stats.values():
        assert s.history_frequency is None
        assert _beta_params(s) == (1.0, 1.0)


def test_onboarding_history_sets_frequency_prior() -> None:
    # Three pre-Nosh places: two Thai, one taco.
    stats = build_cuisine_stats(CATALOG, [THAI, THAI, TACO], [])
    assert stats[THAI].history_frequency == pytest.approx(2 / 3)
    assert stats[TACO].history_frequency == pytest.approx(1 / 3)
    # With history present, an unseen cuisine gets f=0, not the neutral prior.
    assert stats[RAMEN].history_frequency == 0.0
    assert _beta_params(stats[THAI]) == pytest.approx((1 + 4 * 2 / 3, 1 + 4 * 1 / 3))
    assert _beta_params(stats[RAMEN]) == (1.0, 5.0)


def test_positive_and_negative_visits_without_history_stay_on_neutral_prior() -> None:
    stats = build_cuisine_stats(CATALOG, [], [(THAI, "positive"), (TACO, "negative")])
    assert stats[THAI].history_frequency is None
    assert stats[THAI].confirmed_positive_visits == 1
    assert _beta_params(stats[THAI]) == (2.0, 1.0)
    assert stats[TACO].confirmed_negative_visits == 1
    assert _beta_params(stats[TACO]) == (1.0, 1.25)


def test_later_visits_are_outcomes_not_onboarding_history() -> None:
    """A post-Nosh visit adds outcome evidence only; the history prior is unchanged."""
    before = build_cuisine_stats(CATALOG, [TACO], [])
    after = build_cuisine_stats(
        CATALOG, [TACO], [(THAI, "positive"), (THAI, "positive"), (RAMEN, "negative")]
    )
    for cid in CATALOG:
        assert after[cid].history_frequency == before[cid].history_frequency
    assert after[THAI].confirmed_positive_visits == 2
    assert after[RAMEN].confirmed_negative_visits == 1
    # Beta(1 + 4*0, 1 + 4*1) + 2 positives
    assert _beta_params(after[THAI]) == (3.0, 5.0)
    assert _beta_params(after[RAMEN]) == (1.0, 5.25)


def test_unrated_outcomes_are_ignored() -> None:
    stats = build_cuisine_stats(CATALOG, [], [(THAI, None)])
    assert stats[THAI].confirmed_positive_visits == 0
    assert stats[THAI].confirmed_negative_visits == 0


def test_cuisines_outside_catalog_are_still_represented() -> None:
    stray = uuid.uuid4()
    stats = build_cuisine_stats(CATALOG, [stray], [])
    assert stats[stray].history_frequency == 1.0
    assert stats[stray].slug == ""
