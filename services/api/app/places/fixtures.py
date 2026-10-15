"""Deterministic fixture restaurants for local development.

These are fictional restaurants in the Mission District / Castro area of San
Francisco. They exist only to make the recommendation loop runnable locally.
All provider_place_ids use the "fixture" provider so they cannot collide with
real data sources.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

# Seed UUIDs so fixture IDs are stable across resets.
_SEED_PLACES = [
    uuid.UUID("10000000-0000-0000-0000-000000000001"),
    uuid.UUID("10000000-0000-0000-0000-000000000002"),
    uuid.UUID("10000000-0000-0000-0000-000000000003"),
    uuid.UUID("10000000-0000-0000-0000-000000000004"),
    uuid.UUID("10000000-0000-0000-0000-000000000005"),
    uuid.UUID("10000000-0000-0000-0000-000000000006"),
    uuid.UUID("10000000-0000-0000-0000-000000000007"),
    uuid.UUID("10000000-0000-0000-0000-000000000008"),
    uuid.UUID("10000000-0000-0000-0000-000000000009"),
    uuid.UUID("10000000-0000-0000-0000-000000000010"),
    uuid.UUID("10000000-0000-0000-0000-000000000011"),
    uuid.UUID("10000000-0000-0000-0000-000000000012"),
    uuid.UUID("10000000-0000-0000-0000-000000000013"),
    uuid.UUID("10000000-0000-0000-0000-000000000014"),
    uuid.UUID("10000000-0000-0000-0000-000000000015"),
    uuid.UUID("10000000-0000-0000-0000-000000000016"),
    uuid.UUID("10000000-0000-0000-0000-000000000017"),
    uuid.UUID("10000000-0000-0000-0000-000000000018"),
    uuid.UUID("10000000-0000-0000-0000-000000000019"),
    uuid.UUID("10000000-0000-0000-0000-000000000020"),
]

_SEED_CUISINES = {
    "mexican": uuid.UUID("20000000-0000-0000-0000-000000000001"),
    "chinese": uuid.UUID("20000000-0000-0000-0000-000000000002"),
    "japanese": uuid.UUID("20000000-0000-0000-0000-000000000003"),
    "italian": uuid.UUID("20000000-0000-0000-0000-000000000004"),
    "vietnamese": uuid.UUID("20000000-0000-0000-0000-000000000005"),
    "thai": uuid.UUID("20000000-0000-0000-0000-000000000006"),
    "american": uuid.UUID("20000000-0000-0000-0000-000000000007"),
    "indian": uuid.UUID("20000000-0000-0000-0000-000000000008"),
    "korean": uuid.UUID("20000000-0000-0000-0000-000000000009"),
    "mediterranean": uuid.UUID("20000000-0000-0000-0000-000000000010"),
}


@dataclass(frozen=True)
class FixtureCuisine:
    id: uuid.UUID
    slug: str
    display_name: str


@dataclass(frozen=True)
class FixturePlace:
    id: uuid.UUID
    canonical_name: str
    longitude: float
    latitude: float
    address: str
    cuisine_slug: str
    quality_score: float  # [0, 1] stored in metadata
    provider_place_id: str


CUISINES: list[FixtureCuisine] = [
    FixtureCuisine(_SEED_CUISINES["mexican"], "mexican", "Mexican"),
    FixtureCuisine(_SEED_CUISINES["chinese"], "chinese", "Chinese"),
    FixtureCuisine(_SEED_CUISINES["japanese"], "japanese", "Japanese"),
    FixtureCuisine(_SEED_CUISINES["italian"], "italian", "Italian"),
    FixtureCuisine(_SEED_CUISINES["vietnamese"], "vietnamese", "Vietnamese"),
    FixtureCuisine(_SEED_CUISINES["thai"], "thai", "Thai"),
    FixtureCuisine(_SEED_CUISINES["american"], "american", "American"),
    FixtureCuisine(_SEED_CUISINES["indian"], "indian", "Indian"),
    FixtureCuisine(_SEED_CUISINES["korean"], "korean", "Korean"),
    FixtureCuisine(_SEED_CUISINES["mediterranean"], "mediterranean", "Mediterranean"),
]

# Mission District / Castro, San Francisco (fictional names)
# Coordinates roughly centered on 37.759°N 122.419°W
PLACES: list[FixturePlace] = [
    FixturePlace(
        _SEED_PLACES[0],
        "La Paloma Tacos",
        -122.4194,
        37.7599,
        "3241 Mission St, SF",
        "mexican",
        0.85,
        "fix-001",
    ),
    FixturePlace(
        _SEED_PLACES[1],
        "Taqueria El Sol",
        -122.4218,
        37.7623,
        "2987 24th St, SF",
        "mexican",
        0.78,
        "fix-002",
    ),
    FixturePlace(
        _SEED_PLACES[2],
        "Carnitas Fuentes",
        -122.4150,
        37.7567,
        "518 Valencia St, SF",
        "mexican",
        0.72,
        "fix-003",
    ),
    FixturePlace(
        _SEED_PLACES[3],
        "Golden Dragon",
        -122.4091,
        37.7612,
        "4199 18th St, SF",
        "chinese",
        0.80,
        "fix-004",
    ),
    FixturePlace(
        _SEED_PLACES[4],
        "Panda House Kitchen",
        -122.4233,
        37.7555,
        "655 Castro St, SF",
        "chinese",
        0.68,
        "fix-005",
    ),
    FixturePlace(
        _SEED_PLACES[5],
        "Sakura Ramen",
        -122.4175,
        37.7640,
        "3301 24th St, SF",
        "japanese",
        0.88,
        "fix-006",
    ),
    FixturePlace(
        _SEED_PLACES[6],
        "Nori Sushi Bar",
        -122.4205,
        37.7580,
        "401 Guerrero St, SF",
        "japanese",
        0.75,
        "fix-007",
    ),
    FixturePlace(
        _SEED_PLACES[7],
        "Trattoria Bella",
        -122.4162,
        37.7598,
        "3100 16th St, SF",
        "italian",
        0.82,
        "fix-008",
    ),
    FixturePlace(
        _SEED_PLACES[8],
        "Pasta Nonna",
        -122.4240,
        37.7635,
        "200 Noe St, SF",
        "italian",
        0.70,
        "fix-009",
    ),
    FixturePlace(
        _SEED_PLACES[9],
        "Pho 24 Bowl",
        -122.4190,
        37.7610,
        "1987 Mission St, SF",
        "vietnamese",
        0.79,
        "fix-010",
    ),
    FixturePlace(
        _SEED_PLACES[10],
        "Banh Mi Brothers",
        -122.4210,
        37.7575,
        "776 Valencia St, SF",
        "vietnamese",
        0.73,
        "fix-011",
    ),
    FixturePlace(
        _SEED_PLACES[11],
        "Spice & Lime Thai",
        -122.4180,
        37.7590,
        "901 Guerrero St, SF",
        "thai",
        0.81,
        "fix-012",
    ),
    FixturePlace(
        _SEED_PLACES[12],
        "Bangkok Corner",
        -122.4225,
        37.7620,
        "3400 18th St, SF",
        "thai",
        0.66,
        "fix-013",
    ),
    FixturePlace(
        _SEED_PLACES[13],
        "The Mission Diner",
        -122.4145,
        37.7615,
        "2201 Mission St, SF",
        "american",
        0.74,
        "fix-014",
    ),
    FixturePlace(
        _SEED_PLACES[14],
        "Castro Burger Co.",
        -122.4195,
        37.7641,
        "503 Castro St, SF",
        "american",
        0.71,
        "fix-015",
    ),
    FixturePlace(
        _SEED_PLACES[15],
        "Taj Mahal Curry",
        -122.4155,
        37.7572,
        "2888 24th St, SF",
        "indian",
        0.84,
        "fix-016",
    ),
    FixturePlace(
        _SEED_PLACES[16],
        "Saffron Palace",
        -122.4237,
        37.7600,
        "4050 18th St, SF",
        "indian",
        0.76,
        "fix-017",
    ),
    FixturePlace(
        _SEED_PLACES[17],
        "Seoul Garden",
        -122.4200,
        37.7558,
        "188 Dolores St, SF",
        "korean",
        0.83,
        "fix-018",
    ),
    FixturePlace(
        _SEED_PLACES[18],
        "Olive & Vine",
        -122.4168,
        37.7630,
        "3505 17th St, SF",
        "mediterranean",
        0.77,
        "fix-019",
    ),
    FixturePlace(
        _SEED_PLACES[19],
        "Mezze House",
        -122.4220,
        37.7588,
        "600 Guerrero St, SF",
        "mediterranean",
        0.69,
        "fix-020",
    ),
]
