from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt, ValidationInfo, field_validator

from app.contexts import validation

MealType = Literal["lunch", "dinner", "brunch"]


class ContextCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    meal_type: MealType
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    radius_meters: int = Field(default=1600, ge=100, le=50000)
    local_window_start: str
    local_window_end: str
    time_zone: str
    active_days: Annotated[list[StrictInt], Field(min_length=1, max_length=7)] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5, 6]
    )
    notifications_enabled: bool = True

    @field_validator("local_window_start", "local_window_end")
    @classmethod
    def _check_time(cls, value: str) -> str:
        validation.parse_local_time(value)
        return value

    @field_validator("time_zone")
    @classmethod
    def _check_zone(cls, value: str) -> str:
        return validation.validate_time_zone(value)

    @field_validator("active_days")
    @classmethod
    def _check_days(cls, value: list[int]) -> list[int]:
        return validation.validate_active_days(value)

    @field_validator("local_window_end")
    @classmethod
    def _check_window(cls, value: str, info: ValidationInfo) -> str:
        # Runs after _check_time; the start is absent from info.data if it was
        # itself invalid, in which case that error is already reported.
        start = info.data.get("local_window_start")
        if start is not None:
            validation.validate_window(start, value)
        return value


class ContextUpdate(BaseModel):
    """Partial update.  Cross-field window rules are checked against the stored
    context in the service, because either bound may be omitted here."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    meal_type: MealType | None = None
    radius_meters: int | None = Field(default=None, ge=100, le=50000)
    local_window_start: str | None = None
    local_window_end: str | None = None
    time_zone: str | None = None
    active_days: Annotated[list[StrictInt], Field(min_length=1, max_length=7)] | None = None
    notifications_enabled: bool | None = None

    @field_validator("local_window_start", "local_window_end")
    @classmethod
    def _check_time(cls, value: str | None) -> str | None:
        if value is not None:
            validation.parse_local_time(value)
        return value

    @field_validator("time_zone")
    @classmethod
    def _check_zone(cls, value: str | None) -> str | None:
        return None if value is None else validation.validate_time_zone(value)

    @field_validator("active_days")
    @classmethod
    def _check_days(cls, value: list[int] | None) -> list[int] | None:
        return None if value is None else validation.validate_active_days(value)


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
