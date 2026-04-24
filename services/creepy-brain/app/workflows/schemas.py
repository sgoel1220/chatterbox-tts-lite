"""Shared workflow input/output schemas."""

from pydantic import BaseModel


class EmptyWorkflowInput(BaseModel):
    """Input schema for workflows that take no parameters (e.g. recon)."""


class ReconStepOutput(BaseModel):
    """Output from the recon step."""

    db_checked: int
    provider_untracked: int
    terminated: int
