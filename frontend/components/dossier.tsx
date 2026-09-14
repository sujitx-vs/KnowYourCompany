"use client";

import { FormEvent, useEffect, useState } from "react";
import { ACTIVE, Brief, ResearchRun, Source, reportBlob } from "@/lib/api";

export function CompanySearchForm({ onStart, disabled }: { onStart: (name: string, hint: string, refresh: boolean) => void; disabled: boolean }) {
  const [name, setName] = useState("");
  const [hint, setHint] = useState("");
  const [refresh, setRefresh] = useState(false);
  function submit(event: FormEvent) { event.preventDefault(); if (name.trim()) onStart(name.trim(), hint.trim(), refresh); }
  return <form className="search-form" onSubmit={submit}>
    <label htmlFor="company-name">Which company is on your mind?</label>
    <div className="search-row"><input id="company-name" name="company" autoComplete="organization" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Tata Consultancy Services" maxLength={180} required disabled={disabled} /><button className="primary" disabled={disabled || !name.trim()}>{disabled ? "Starting…" : "Build my brief"}<span aria-hidden="true">↗</span></button></div>
    <details className="search-options"><summary>Make the match more precise <span>optional</span></summary><label htmlFor="company-hint">Official website or location</label><input id="company-hint" value={hint} onChange={e => setHint(e.target.value)} maxLength={300} placeholder="Company website, city or country" disabled={disabled} /><label className="check"><input type="checkbox" checked={refresh} onChange={e => setRefresh(e.target.checked)} disabled={disabled} />Research fresh sources instead of reusing a recent brief</label></details>
    <p className="form-note">Start with the company. Choose your career focus next.</p>
  </form>;
}

