import useSWR from "swr";
import { fetchWorkflows, fetchWorkflow, fetchGpuPods, Workflow, WorkflowDetail, GpuPod } from "./api";

export function useWorkflows(status?: string) {
  return useSWR<Workflow[]>(
    ["workflows", status],
    () => fetchWorkflows(status),
    { refreshInterval: 5000 }
  );
}

export function useWorkflow(id: string) {
  return useSWR<WorkflowDetail>(
    ["workflow", id],
    () => fetchWorkflow(id),
    { refreshInterval: 5000 }
  );
}

export function useGpuPods() {
  return useSWR<GpuPod[]>(
    "gpu-pods",
    fetchGpuPods,
    { refreshInterval: 10000 }
  );
}
