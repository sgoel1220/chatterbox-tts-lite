"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db import DbSession
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
async def readyz(session: DbSession) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ok")
