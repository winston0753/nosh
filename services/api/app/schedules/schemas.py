from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt, ValidationInfo, field_validator

from app.schedules import validation

MealType = Literal["lunch", "dinner"]
AnchorKind = Literal["home", "work"]


class MealPlanIn(BaseModel):
    meal_type: MealType
    enabled: bool
    local_window_start: str
    local_window_end: str
    active_days: Annotated[list[StrictInt], Field(min_length=1, max_length=7)]
    price_ceiling: int | None = Field(default=None, ge=1, le=4)
    notifications_enabled: bool = True

    @field_validator("local_window_start", "local_window_end")
    @classmethod
    def _check_time(cls, value: str) -> str:
        validation.parse_local_time(value)
        return value

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


class MealScheduleUpdate(BaseModel):
    """Full replacement of the user's meal schedule (idempotent PUT).

    Meal types left out are removed.  Overlap between enabled meals is checked
    in the service so the error can name the offending field.
    """

    time_zone: str
    meals: Annotated[list[MealPlanIn], Field(min_length=1, max_length=2)]

    @field_validator("time_zone")
    @classmethod
    def _check_zone(cls, value: str) -> str:
        return validation.validate_time_zone(value)

    @field_validator("meals")
    @classmethod
    def _check_unique(cls, value: list[MealPlanIn]) -> list[MealPlanIn]:
        types = [m.meal_type for m in value]
        if len(set(types)) != len(types):
            raise ValueError("each meal_type may appear only once")
        return value


class MealPlan(BaseModel):
    meal_type: MealType
    enabled: bool
    local_window_start: str
    local_window_end: str
    time_zone: str
    active_days: list[int]
    price_ceiling: int | None
    notifications_enabled: bool
    version: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealScheduleResponse(BaseModel):
    """``meals`` is empty until the user completes the schedule survey."""

    meals: list[MealPlan]


class AnchorIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AnchorResponse(BaseModel):
    kind: AnchorKind
    latitude: float
    longitude: float
    updated_at: datetime
