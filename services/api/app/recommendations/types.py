from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidatePlace:
    place_id: uuid.UUID
    cuisine_id: uuid.UUID
    cuisine_slug: str
    distance_meters: float
    quality_score: float  # [0, 1] curated quality; neutral 0.5 if unknown
    is_primary_cuisine: bool


@dataclass(frozen=True)
class CuisineStats:
    cuisine_id: uuid.UUID
    slug: str
    confirmed_positive_visits: int = 0
    confirmed_negative_visits: int = 0
    history_frequency: float = 0.0  # normalized onboarding frequency [0, 1]
    unvisited_count: int = 0


@dataclass
class ScoredPlace:
    candidate: CandidatePlace
    quality_score: float
    distance_score: float
    context_fit: float
    exploration_score: float
    total_score: float
    reason_codes: list[str] = field(default_factory=list)

    @property
    def score_components(self) -> dict[str, float]:
        return {
            "quality": self.quality_score,
            "distance": self.distance_score,
            "context_fit": self.context_fit,
            "exploration": self.exploration_score,
        }


@dataclass
class RecommendationResult:
    proposal: ScoredPlace
    chosen_cuisine_id: uuid.UUID
    chosen_cuisine_slug: str
    cuisine_sample: float
    unvisited_pool_size: int
    candidate_count: int
    exclusion_counts: dict[str, int]
    policy_version: str
    session_seed: str


@dataclass
class NoCandidatesResult:
    reason_codes: list[str]
    exclusion_counts: dict[str, int]
    policy_version: str


RecommendationOutcome = RecommendationResult | NoCandidatesResult
