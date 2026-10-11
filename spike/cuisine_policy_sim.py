"""Cuisine-selection policy simulation (pre-design spike).

Question this spike answers
---------------------------
If the goal is "get the user to try as many new restaurants as possible", is
"propose the cuisine with the lowest been-to %" a good policy?

Hypothesis being tested: been-to % is confounded with taste. People have been
to fewer places in cuisines they don't like, so the lowest-% cuisine is often
one the user will reject. A policy that learns acceptance from rejections
should beat it.

This is a toy model. Absolute numbers depend entirely on SimConfig; read the
results as "does the mechanism show up, and how big could it be", not as a
forecast. Every assumption is a named field so it can be challenged.

Run:  uv run python -m spike.cuisine_policy_sim --users 500
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Callable, Protocol

# Restaurant counts per cuisine in a made-up suburban neighborhood.
# Deliberately uneven: big cuisines (chinese) and tiny ones (ethiopian).
CUISINE_COUNTS: dict[str, int] = {
    "chinese": 30,
    "american": 25,
    "mexican": 22,
    "japanese": 20,
    "thai": 14,
    "indian": 12,
    "italian": 12,
    "vietnamese": 10,
    "korean": 10,
    "mediterranean": 8,
    "french": 4,
    "peruvian": 3,
    "ethiopian": 2,
}


@dataclass(frozen=True)
class SimConfig:
    days: int = 90
    meals_per_day: int = 2  # lunch + dinner, no breakfast
    p_open: float = 0.7  # P(user engages with a nudge) vs snooze / "not today"
    max_proposals: int = 3  # cuisines shown before the user gives up on the app
    p_accept_restaurant: float = 0.75  # P(user accepts the restaurant once the cuisine is accepted)
    taste_a: float = 1.5  # per-cuisine taste ~ Beta(taste_a, taste_b)
    taste_b: float = 1.5
    history_meals: int = 80  # meals eaten before installing (imported at onboarding)
    taste_concentration: float = 2.0  # history cuisine choice weight = taste ** this * sqrt(count)
    p_revisit: float = 0.6  # in history, P(back to a known place) when one exists
    churn: bool = True  # whether rejections can make the user mute the app
    churn_base: float = 0.002  # per-session P(mute) with zero rejections
    churn_per_rejection: float = 0.01  # added per-session P(mute) per rejected proposal


# --------------------------------------------------------------------------- #
# World, user, and what the system knows
# --------------------------------------------------------------------------- #


@dataclass
class World:
    quality: dict[str, list[float]]  # cuisine -> quality score per restaurant (index = id)


@dataclass
class State:
    """Everything the recommender is allowed to see."""

    total: dict[str, int]
    visited: dict[str, set[int]]
    history_counts: dict[str, int]  # meals per cuisine from the onboarding import
    accepts: dict[str, int] = field(default_factory=dict)
    rejects: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for c in self.total:
            self.accepts.setdefault(c, 0)
            self.rejects.setdefault(c, 0)

    @property
    def cuisines(self) -> list[str]:
        return list(self.total)

    def unvisited(self, c: str) -> int:
        return self.total[c] - len(self.visited[c])

    def been_pct(self, c: str) -> float:
        return len(self.visited[c]) / self.total[c]


def make_world(rng: random.Random) -> World:
    return World({c: [rng.random() for _ in range(n)] for c, n in CUISINE_COUNTS.items()})


def make_taste(cfg: SimConfig, rng: random.Random) -> dict[str, float]:
    """Hidden ground truth: P(user accepts cuisine c when it is proposed)."""
    return {c: rng.betavariate(cfg.taste_a, cfg.taste_b) for c in CUISINE_COUNTS}


def seed_history(
    world: World, taste: dict[str, float], cfg: SimConfig, rng: random.Random
) -> tuple[dict[str, set[int]], dict[str, int]]:
    """Pre-app eating history. Cuisine choice follows taste, which is what creates the confound."""
    cuisines = list(world.quality)
    weights = [taste[c] ** cfg.taste_concentration * math.sqrt(len(world.quality[c])) for c in cuisines]
    visited: dict[str, set[int]] = {c: set() for c in cuisines}
    counts = {c: 0 for c in cuisines}
    for _ in range(cfg.history_meals):
        c = rng.choices(cuisines, weights)[0]
        counts[c] += 1
        n = len(world.quality[c])
        if visited[c] and (len(visited[c]) == n or rng.random() < cfg.p_revisit):
            continue  # went back to a favourite: no new restaurant
        visited[c].add(rng.choice([i for i in range(n) if i not in visited[c]]))
    return visited, counts


def best_unvisited(world: World, state: State, c: str) -> int:
    """Same restaurant recommender for every policy: highest quality not yet visited."""
    options = [i for i in range(state.total[c]) if i not in state.visited[c]]
    return max(options, key=lambda i: world.quality[c][i])


# --------------------------------------------------------------------------- #
# Policies: which cuisine to propose next
# --------------------------------------------------------------------------- #


def available(state: State, exclude: set[str]) -> list[str]:
    return [c for c in state.cuisines if state.unvisited(c) > 0 and c not in exclude]


def depletion_weight(unvisited: int, scale: float = 2.0) -> float:
    """Value of a cuisine's remaining pool: ~0.39 with 1 left, ~0.78 with 3, ~1 with 10+."""
    return 1.0 - math.exp(-unvisited / scale)


