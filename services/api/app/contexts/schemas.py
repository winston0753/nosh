from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ContextCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    meal_type: str = Field(pattern="^(lunch|dinner|brunch)$")
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    radius_meters: int = Field(default=1600, ge=100, le=50000)
    local_window_start: str = Field(pattern="^\\d{2}:\\d{2}$")
    local_window_end: str = Field(pattern="^\\d{2}:\\d{2}$")
    time_zone: str = Field(min_length=1)
    active_days: Annotated[list[int], Field(min_length=1)] = Field(default=[0, 1, 2, 3, 4, 5, 6])
    notifications_enabled: bool = True


class ContextUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    meal_type: str | None = Field(default=None, pattern="^(lunch|dinner|brunch)$")
    radius_meters: int | None = Field(default=None, ge=100, le=50000)
    local_window_start: str | None = Field(default=None, pattern="^\\d{2}:\\d{2}$")
    local_window_end: str | None = Field(default=None, pattern="^\\d{2}:\\d{2}$")
    time_zone: str | None = None
    active_days: list[int] | None = None
    notifications_enabled: bool | None = None


class ContextResponse(BaseModel):
    id: uuid.UUID
    name: str
    meal_type: str
    longitude: float
    latitude: float
    radius_meters: int
    local_window_start: str
    local_window_end: str
    time_zone: str
    active_days: list[int]
    notifications_enabled: bool
    version: int
    disabled_at: datetime | None
    created_at: datetime
