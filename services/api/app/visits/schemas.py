from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    place_id: uuid.UUID
    # proposal_id is optional: omit for a manual visit the user logged
    # independently of Nosh.  When provided, the proposal must belong to the
    # user and its session must be in state 'accepted'.  See DECISIONS.md D015.
    proposal_id: uuid.UUID | None = Field(
        default=None,
        description="Omit for manual visits not originating from a Nosh Go response.",
    )
    visited_at: datetime
    rating: Literal["positive", "negative"]
    confirmation_source: Literal["app_confirmation", "manual"] = "app_confirmation"


class VisitUpdate(BaseModel):
    rating: Literal["positive", "negative"] | None = None
    visited_at: datetime | None = None


class VisitResponse(BaseModel):
    id: uuid.UUID
    place_id: uuid.UUID
    place_name: str
    proposal_id: uuid.UUID | None
    visited_at: datetime
    rating: str | None
    confirmation_source: str
    created_at: datetime
    corrected_at: datetime | None


class ProgressResponse(BaseModel):
    month: str  # YYYY-MM
    confirmed_positive_new_count: int
    total_confirmed_count: int
