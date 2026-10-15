from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    dining_context_id: uuid.UUID
    meal_window_key: str = Field(
        description="YYYY-MM-DD#meal_type, e.g. 2026-10-12#dinner",
        pattern=r"^\d{4}-\d{2}-\d{2}#(lunch|dinner|brunch)$",
    )


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
    dining_context_id: uuid.UUID
    meal_window_key: str
    state: str
    policy_version: str
    current_proposal: ProposalResponse_Schema | None
    created_at: datetime


class ResponseRequest(BaseModel):
    response: Literal["go", "another", "not_today"]
    client_event_id: str = Field(min_length=1, max_length=255)


class ResponseResult(BaseModel):
    response: str
    session_state: str
    next_proposal: ProposalResponse_Schema | None = None
    no_candidates: bool = False