class Policy(Protocol):
    name: str

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None: ...


class RandomCuisine:
    name = "random"

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None:
        opts = available(state, exclude)
        return rng.choice(opts) if opts else None


class LowestBeenPct:
    """The spec as written: always lead with the cuisine you've covered least."""

    name = "lowest_been_pct (spec)"

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None:
        opts = available(state, exclude)
        if not opts:
            return None
        return min(opts, key=lambda c: (state.been_pct(c), rng.random()))


class WeightedBeenPct:
    """Softer spec: sample cuisines with probability proportional to (1 - been %)."""

    name = "weighted_been_pct"

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None:
        opts = available(state, exclude)
        if not opts:
            return None
        return rng.choices(opts, [1.0 - state.been_pct(c) + 0.05 for c in opts])[0]


class ThompsonNovelty:
    """Contextual-bandit-lite: sampled P(accept) x value of the unvisited pool.

    Every accept/reject on a proposal updates a Beta posterior per cuisine.
    With history_prior > 0, onboarding history frequency is treated as evidence
    of taste (the opposite of the spec's reading of the same signal).
    """

    def __init__(self, history_prior: float = 0.0) -> None:
        self.m = history_prior
        self.name = "thompson + history prior" if history_prior else "thompson"

    def prior(self, state: State, c: str) -> tuple[float, float]:
        if not self.m:
            return 1.0, 1.0
        top = max(state.history_counts.values()) or 1
        f = state.history_counts[c] / top
        return 1.0 + self.m * f, 1.0 + self.m * (1.0 - f)

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None:
        opts = available(state, exclude)
        if not opts:
            return None

        def score(c: str) -> float:
            a0, b0 = self.prior(state, c)
            theta = rng.betavariate(a0 + state.accepts[c], b0 + state.rejects[c])
            return theta * depletion_weight(state.unvisited(c))

        return max(opts, key=score)


class Oracle:
    """Cheats: knows the true taste. Upper-bound reference, not a real policy."""

    name = "oracle (knows taste)"

    def __init__(self, taste: dict[str, float]) -> None:
        self.taste = taste

    def propose(self, state: State, rng: random.Random, exclude: set[str]) -> str | None:
        opts = available(state, exclude)
        if not opts:
            return None
        return max(opts, key=lambda c: self.taste[c] * depletion_weight(state.unvisited(c)))


PolicyFactory = Callable[[dict[str, float]], Policy]

POLICIES: dict[str, PolicyFactory] = {
    "random": lambda taste: RandomCuisine(),
    "lowest_been_pct": lambda taste: LowestBeenPct(),
    "weighted_been_pct": lambda taste: WeightedBeenPct(),
    "thompson": lambda taste: ThompsonNovelty(),
    "thompson_history_prior": lambda taste: ThompsonNovelty(history_prior=4.0),
    "oracle": lambda taste: Oracle(taste),
}
BASELINE = "lowest_been_pct"


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #


