"""Voice API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VoiceResponse(BaseModel):
    """Voice response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    # audio_path holds a filesystem path for built-in voices; None for uploaded voices.
    audio_path: str | None = None
    # audio_blob_id holds the blob UUID for uploaded voices; None for built-in voices.
    audio_blob_id: uuid.UUID | None = None
    is_default: bool
    created_at: datetime


class CreateVoiceResponse(BaseModel):
    """Response for voice upload — includes a created flag for idempotency."""

    voice: VoiceResponse
    created: bool


class CreateVoiceRequest(BaseModel):
    """Request body fields for creating a voice (non-file fields)."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    is_default: bool = False
