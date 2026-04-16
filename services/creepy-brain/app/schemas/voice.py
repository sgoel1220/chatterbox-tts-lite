"""Voice API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VoiceResponse(BaseModel):
    """Voice response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    audio_path: str
    is_default: bool
    created_at: datetime


class CreateVoiceResponse(BaseModel):
    """Response for voice upload — includes a created flag for idempotency."""

    voice: VoiceResponse
    created: bool


class CreateVoiceRequest(BaseModel):
    """Request body fields for creating a voice (non-file fields)."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: bool = False
