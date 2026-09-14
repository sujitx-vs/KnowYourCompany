export type RunStatus = "queued" | "researching_company" | "needs_company_confirmation" | "awaiting_domain_selection" | "researching_domain" | "preparing_export" | "completed" | "insufficient_evidence" | "failed" | "cancelled" | "export_failed";
export type Claim = { text: string; kind: "fact" | "recommendation" | "limitation"; source_ids: string[] };
export type Brief = { confidence: string; summary: string; sections: { title: string; claims: Claim[] }[]; domains: { name: string; reason: string; source_ids: string[] }[] };
export type Source = { id: string; title: string; url: string; source: string; retrieved_at: string; official: boolean };
export type ProgressEvent = { id: number; timestamp: number; event_type: string; stage: string; message?: string; completed?: number; total?: number };
export type ResearchRun = {
  timing?: { total_seconds: number | null; company_seconds: number | null; domain_seconds: number | null; export_seconds: number | null; queue_wait_seconds: number | null; automatic_retries: number; manual_retries: number; completed_through_retry: boolean };
  eta?: { remaining_minutes: [number, number]; confidence: string; label: string };
  retry_allowed?: boolean; retries_remaining?: number; retry_scope?: "phase" | "legacy_shared"; failure_category?: string | null;
  id: string; company_name: string; status: RunStatus; phase: string; stage: string; message: string;
  created_at: number; updated_at: number; phase_started_at: number | null; completed_nodes: string[]; event_seq: number; export_status: string;
  identity: { name: string; website: string; location: string; industry: string; confidence: string; reason: string } | null;
  company_brief: Brief | null; domain_brief: Brief | null; selected_domain: string | null;
  sources: Source[]; researched_at: string | null; cached_at: string | null;
  events: ProgressEvent[]; cancel_requested: boolean; feedback: { rating: number; comment: string } | null;
};
export type Usage = { daily_limit: number; used_today: number; completed: number; cache_hits: number; input_tokens: number; output_tokens: number; median_compute_seconds: number | null; estimated_llm_cost_usd: number | null };
export const ACTIVE = new Set<RunStatus>(["queued", "researching_company", "researching_domain", "preparing_export"]);
export const API = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function sessionToken() {
  let token = localStorage.getItem("kyc.session.v2");
  if (!token) {
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    token = btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
    localStorage.setItem("kyc.session.v2", token);
  }
  return token;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers: { "Content-Type": "application/json", Authorization: `Bearer ${sessionToken()}`, ...options.headers } });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error("The research service could not be reached. Check your connection and try again; an accepted run will stay saved.");
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`;
    try { const body = await response.json(); if (typeof body.detail === "string") message = body.detail; } catch { /* Keep the safe fallback. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function reportBlob(id: string, action: "view" | "download") {
  const response = await fetch(`${API}/reports/${id}/${action}`, { headers: { Authorization: `Bearer ${sessionToken()}` } });
  if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) throw new Error("The PDF could not be opened. Please try again.");
  return response.blob();
}
