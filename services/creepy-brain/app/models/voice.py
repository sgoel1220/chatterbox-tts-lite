"""Voice model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Voice(BaseModel):
    """Voice reference for TTS.

    A voice has either:
    - ``audio_path``: a filesystem path to a built-in voice file, or
    - ``audio_blob_id``: a FK to a workflow_blobs row for uploaded voice audio.

    Exactly one of the two should be non-null for any given row, but both are
    nullable so that either storage mode can be used independently.

    The partial unique index ``uq_voices_single_default`` ensures at most one
    row can have ``is_default = true``.
    """

    __tablename__ = "voices"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Built-in file voices: local filesystem path.
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Uploaded blob voices: explicit FK to workflow_blobs.
    audio_blob_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_blobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_voices_audio_blob", "audio_blob_id"),
        # Partial unique index: only one row may have is_default = TRUE.
        # Cannot be expressed as a SQLAlchemy UniqueConstraint with a WHERE clause
        # in a cross-DB way; it is created via raw DDL in migration 0007.
    )
