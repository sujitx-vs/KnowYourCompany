"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ACTIVE, API, ProgressEvent, ResearchRun, Usage, request, sessionToken } from "@/lib/api";

export function useResearchRun() {
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [history, setHistory] = useState<ResearchRun[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState("Connecting to your workspace…");
  const currentId = useRef<string | null>(null);
  const mutationLock = useRef(false);
  const interaction = useRef(0);
  const requestKey = useRef<{ payload: string; key: string } | null>(null);

  const refreshHistory = useCallback(async () => {
    const [saved, allowance] = await Promise.all([request<ResearchRun[]>("/runs"), request<Usage>("/usage")]);
    setHistory(saved); setUsage(allowance);
  }, []);

  const accept = useCallback((next: ResearchRun) => {
    currentId.current = next.id;
    localStorage.setItem("kyc.run.v2", next.id);
    setRun(next);
  }, []);

  useEffect(() => {
    let mounted = true;
    const revision = interaction.current;
    async function restore() {
      try {
        const saved = await request<ResearchRun[]>("/runs");
        if (!mounted || revision !== interaction.current) return;
        setHistory(saved);
        const id = localStorage.getItem("kyc.run.v2");
        const match = saved.find(r => r.id === id);
        if (match) accept(match);
        else if (id) localStorage.removeItem("kyc.run.v2");
        const allowance = await request<Usage>("/usage");
        if (!mounted) return;
        setUsage(allowance);
        setConnection("Workspace connected");
      } catch {
        if (mounted) setConnection("Workspace offline. Your saved session will reconnect when research starts.");
      }
    }
    void restore();
    return () => { mounted = false; };
  }, [accept]);

  const active = !!run && ACTIVE.has(run.status);
  const id = run?.id;
  useEffect(() => {
    if (!id || !active) return;
    const controller = new AbortController();
    let refreshing = false;
    async function refresh() {
      if (refreshing) return;
      refreshing = true;
      try {
        const latest = await request<ResearchRun>(`/runs/${id}`, { signal: controller.signal });
        if (currentId.current !== id || controller.signal.aborted) return;
        setRun(previous => previous?.id === latest.id && previous.event_seq > latest.event_seq ? previous : latest);
        setConnection("Live research connected");
        if (!ACTIVE.has(latest.status)) void refreshHistory().catch(() => {});
      } catch {
        if (!controller.signal.aborted) setConnection("Reconnecting. Your research continues in the background.");
      } finally { refreshing = false; }
    }
    async function stream() {
      try {
        const response = await fetch(`${API}/runs/${id}/events`, { headers: { Authorization: `Bearer ${sessionToken()}` }, signal: controller.signal });
        if (!response.ok || !response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n"); buffer = frames.pop() || "";
          for (const frame of frames) {
            const data = frame.split("\n").find(line => line.startsWith("data: "))?.slice(6);
            if (!data || currentId.current !== id) continue;
            if (frame.includes("event: snapshot")) { void refresh(); continue; }
            const event = JSON.parse(data) as ProgressEvent;
            setRun(previous => !previous || previous.id !== id || event.id <= previous.event_seq ? previous : {
              ...previous, event_seq: event.id, stage: event.stage,
              message: event.message || previous.message, events: [...previous.events, event].slice(-15),
            });
          }
        }
      } catch { /* Status polling is the reconnect fallback. */ }
    }
    void refresh(); void stream();
    const timer = setInterval(() => void refresh(), 2500);
    return () => { controller.abort(); clearInterval(timer); };
  }, [id, active, refreshHistory]);

  async function mutate(path: string, body: unknown = {}, headers = {}) {
    if (mutationLock.current) return;
    interaction.current += 1;
    mutationLock.current = true; setPending(true); setError("");
    try {
      const next = await request<ResearchRun>(path, { method: "POST", body: JSON.stringify(body), headers });
      accept(next);
      void refreshHistory().catch(() => {});
    } catch (err) { setError(err instanceof Error ? err.message : "Something went wrong. Please try again."); }
    finally { mutationLock.current = false; setPending(false); }
  }

  async function start(company_name: string, company_hint: string, refresh: boolean) {
    const body = { company_name, company_hint, refresh };
    const payload = JSON.stringify(body);
    if (requestKey.current?.payload !== payload) requestKey.current = { payload, key: crypto.randomUUID() };
    await mutate("/runs", body, { "Idempotency-Key": requestKey.current.key });
  }
  function newResearch() {
    if (mutationLock.current) return;
    interaction.current += 1;
    currentId.current = null; requestKey.current = null; setRun(null); setError("");
    localStorage.removeItem("kyc.run.v2");
  }
  async function openSaved(saved: ResearchRun) {
    interaction.current += 1;
    currentId.current = saved.id;
    try { const latest = await request<ResearchRun>(`/runs/${saved.id}`); if (currentId.current === saved.id) accept(latest); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to open this brief."); }
  }
  return { run, history, usage, pending, error, connection, active, start, newResearch, openSaved,
    chooseDomain: (selected_domain: string) => mutate(`/runs/${id}/domain`, { selected_domain }),
    confirm: () => mutate(`/runs/${id}/confirm`), cancel: () => mutate(`/runs/${id}/cancel`),
    retry: () => mutate(`/runs/${id}/retry`), feedback: (rating: number, comment: string) => mutate(`/runs/${id}/feedback`, { rating, comment }) };
}
