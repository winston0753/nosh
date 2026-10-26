from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.places import schemas, service

router = APIRouter(tags=["places"])


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
