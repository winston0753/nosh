from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


class CuisineResponse(BaseModel):
    id: uuid.UUID
    slug: str
    display_name: str

    model_config = {"from_attributes": True}


class PlaceResponse(BaseModel):
    id: uuid.UUID
    canonical_name: str
    address: str | None
    status: str

    model_config = {"from_attributes": True}


class OnboardingPlaceResponse(BaseModel):
    place: PlaceResponse
    distance_meters: float
    primary_cuisine: str | None
    state: Literal["unknown", "visited", "not_interested"]


class PlaceStateRequest(BaseModel):
    state: Literal["visited", "not_interested", "unknown"]


class PlaceStateResponse(BaseModel):
    place_id: uuid.UUID
    state: str
    source: str
