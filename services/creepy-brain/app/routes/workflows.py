"""Workflow management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowRunResponse(BaseModel):
    workflow_run_id: str


@router.post("/test", response_model=WorkflowRunResponse)  # type: ignore[untyped-decorator]
async def trigger_test_workflow() -> WorkflowRunResponse:
    """Trigger the test workflow to verify the Hatchet setup works end-to-end.

    Only available when DEV_MODE=true.
    """
    if not settings.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")

    from app.workflows.test_workflow import test_workflow

    run_ref = await test_workflow.aio_run_no_wait()
    return WorkflowRunResponse(workflow_run_id=run_ref.workflow_run_id)
