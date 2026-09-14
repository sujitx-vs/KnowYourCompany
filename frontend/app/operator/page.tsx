"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";

type Metrics = {
  runs: number; completed: number; failed: number; activated: number; cancelled: number;
  cache_hits: number; feedback_count: number; returning_sessions: number; period_days: number;
  median_compute_seconds: number | null; p95_compute_seconds: number | null;
  estimated_provider_cost_usd: number | null; estimated_cost_per_completed_brief_usd: number | null;
  cost_note: string;
};

export default function OperatorPage() {
  const [key, setKey] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function load(event: FormEvent) {
    event.preventDefault(); setPending(true); setError("");
    try {
      const response = await fetch(`${API}/admin/metrics`, { headers: { "X-Admin-Key": key } });
      if (!response.ok) throw new Error("Operator access could not be verified.");
      setMetrics(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : "The service is unavailable."); }
    finally { setPending(false); }
  }
  const cards = metrics ? [
    ["Research requests", metrics.runs], ["Completed dossiers", metrics.completed],
    ["Career focus selected", metrics.activated], ["Failed steps", metrics.failed],
    ["Cancelled research", metrics.cancelled], ["Company cache hits", metrics.cache_hits],
    ["Feedback received", metrics.feedback_count], ["Returning browser sessions", metrics.returning_sessions],
    ["Median compute time", metrics.median_compute_seconds === null ? "Not measured" : `${metrics.median_compute_seconds.toFixed(1)}s`],
    ["95th percentile compute", metrics.p95_compute_seconds === null ? "Not measured" : `${metrics.p95_compute_seconds.toFixed(1)}s`],
    ["Estimated provider cost", metrics.estimated_provider_cost_usd === null ? "Prices not configured" : `$${metrics.estimated_provider_cost_usd.toFixed(3)}`],
    ["Cost / completed dossier", metrics.estimated_cost_per_completed_brief_usd === null ? "Not available" : `$${metrics.estimated_cost_per_completed_brief_usd.toFixed(3)}`],
  ] : [];
  return <main className="operator-page"><Link href="/">← Research desk</Link><span className="eyebrow">PRIVATE BETA / OPERATIONS</span><h1>How the desk is doing.</h1><p>Aggregate usage and reliability over the last 30 days. No private briefs are displayed here.</p><form onSubmit={load}><label htmlFor="operator-key">Operator access key</label><div><input id="operator-key" type="password" autoComplete="off" value={key} onChange={e => setKey(e.target.value)} required minLength={32} /><button className="primary" disabled={pending}>{pending ? "Loading…" : "Load metrics"}</button><button type="button" className="secondary" onClick={() => { setKey(""); setMetrics(null); }}>Clear access</button></div><p>The key stays in memory in this tab and is never saved in browser storage.</p></form>{error && <p className="error" role="alert">{error}</p>}{metrics && <><div className="metrics-grid">{cards.map(([label, value]) => <article key={label}><span>{label}</span><strong>{value}</strong></article>)}</div><p className="small">{metrics.cost_note} Compute time excludes time waiting for user selections. Returning browser sessions are not verified individual people.</p></>}</main>;
}
