from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.contexts.models import DiningContext
from app.contexts.service import get_context_for_user
from app.core.database import get_db
from app.places import schemas, service

router = APIRouter(tags=["places"])


@router.get(
    "/contexts/{context_id}/onboarding-places",
    response_model=list[schemas.OnboardingPlaceResponse],
)
async def get_onboarding_places(
    context_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, le=100),
) -> list[schemas.OnboardingPlaceResponse]:
    ctx = await get_context_for_user(db, context_id, current_user)

    result = await db.execute(
        select(
            func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lon"),
            func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lat"),
        ).where(DiningContext.id == context_id)
    )
    row = result.one()
    lon, lat = float(row.lon), float(row.lat)

    places = await service.get_onboarding_places(
        db, current_user, lon, lat, float(ctx.radius_meters), limit=limit
    )

    out: list[schemas.OnboardingPlaceResponse] = []
    for place, dist, state in places:
        primary_cuisine = None
        for pc in place.cuisines:
            if pc.is_primary and pc.cuisine:
                primary_cuisine = pc.cuisine.display_name
                break
        out.append(
            schemas.OnboardingPlaceResponse(
                place=schemas.PlaceResponse.model_validate(place),
                distance_meters=dist,
                primary_cuisine=primary_cuisine,
                state=state,
            )
        )
    return out


@router.put(
    "/contexts/{context_id}/onboarding-places/{place_id}/state",
    response_model=schemas.PlaceStateResponse,
)
async def classify_onboarding_place(
    context_id: uuid.UUID,
    place_id: uuid.UUID,
    body: schemas.PlaceStateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlaceStateResponse:
    """Onboarding classification: records source='onboarding' provenance."""
    row = await service.classify_onboarding_place(
        db, current_user, context_id, place_id, body.state
    )
    return schemas.PlaceStateResponse.model_validate(row)


@router.put(
    "/places/{place_id}/state",
    response_model=schemas.PlaceStateResponse,
)
async def set_place_state(
    place_id: uuid.UUID,
    body: schemas.PlaceStateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlaceStateResponse:
    """Manual place-state edit (settings).  Never marks a place as pre-Nosh."""
    row = await service.set_user_place_state(db, current_user, place_id, body.state)
    return schemas.PlaceStateResponse.model_validate(row)
