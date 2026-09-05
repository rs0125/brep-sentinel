import type {
  AdjudicateResponse,
  BatchEvaluation,
  BatchHistoryEntry,
  BatchRunResponse,
  OverviewResponse,
  PipelineStage,
  RealHistoryEntry,
  RealRunResponse,
  SingleHistoryEntry,
} from "./types";

// Set VITE_API_URL in frontend/.env if the API isn't on localhost:8000.
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---- single-file adjudication -------------------------------------------
export function adjudicateFile(file: File): Promise<AdjudicateResponse> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/adjudicate", { method: "POST", body: form });
}

export function getSingleHistory(): Promise<SingleHistoryEntry[]> {
  return request("/api/adjudicate/history");
}

export function getSingleResult(runId: string): Promise<AdjudicateResponse> {
  return request(`/api/adjudicate/${runId}`);
}

// ---- batch pipeline -------------------------------------------------------
export function runBatch(label?: string): Promise<BatchRunResponse> {
  return request("/api/batch/run", {
    method: "POST",
    body: JSON.stringify({ label: label ?? null }),
  });
}

export function getBatchHistory(): Promise<BatchHistoryEntry[]> {
  return request("/api/batch/history");
}

export function getBatchEvaluation(
  runId: string
): Promise<{ run_id: string; meta: BatchHistoryEntry; evaluation: BatchEvaluation }> {
  return request(`/api/batch/${runId}`);
}

export function getBatchReport(runId: string): Promise<{ run_id: string; markdown: string }> {
  return request(`/api/batch/${runId}/report`);
}

// ---- real-corpus demo ------------------------------------------------------
export function ingestRealCorpus(): Promise<{ run_id: string; manifest: Record<string, unknown> }> {
  return request("/api/real/ingest", { method: "POST" });
}

export function runRealDemo(label?: string): Promise<RealRunResponse> {
  return request("/api/real/run", {
    method: "POST",
    body: JSON.stringify({ label: label ?? null }),
  });
}

export function getRealHistory(): Promise<RealHistoryEntry[]> {
  return request("/api/real/history");
}

export function getRealReport(runId: string): Promise<{ run_id: string; markdown: string }> {
  return request(`/api/real/${runId}/report`);
}

// ---- meta -------------------------------------------------------------------
export function getPipelineStages(): Promise<PipelineStage[]> {
  return request("/api/pipeline/stages");
}

export function getOverview(): Promise<OverviewResponse> {
  return request("/api/overview");
}