@dataclass
class Outcome:
    new_restaurants: int
    sessions: int
    proposals: int
    rejections: int
    muted: bool

    @property
    def rejections_per_session(self) -> float:
        return self.rejections / self.sessions if self.sessions else 0.0

    @property
    def cuisine_accept_rate(self) -> float:
        return (self.proposals - self.rejections) / self.proposals if self.proposals else 0.0


def simulate(policy_key: str, seed: int, cfg: SimConfig = SimConfig()) -> Outcome:
    """One simulated user over cfg.days. Same seed => same world, taste and history for every policy."""
    world_rng = random.Random(seed)
    world = make_world(world_rng)
    taste = make_taste(cfg, world_rng)
    visited, counts = seed_history(world, taste, cfg, world_rng)
    state = State(total=dict(CUISINE_COUNTS), visited=visited, history_counts=counts)

    policy = POLICIES[policy_key](taste)
    user_rng = random.Random(seed + 1_000_003)
    policy_rng = random.Random(seed + 2_000_003)

    new = sessions = proposals = rejections = 0
    muted = False
    for _ in range(cfg.days * cfg.meals_per_day):
        if muted:
            break
        if user_rng.random() > cfg.p_open:
            continue  # snoozed or "not today": not a signal about cuisine
        sessions += 1
        exclude: set[str] = set()
        session_rejections = 0
        for _ in range(cfg.max_proposals):
            c = policy.propose(state, policy_rng, exclude)
            if c is None:
                break
            proposals += 1
            if user_rng.random() < taste[c]:
                state.accepts[c] += 1
                rid = best_unvisited(world, state, c)
                if user_rng.random() < cfg.p_accept_restaurant:
                    state.visited[c].add(rid)
                    new += 1
                break
            state.rejects[c] += 1
            session_rejections += 1
            exclude.add(c)
        rejections += session_rejections
        if cfg.churn and user_rng.random() < cfg.churn_base + cfg.churn_per_rejection * session_rejections:
            muted = True
    return Outcome(new, sessions, proposals, rejections, muted)


def mean_ci(xs: list[float]) -> tuple[float, float]:
    """Mean and 95% CI half-width (normal approximation)."""
    m = statistics.fmean(xs)
    half = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
    return m, half


def run_all(cfg: SimConfig, users: int) -> dict[str, list[Outcome]]:
    return {key: [simulate(key, seed, cfg) for seed in range(users)] for key in POLICIES}


def report(results: dict[str, list[Outcome]], cfg: SimConfig, users: int) -> str:
    base = [o.new_restaurants for o in results[BASELINE]]
    lines = [
        f"{users} simulated users x {cfg.days} days, churn={'on' if cfg.churn else 'off'}. "
        "Mean +/- 95% CI. Delta is paired (same users) vs the spec policy.",
        "",
        "| Policy | New restaurants | Delta vs spec | Rejections / session | Cuisine accept rate | Muted by end |",
        "|---|---|---|---|---|---|",
    ]
    for key, outs in results.items():
        name = POLICIES[key]({c: 0.5 for c in CUISINE_COUNTS}).name
        n, n_ci = mean_ci([o.new_restaurants for o in outs])
        d, d_ci = mean_ci([o.new_restaurants - b for o, b in zip(outs, base)])
        r, r_ci = mean_ci([o.rejections_per_session for o in outs])
        a, a_ci = mean_ci([o.cuisine_accept_rate for o in outs])
        muted = statistics.fmean(o.muted for o in outs)
        delta = "—" if key == BASELINE else f"{d:+.1f} ± {d_ci:.1f}"
        lines.append(
            f"| {name} | {n:.1f} ± {n_ci:.1f} | {delta} | {r:.2f} ± {r_ci:.2f} "
            f"| {a:.0%} ± {a_ci:.0%} | {muted:.0%} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--users", type=int, default=500)
    parser.add_argument("--no-churn", action="store_true", help="rejections never make the user mute the app")
    args = parser.parse_args(argv)
    cfg = SimConfig(churn=not args.no_churn)
    print(report(run_all(cfg, args.users), cfg, args.users))


if __name__ == "__main__":
    main()
