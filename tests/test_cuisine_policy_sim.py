import random
import statistics

import pytest

from spike.cuisine_policy_sim import (
    CUISINE_COUNTS,
    POLICIES,
    LowestBeenPct,
    SimConfig,
    State,
    ThompsonNovelty,
    available,
    make_taste,
    make_world,
    seed_history,
    simulate,
)


def small_state() -> State:
    return State(
        total={"thai": 4, "pho": 2, "taco": 3},
        visited={"thai": {0}, "pho": {0, 1}, "taco": set()},
        history_counts={"thai": 5, "pho": 9, "taco": 0},
    )


def test_been_pct_and_unvisited():
    s = small_state()
    assert s.been_pct("thai") == 0.25
    assert s.unvisited("thai") == 3
    assert s.been_pct("pho") == 1.0


def test_available_skips_exhausted_and_excluded():
    s = small_state()
    assert available(s, set()) == ["thai", "taco"]
    assert available(s, {"taco"}) == ["thai"]


def test_lowest_been_pct_leads_with_least_covered():
    s = small_state()
    assert LowestBeenPct().propose(s, random.Random(0), set()) == "taco"


@pytest.mark.parametrize("key", list(POLICIES))
def test_policies_never_repeat_or_propose_exhausted(key):
    s = small_state()
    policy = POLICIES[key]({c: 0.5 for c in s.total})
    rng, seen = random.Random(1), set()
    while (c := policy.propose(s, rng, seen)) is not None:
        assert c not in seen and s.unvisited(c) > 0
        seen.add(c)
    assert seen == {"thai", "taco"}


def test_thompson_learns_from_rejections():
    s = State(
        total={"a": 10, "b": 10},
        visited={"a": set(), "b": set()},
        history_counts={"a": 0, "b": 0},
        accepts={"a": 20, "b": 0},
        rejects={"a": 0, "b": 20},
    )
    rng, policy = random.Random(2), ThompsonNovelty()
    picks = [policy.propose(s, rng, set()) for _ in range(200)]
    assert picks.count("a") > 190


def test_simulation_is_deterministic_per_seed():
    assert simulate("thompson", seed=3) == simulate("thompson", seed=3)


def test_model_contains_the_confound():
    """Sanity check on the model itself: lower been-to % should go with lower taste."""
    cfg, corrs = SimConfig(), []
    for seed in range(200):
        rng = random.Random(seed)
        world = make_world(rng)
        taste = make_taste(cfg, rng)
        visited, _ = seed_history(world, taste, cfg, rng)
        been = [len(visited[c]) / CUISINE_COUNTS[c] for c in CUISINE_COUNTS]
        corrs.append(statistics.correlation(been, [taste[c] for c in CUISINE_COUNTS]))
    assert statistics.fmean(corrs) > 0.3
