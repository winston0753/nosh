from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str | None
    onboarding_state: str
    created_at: datetime

    model_config = {"from_attributes": True}
