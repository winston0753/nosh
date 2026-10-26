from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SessionCreateRequest(BaseModel):
    """Open (or fetch) the session for one meal window.

    Give exactly one anchor: ``location`` (the device's foreground location,
    transient: never logged or stored) or ``anchor`` (a saved Home/Work spot,
    used when location is unavailable).  Once a session exists, later requests
    for the same window return it unchanged whatever anchor they give.
    """

    meal_window_key: str = Field(
        description="YYYY-MM-DD#meal_type, e.g. 2026-10-12#lunch",
        pattern=r"^\d{4}-\d{2}-\d{2}#(lunch|dinner)$",
    )
    location: Coordinate | None = None
    anchor: Literal["home", "work"] | None = None

    @model_validator(mode="after")
    def _one_anchor(self) -> SessionCreateRequest:
        if (self.location is None) == (self.anchor is None):
            raise ValueError("give exactly one of location or anchor")
        return self


class ProposalResponse_Schema(BaseModel):
    id: uuid.UUID
    place_id: uuid.UUID
    place_name: str
    cuisine_name: str
    distance_meters: float
    address: str | None
    reason_codes: list[str]
    sequence_number: int
    total_score: float
    score_components: dict[str, float]

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: uuid.UUID
    meal_window_key: str
    # device, home, or work (legacy_context for sessions migrated from contexts)
    anchor_source: str
    state: str
    policy_version: str
    current_proposal: ProposalResponse_Schema | None
    created_at: datetime


class ResponseRequest(BaseModel):
    response: Literal["go", "another", "not_today", "been_here"]
    client_event_id: str = Field(min_length=1, max_length=255)


class ResponseResult(BaseModel):
    response: str
    session_state: str
    next_proposal: ProposalResponse_Schema | None = None
    no_candidates: bool = False
