// All paths are relative — the Next.js rewrite proxy forwards /api/* to the backend.
// See next.config.ts for the proxy config and .env.local.example for NEXT_PUBLIC_API_URL.

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export interface Workflow {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  title?: string;
  error?: string;
}

export interface GpuPod {
  id: string;
  status: string;
  cost_per_hr: number;
  started_at: string;
  stopped_at?: string;
}

export function fetchWorkflows(status?: string): Promise<Workflow[]> {
  const params = status ? `?status=${status}` : "";
  return apiFetch<Workflow[]>(`/api/workflows${params}`);
}

export function fetchWorkflow(id: string): Promise<Workflow> {
  return apiFetch<Workflow>(`/api/workflows/${id}`);
}

// NOTE: /api/gpu-pods is not yet implemented in the backend.
// This will be wired up when the backend endpoint is added (see bead for GPU pod monitoring).
export function fetchGpuPods(): Promise<GpuPod[]> {
  return apiFetch<GpuPod[]>("/api/gpu-pods");
}
