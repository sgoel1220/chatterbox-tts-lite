"""Blob streaming endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import Response

from app.db import DbSession
from app.services import blob_service

router = APIRouter(prefix="/api/blobs", tags=["blobs"])


@router.get("/{blob_id}")
async def get_blob(blob_id: uuid.UUID, session: DbSession) -> Response:
    """Return binary blob data with its stored MIME type."""
    blob = await blob_service.get(session, blob_id)
    return Response(
        content=blob.data,
        media_type=blob.mime_type,
        headers={"Content-Length": str(blob.size_bytes)},
    )
