"""API schemas (Pydantic request/response models)."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""

    status: str


class ServiceInfo(BaseModel):
    """Service information response"""

    service: str
    version: str
    status: str