const STAGE_NAMES: Record<string, string> = { queued: "Getting ready", identity: "Company identity", company_search: "Public source research", filtering: "Evidence check", company_brief: "Company brief", domain_search: "Career research", domain_brief: "Preparation brief", export: "PDF export" };
export function ResearchProgress({ run, connection, onCancel, disabled }: { run: ResearchRun; connection: string; onCancel: () => void; disabled: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  const active = ACTIVE.has(run.status);
  useEffect(() => { if (!active) return; const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, [active]);
  const seconds = Math.max(0, Math.floor(now / 1000 - (run.phase_started_at ?? now / 1000)));
  const recent = run.events.filter(e => e.message).slice(-5);
  const last = recent.at(-1);
  const slow = active && last && now / 1000 - last.timestamp > 30;
  return <section className="progress-panel" aria-label="Research activity">
    <div className="eyebrow"><span className={active ? "live-dot" : "status-dot"} />{active ? "RESEARCH IN PROGRESS" : "RESEARCH ACTIVITY"}</div>
    <div className="progress-title"><h2>{STAGE_NAMES[run.stage] || "Your dossier"}</h2>{active && <span className="elapsed">{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}</span>}</div>
    <p className="live-message" role="status" aria-live="polite">{run.message}</p>
    <div className="progress-facts"><span>{run.sources.length} checked sources</span><span>{run.completed_nodes.length} steps saved</span></div>
    {active && <p className="next-step">Next: {run.phase === "company" ? "read the company brief and choose your career focus." : run.phase === "domain" ? "review your preparation priorities." : "download your complete dossier."}</p>}
    {slow && <p className="notice">This step is taking longer than usual. Your completed work is saved.</p>}
    <details className="activity-details"><summary>Recent research activity</summary><ol className="activity-list">{recent.map(event => <li key={event.id} className={event.event_type === "warning" ? "warning-event" : ""}><span aria-hidden="true">{event.event_type === "warning" ? "!" : "·"}</span><p>{event.message}</p></li>)}</ol></details>
    <div className="progress-footer"><span>{connection}</span>{active && <button className="text-button" onClick={onCancel} disabled={disabled}>Cancel research</button>}</div>
  </section>;
}

export function CompanyIdentity({ run, onConfirm, disabled }: { run: ResearchRun; onConfirm: () => void; disabled: boolean }) {
  const identity = run.identity;
  if (!identity) return null;
  return <section className="identity-block" aria-label="Company identity"><div><span className="eyebrow">COMPANY RECORD</span><h2>{identity.name}</h2><p>{identity.industry} <span aria-hidden="true">/</span> {identity.location}</p></div>{identity.website && <a className="external-link" href={identity.website} target="_blank" rel="noopener noreferrer">Official website ↗</a>}{run.status === "needs_company_confirmation" && <div className="confirmation"><h3>Is this the company you mean?</h3><p>{identity.reason}</p><button className="primary" onClick={onConfirm} disabled={disabled}>Yes, research this company <span aria-hidden="true">→</span></button><p className="small">If this is a different company, start a new brief with its website or location.</p></div>}</section>;
}

export function BriefContent({ brief, label, title }: { brief: Brief; label: string; title: string }) {
  return <section className="brief-section"><header className="section-header"><div><span className="eyebrow">{label}</span><h2>{title}</h2></div><span className={`confidence confidence-${brief.confidence.toLowerCase()}`}>{brief.confidence.toLowerCase()} evidence</span></header><p className="evidence-summary">{brief.summary}</p><div className="brief-content">{brief.sections.map((section, index) => <section className="brief-chapter" key={section.title}><span className="chapter-number">{String(index + 1).padStart(2, "0")}</span><div><h3>{section.title}</h3>{section.claims.map((claim, i) => <p key={i} className={`claim claim-${claim.kind}`}>{claim.kind === "recommendation" && <span className="recommendation-label">Suggested preparation</span>}{claim.text} {claim.source_ids.map(id => <a key={id} className="citation" href={`#source-${id}`} aria-label={`Read source ${id}`}>[{id}]</a>)}</p>)}</div></section>)}</div></section>;
}

export function DomainPicker({ brief, onChoose, disabled }: { brief: Brief; onChoose: (domain: string) => void; disabled: boolean }) {
  return <section className="domain-section"><span className="eyebrow">NEXT / MAKE IT RELEVANT TO YOU</span><h2>Where do you want to go?</h2><p>Choose a career area. We’ll connect the company research to your preparation.</p><div className="domain-grid">{brief.domains.map((domain, index) => <button className="domain-option" key={domain.name} onClick={() => onChoose(domain.name)} disabled={disabled}><span className="domain-number">0{index + 1}</span><span><strong>{domain.name}</strong><span className="domain-reason">{domain.reason}</span><span className="domain-evidence">Based on {domain.source_ids.join(", ")}</span></span><span aria-hidden="true">↗</span></button>)}</div></section>;
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return <section className="source-register" id="sources"><span className="eyebrow">THE EVIDENCE BEHIND THE BRIEF</span><h2>Source register <span>{sources.length}</span></h2><p>Follow the references. Check the context. Make your own judgement.</p><div>{sources.map(source => <article className="source-row" id={`source-${source.id}`} key={source.id}><span className="source-id">{source.id}</span><div><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title || new URL(source.url).hostname} <span aria-hidden="true">↗</span></a><p>{new URL(source.url).hostname} · {source.official ? "Official source" : "Public source"}{source.retrieved_at ? ` · Retrieved ${source.retrieved_at.slice(0, 10)}` : ""}</p></div></article>)}</div></section>;
}

export function ReportActions({ run, onRetry, disabled }: { run: ResearchRun; onRetry: () => void; disabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function open(action: "view" | "download") {
    setBusy(true); setError("");
    // Open synchronously to respect popup blockers, then navigate to an authenticated blob.
    const tab = action === "view" ? window.open("about:blank", "_blank") : null;
    if (tab) tab.opener = null;
    try {
      const blob = await reportBlob(run.id, action);
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = url;
      else { const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${run.company_name}-dossier.pdf`; anchor.click(); }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) { tab?.close(); setError(err instanceof Error ? err.message : "The report could not be opened."); }
    finally { setBusy(false); }
  }
  return <section className="export-panel"><div><span className="eyebrow">TAKE IT WITH YOU</span><h2>Your interview companion.</h2><p>{run.export_status === "ready" ? "Your complete brief, with its sources, ready to keep." : run.export_status === "failed" ? "Your web brief is safe. The PDF export needs another attempt." : "Your web brief is ready. The PDF is being prepared."}</p></div><div className="export-buttons">{run.export_status === "ready" ? <><button className="primary" disabled={busy} onClick={() => void open("download")}>{busy ? "Opening…" : "Download PDF ↓"}</button><button className="secondary" disabled={busy} onClick={() => void open("view")}>Preview ↗</button></> : run.export_status === "failed" ? <button className="primary" onClick={onRetry} disabled={disabled}>Retry PDF export</button> : <span className="small">Preparing export…</span>}</div>{error && <p role="alert" className="error">{error}</p>}</section>;
}

export function Feedback({ run, onSubmit, disabled }: { run: ResearchRun; onSubmit: (rating: number, comment: string) => void; disabled: boolean }) {
  const [rating, setRating] = useState(4);
  const [comment, setComment] = useState("");
  return <section className="feedback"><h3>Did this give you a clearer starting point?</h3>{run.feedback ? <p>Thanks. Your feedback is saved with this brief.</p> : <form onSubmit={e => { e.preventDefault(); onSubmit(rating, comment); }}><label htmlFor="rating">How useful was this brief?</label><select id="rating" value={rating} onChange={e => setRating(Number(e.target.value))}>{[5, 4, 3, 2, 1].map(n => <option key={n} value={n}>{n} / 5{n === 5 ? " — Very useful" : n === 1 ? " — Not useful" : ""}</option>)}</select><label htmlFor="feedback">What would make it better? <span>optional</span></label><textarea id="feedback" maxLength={1000} rows={2} value={comment} onChange={e => setComment(e.target.value)} /><button className="secondary" disabled={disabled}>Send feedback</button></form>}</section>;
}
