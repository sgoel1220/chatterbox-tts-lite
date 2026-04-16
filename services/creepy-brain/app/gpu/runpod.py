"""RunPod GPU provider implementation using the RunPod GraphQL API."""

import asyncio
from datetime import datetime, timezone

import httpx

from .base import GpuPod, GpuPodSpec, GpuProvider, PodStatus

RUNPOD_API = "https://api.runpod.io/graphql"

_CREATE_POD_MUTATION = """
mutation CreatePod($input: PodRentInterruptableInput!) {
    podRentInterruptable(input: $input) {
        id
        name
        desiredStatus
        machine { gpuDisplayName costPerGpu }
    }
}
"""

_GET_POD_QUERY = """
query GetPod($id: String!) {
    pod(input: {podId: $id}) {
        id
        name
        desiredStatus
        runtime {
            ports { ip privatePort publicPort isIpPublic type }
        }
        machine { gpuDisplayName costPerGpu }
    }
}
"""

_TERMINATE_POD_MUTATION = """
mutation TerminatePod($id: String!) {
    podTerminate(input: {podId: $id})
}
"""

_LIST_PODS_QUERY = """
query ListPods {
    myself {
        pods {
            id
            name
            desiredStatus
            runtime {
                ports { ip privatePort publicPort isIpPublic type }
            }
            machine { gpuDisplayName costPerGpu }
        }
    }
}
"""


class RunPodProvider(GpuProvider):
    """GPU provider backed by RunPod's GraphQL API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def _gql(
        self,
        query: str,
        variables: dict[str, object] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = await self._client.post(RUNPOD_API, json=payload)
        resp.raise_for_status()
        body: dict[str, object] = resp.json()
        if "errors" in body:
            raise RuntimeError(f"RunPod GraphQL error: {body['errors']}")
        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected RunPod response shape: {body}")
        return data

    def _parse_pod(self, raw: dict[str, object]) -> GpuPod:
        pod_id = str(raw["id"])
        desired = str(raw.get("desiredStatus", ""))

        if desired == "RUNNING":
            status = PodStatus.RUNNING
        elif desired in ("EXITED", "TERMINATED"):
            status = PodStatus.TERMINATED
        else:
            status = PodStatus.CREATING

        endpoint_url: str | None = None
        runtime = raw.get("runtime")
        if isinstance(runtime, dict):
            for port in runtime.get("ports") or []:
                if (
                    isinstance(port, dict)
                    and port.get("privatePort") == 8005
                    and port.get("isIpPublic")
                ):
                    ip = port.get("ip", "")
                    public_port = port.get("publicPort", 8005)
                    endpoint_url = f"http://{ip}:{public_port}"
                    break

        machine = raw.get("machine") if isinstance(raw.get("machine"), dict) else {}
        assert isinstance(machine, dict)
        gpu_type: str | None = str(machine["gpuDisplayName"]) if "gpuDisplayName" in machine else None
        cost_raw = machine.get("costPerGpu")
        cost_cents: int | None = int(float(cost_raw) * 100) if cost_raw is not None else None

        return GpuPod(
            id=pod_id,
            provider="runpod",
            status=status,
            endpoint_url=endpoint_url,
            gpu_type=gpu_type,
            cost_per_hour_cents=cost_cents,
            created_at=datetime.now(timezone.utc),
        )

    async def _find_pod_by_name(self, name: str) -> GpuPod | None:
        data = await self._gql(_LIST_PODS_QUERY)
        myself = data.get("myself")
        if not isinstance(myself, dict):
            return None
        for raw in myself.get("pods") or []:
            if isinstance(raw, dict) and raw.get("name") == name:
                return self._parse_pod(raw)
        return None

    async def create_pod(self, spec: GpuPodSpec, idempotency_key: str) -> GpuPod:
        existing = await self._find_pod_by_name(idempotency_key)
        if existing and existing.status != PodStatus.TERMINATED:
            return existing

        env_list = [{"key": k, "value": v} for k, v in spec.env.items()]
        ports_str = ",".join(f"{p}/http" for p in spec.ports)

        variables: dict[str, object] = {
            "input": {
                "name": idempotency_key,
                "imageName": spec.image,
                "gpuTypeId": spec.gpu_type,
                "containerDiskInGb": spec.disk_size_gb,
                "ports": ports_str,
                "env": env_list,
            }
        }
        try:
            data = await self._gql(_CREATE_POD_MUTATION, variables)
            raw = data.get("podRentInterruptable")
            if not isinstance(raw, dict):
                raise RuntimeError(f"Unexpected create_pod response: {data}")
            return self._parse_pod(raw)
        except Exception:
            # On any error (including concurrent creation), re-check by name before
            # re-raising — a concurrent caller may have already created the pod.
            recovered = await self._find_pod_by_name(idempotency_key)
            if recovered and recovered.status != PodStatus.TERMINATED:
                return recovered
            raise

    async def get_pod(self, pod_id: str) -> GpuPod | None:
        data = await self._gql(_GET_POD_QUERY, {"id": pod_id})
        raw = data.get("pod")
        if not isinstance(raw, dict):
            return None
        return self._parse_pod(raw)

    async def terminate_pod(self, pod_id: str) -> bool:
        data = await self._gql(_TERMINATE_POD_MUTATION, {"id": pod_id})
        # RunPod returns the pod id string on success or null/false on failure.
        result = data.get("podTerminate")
        return bool(result)

    async def wait_for_ready(self, pod_id: str, timeout_sec: int = 300) -> GpuPod:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        while loop.time() < deadline:
            pod = await self.get_pod(pod_id)
            if pod and pod.endpoint_url:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as probe:
                        # Probe /api/model-info (guaranteed to exist in the TTS server)
                        # and require HTTP 200 so a bare-HTTP-server 404 is not accepted.
                        r = await probe.get(f"{pod.endpoint_url}/api/model-info")
                        if r.status_code == 200:
                            pod.status = PodStatus.READY
                            return pod
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass
            await asyncio.sleep(10)
        raise TimeoutError(f"Pod {pod_id} did not become ready within {timeout_sec}s")

    async def list_active_pods(self) -> list[GpuPod]:
        data = await self._gql(_LIST_PODS_QUERY)
        myself = data.get("myself")
        if not isinstance(myself, dict):
            return []
        result: list[GpuPod] = []
        for raw in myself.get("pods") or []:
            if isinstance(raw, dict):
                pod = self._parse_pod(raw)
                if pod.status != PodStatus.TERMINATED:
                    result.append(pod)
        return result

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
