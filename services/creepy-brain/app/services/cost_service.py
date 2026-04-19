"""GPU cost tracking service."""

import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GpuPodStatus, GpuProvider
from app.models.gpu_pod import GpuPod
from app.models.llm_usage import LlmUsage


class CostSummary(BaseModel):
    """Aggregated cost summary."""

    today_cents: int
    month_cents: int
    active_pod_count: int


class WorkflowCost(BaseModel):
    """Cost for a single workflow (GPU + LLM)."""

    workflow_id: str
    gpu_cost_cents: int
    llm_cost_cents: int
    total_cost_cents: int
    pod_count: int


class CostService:
    """Tracks GPU pod costs.

    NOTE: This service commits its own transactions (self-committing).
    This is an intentional deviation from the flush-only convention used
    by other services, because cost mutations must be durable even if the
    caller's outer transaction rolls back (e.g. pod terminated but step fails).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_pod(
        self,
        pod_id: str,
        provider: GpuProvider,
        workflow_id: uuid.UUID | None,
        gpu_type: str | None,
        cost_per_hour_cents: int | None,
        endpoint_url: str | None = None,
        status: GpuPodStatus = GpuPodStatus.CREATING,
    ) -> GpuPod:
        """Insert or update a pod record in the database."""
        existing = await self._session.get(GpuPod, pod_id)
        if existing is not None:
            existing.status = status
            if endpoint_url:
                existing.endpoint_url = endpoint_url
            if cost_per_hour_cents is not None:
                existing.cost_per_hour_cents = cost_per_hour_cents
            await self._session.commit()
            return existing

        pod = GpuPod(
            id=pod_id,
            provider=provider,
            workflow_id=workflow_id,
            status=status,
            gpu_type=gpu_type,
            cost_per_hour_cents=cost_per_hour_cents,
            endpoint_url=endpoint_url,
        )
        self._session.add(pod)
        await self._session.commit()
        return pod

    async def mark_ready(self, pod_id: str, endpoint_url: str | None = None) -> None:
        """Mark a pod as ready and start cost tracking."""
        pod = await self._session.get(GpuPod, pod_id)
        if pod is None:
            return
        pod.status = GpuPodStatus.READY
        pod.ready_at = datetime.now(timezone.utc)
        if endpoint_url:
            pod.endpoint_url = endpoint_url
        await self._session.commit()

    async def finalize_cost(
        self,
        pod_id: str,
        reason: str = "normal",
    ) -> int:
        """Calculate and store final cost when a pod is terminated.

        Returns total cost in cents.
        """
        pod = await self._session.get(GpuPod, pod_id)
        if pod is None:
            return 0

        now = datetime.now(timezone.utc)
        pod.status = GpuPodStatus.TERMINATED
        pod.terminated_at = now
        pod.termination_reason = reason

        if pod.ready_at and pod.cost_per_hour_cents:
            runtime_hours = (now - pod.ready_at).total_seconds() / 3600
            pod.total_cost_cents = int(runtime_hours * pod.cost_per_hour_cents)

        await self._session.commit()
        return pod.total_cost_cents

    async def get_workflow_cost(self, workflow_id: uuid.UUID) -> WorkflowCost:
        """Return GPU + LLM cost breakdown for a workflow."""
        gpu_result = await self._session.execute(
            select(
                func.coalesce(func.sum(GpuPod.total_cost_cents), 0),
                func.count(GpuPod.id),
            ).where(GpuPod.workflow_id == workflow_id)
        )
        gpu_row = gpu_result.one()
        gpu_cents = int(gpu_row[0])
        pod_count = int(gpu_row[1])

        llm_result = await self._session.execute(
            select(func.coalesce(func.sum(LlmUsage.cost_cents), 0)).where(
                LlmUsage.workflow_id == workflow_id
            )
        )
        llm_cents = int(llm_result.scalar_one())

        return WorkflowCost(
            workflow_id=str(workflow_id),
            gpu_cost_cents=gpu_cents,
            llm_cost_cents=llm_cents,
            total_cost_cents=gpu_cents + llm_cents,
            pod_count=pod_count,
        )

    async def get_summary(self) -> CostSummary:
        """Get aggregated cost summary (today, month, active pods). Includes GPU + LLM."""
        today = date.today()
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time(), timezone.utc)

        gpu_today_result = await self._session.execute(
            select(func.coalesce(func.sum(GpuPod.total_cost_cents), 0)).where(
                func.date(GpuPod.created_at) == today
            )
        )
        gpu_today = int(gpu_today_result.scalar_one())

        gpu_month_result = await self._session.execute(
            select(func.coalesce(func.sum(GpuPod.total_cost_cents), 0)).where(
                GpuPod.created_at >= month_start_dt
            )
        )
        gpu_month = int(gpu_month_result.scalar_one())

        llm_today_result = await self._session.execute(
            select(func.coalesce(func.sum(LlmUsage.cost_cents), 0)).where(
                func.date(LlmUsage.created_at) == today
            )
        )
        llm_today = int(llm_today_result.scalar_one())

        llm_month_result = await self._session.execute(
            select(func.coalesce(func.sum(LlmUsage.cost_cents), 0)).where(
                LlmUsage.created_at >= month_start_dt
            )
        )
        llm_month = int(llm_month_result.scalar_one())

        active_result = await self._session.execute(
            select(func.count(GpuPod.id)).where(
                GpuPod.status.notin_([GpuPodStatus.TERMINATED, GpuPodStatus.ERROR])
            )
        )
        active_count = int(active_result.scalar_one())

        return CostSummary(
            today_cents=gpu_today + llm_today,
            month_cents=gpu_month + llm_month,
            active_pod_count=active_count,
        )
