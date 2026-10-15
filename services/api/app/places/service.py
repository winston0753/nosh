from __future__ import annotations

import uuid

from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromText
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.places.models import Cuisine, Place, PlaceCuisine, PlaceSource, UserPlaceState
from app.recommendations.types import CandidatePlace


async def load_fixture_data(db: AsyncSession) -> None:
    """Idempotently load fixture places and cuisines into the database."""
    from app.places.fixtures import CUISINES, PLACES

    for fc in CUISINES:
        existing = await db.execute(select(Cuisine).where(Cuisine.id == fc.id))
        if existing.scalar_one_or_none() is None:
            db.add(Cuisine(id=fc.id, slug=fc.slug, display_name=fc.display_name))

    await db.flush()

    cuisine_by_slug: dict[str, Cuisine] = {}
    for row in (await db.execute(select(Cuisine))).scalars().all():
        cuisine_by_slug[row.slug] = row

    for fp in PLACES:
        existing = await db.execute(select(Place).where(Place.id == fp.id))
        if existing.scalar_one_or_none() is None:
            place = Place(
                id=fp.id,
                canonical_name=fp.canonical_name,
                location=f"SRID=4326;POINT({fp.longitude} {fp.latitude})",
                address=fp.address,
                status="active",
                metadata_={"quality_score": fp.quality_score},
            )
            db.add(place)
            await db.flush()

            source = PlaceSource(
                place_id=fp.id,
                provider="fixture",
                provider_place_id=fp.provider_place_id,
            )
            db.add(source)

            cuisine = cuisine_by_slug.get(fp.cuisine_slug)
            if cuisine:
                db.add(PlaceCuisine(place_id=fp.id, cuisine_id=cuisine.id, is_primary=True))

    await db.commit()


async def get_places_within_radius(
    db: AsyncSession,
    longitude: float,
    latitude: float,
    radius_meters: float,
) -> list[tuple[Place, float]]:
    """Return active places within radius, with distance in meters."""
    center = ST_GeogFromText(f"SRID=4326;POINT({longitude} {latitude})")
    result = await db.execute(
        select(Place, ST_Distance(Place.location, center).label("distance_m"))
        .where(
            Place.status == "active",
            ST_DWithin(Place.location, center, radius_meters),
        )
        .options(selectinload(Place.cuisines).selectinload(PlaceCuisine.cuisine))
        .order_by("distance_m")
    )
    return [(row.Place, row.distance_m) for row in result.all()]


async def get_user_place_states(
    db: AsyncSession, user_id: uuid.UUID, place_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Return the user's state for each place: visited/not_interested/unknown."""
    if not place_ids:
        return {}
    result = await db.execute(
        select(UserPlaceState).where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.place_id.in_(place_ids),
        )
    )
    return {row.place_id: row.state for row in result.scalars().all()}


async def set_user_place_state(
    db: AsyncSession,
    user_id: uuid.UUID,
    place_id: uuid.UUID,
    state: str,
    source: str,
) -> UserPlaceState:
    """Upsert the user's place state."""
    from datetime import UTC, datetime

    result = await db.execute(
        select(UserPlaceState).where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.place_id == place_id,
        )
    )
    row = result.scalar_one_or_none()
    was_before = source == "onboarding" and state == "visited"
    if row is None:
        row = UserPlaceState(
            user_id=user_id,
            place_id=place_id,
            state=state,
            source=source,
            was_visited_before_nosh=was_before,
            occurred_at=datetime.now(UTC),
        )
        db.add(row)
    else:
        row.state = state
        row.source = source
        row.occurred_at = datetime.now(UTC)
        # Never reset was_visited_before_nosh once TRUE.
        if was_before:
            row.was_visited_before_nosh = True
    await db.commit()
    await db.refresh(row)
    return row


async def build_candidates(
    db: AsyncSession,
    user_id: uuid.UUID,
    longitude: float,
    latitude: float,
    radius_meters: float,
    already_proposed_place_ids: set[uuid.UUID],
) -> list[CandidatePlace]:
    """Return eligible candidates after applying hard eligibility filters."""
    places_with_distance = await get_places_within_radius(db, longitude, latitude, radius_meters)
    place_ids = [p.id for p, _ in places_with_distance]
    user_states = await get_user_place_states(db, user_id, place_ids)

    candidates: list[CandidatePlace] = []
    for place, distance_m in places_with_distance:
        # Hard filters
        if place.status != "active":
            continue
        if user_states.get(place.id) in ("visited", "not_interested"):
            continue
        if place.id in already_proposed_place_ids:
            continue
        if not place.cuisines:
            continue

        # Use primary cuisine if available, else first
        primary_pcs = [pc for pc in place.cuisines if pc.is_primary]
        pc = primary_pcs[0] if primary_pcs else place.cuisines[0]

        quality = 0.5
        if place.metadata_ and "quality_score" in place.metadata_:
            quality = float(place.metadata_["quality_score"])  # type: ignore[arg-type]

        candidates.append(
            CandidatePlace(
                place_id=place.id,
                cuisine_id=pc.cuisine_id,
                cuisine_slug=pc.cuisine.slug if pc.cuisine else "",
                distance_meters=float(distance_m),
                quality_score=quality,
                is_primary_cuisine=pc.is_primary,
            )
        )

    return candidates


async def get_onboarding_places(
    db: AsyncSession,
    user_id: uuid.UUID,
    longitude: float,
    latitude: float,
    radius_meters: float,
    limit: int = 50,
) -> list[tuple[Place, float, str]]:
    """Return nearby places with their current user state for onboarding."""
    places_with_distance = await get_places_within_radius(db, longitude, latitude, radius_meters)
    place_ids = [p.id for p, _ in places_with_distance]
    user_states = await get_user_place_states(db, user_id, place_ids)

    result = []
    for place, distance_m in places_with_distance[:limit]:
        state = user_states.get(place.id, "unknown")
        result.append((place, float(distance_m), state))
    return result
