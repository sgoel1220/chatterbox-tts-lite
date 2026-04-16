"""Blob API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import BlobType


class BlobResponse(BaseModel):
    """Audio/image blob response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    blob_type: BlobType
    mime_type: str
    size_bytes: int
    created_at: datetime
