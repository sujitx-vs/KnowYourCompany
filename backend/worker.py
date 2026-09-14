"""Lease-based worker; usable in the API process or as python -m backend.worker."""
from contextlib import suppress
import hashlib
import json
import logging
import os
from threading import Event, Thread
import time

from agent.graph import build_graph, durable_node
from agent.nodes.company import verify_company
from agent.services.runtime import RunContext, RunCancelled, context, remaining, emit
from backend.store import LeaseLost
from backend.retries import retries_used
from agent.services.gemini import ResponseFailure, failure_category

log = logging.getLogger(__name__)
CACHE_FIELDS = ("search_results", "company_brief", "analysis", "report", "available_domains", "company_evidence_confidence", "researched_at")


class Worker:
    def __init__(self, store):
        self.store = store
        self.stop = Event()
        self.threads = []

    def start(self):
        for index in range(max(1, min(4, int(os.getenv("WORKER_CONCURRENCY", "2"))))):
            thread = Thread(target=self.loop, name=f"research-worker-{index}", daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=2)

    def loop(self):
        while not self.stop.is_set():
            try:
                if not self.tick():
                    self.stop.wait(0.5)
            except Exception:
                log.exception("Worker polling failed")
                self.stop.wait(2)

    def tick(self):
        run = self.store.claim()
        if not run:
            return False
        self.execute(run)
        return True

    def execute(self, run):
        run_id, lease = run["id"], run["lease"]
        heartbeat_stop = Event()
        lease_lost = Event()
        cache_key = None

        def renew():
            while not heartbeat_stop.wait(10):
                try:
                    self.store.mutate(run_id, lambda r: r.update(lease_until=time.time() + 60), lease=lease)
                except Exception:
                    lease_lost.set()
                    return

        heartbeat = Thread(target=renew, daemon=True)
        heartbeat.start()

        def cancelled():
            current = self.store.get(run_id)
            return self.stop.is_set() or lease_lost.is_set() or not current or current["cancel_requested"] or current["lease"] != lease

        def checkpoint(state):
            remaining()
            self.store.mutate(run_id, lambda r: r.update(state=state), lease=lease)

        def finish(status, message, **fields):
            def action(current):
                # Cancellation wins over a late result.
                current.update(status="cancelled" if current["cancel_requested"] else status,
                               lease="", lease_until=0, **fields)
                current["metrics"].append({"metric": "phase_seconds", "phase": run["phase"], "value": round(time.monotonic() - start, 3)})
                if fields.get("phase") and fields["phase"] != run["phase"]:
                    current.pop("phase_started_at", None)
                self.store.event(current, "state", message="Research cancelled." if current["cancel_requested"] else message)
            self.store.mutate(run_id, action, lease=lease)

        def response_budget(schema_name, recovery):
            # Reserve before calling the provider; persists across worker restarts.
            key = f"{run['phase']}:{retries_used(run)}:{schema_name}"
            def reserve(current):
                budget = current.setdefault("response_attempts", {}).setdefault(key, {"calls": 0, "repairs": 0})
                if budget["calls"] >= 2 or (recovery and budget["repairs"] >= 1):
                    raise ResponseFailure("automatic_attempts_exhausted")
                budget["calls"] += 1
                budget["repairs"] += int(recovery)
            self.store.mutate(run_id, reserve, lease=lease)

        start = time.monotonic()
        token = context.set(RunContext(
            emit=lambda **event: self.store.append(run_id, lease, **event), cancelled=cancelled,
            deadline=start + max(0, float(os.getenv("RUN_PHASE_TIMEOUT_SECONDS", "240")) - (time.time() - run.get("phase_started_at", time.time()))), checkpoint=checkpoint,
            cache=self.store, cache_lease=lease, refresh=run["refresh"],
            run_id=run_id, phase=run["phase"], response_budget=response_budget))
        try:
            emit("metric", metric="queue_seconds", value=run.get("queue_wait_seconds", 0))
            state = run["state"]
            if run["phase"] == "company":
                state = {**state, **durable_node("verify_company", verify_company)(state)}
                if state["identity"]["confidence"] != "HIGH" and not state.get("identity_confirmed"):
                    status = "needs_company_confirmation" if state["identity"].get("website") else "insufficient_evidence"
                    finish(status, "Please confirm that we found the right company." if status == "needs_company_confirmation" else "We could not verify this company. Try its official website or location.", state=state)
                    return
                canonical = [state["identity"].get("website"), state["identity"]["name"].casefold(), "brief-v2",
                             os.getenv("GEMINI_MODELS", "gemini-3.5-flash,gemini-3.5-flash-lite"), os.getenv("EVIDENCE_BYTE_BUDGET", "24000"), os.getenv("TAVILY_SEARCH_DEPTH", "basic")]
                cache_key = hashlib.sha256(json.dumps(canonical).encode()).hexdigest()
                cache_enabled = os.getenv("RESEARCH_CACHE_ENABLED", "true").lower() == "true" and not run["refresh"]
                if cache_enabled:
                    outcome, cached = self.store.cache_claim(cache_key, lease, ttl=300)
                    if outcome == "wait":
                        finish("queued", "A current company brief is being prepared. Waiting to reuse its verified research.", state=state, not_before=time.time() + 3, attempts=0)
                        return
                    if outcome == "hit":
                        state.update(cached)
                        state["cached_at"] = cached["researched_at"]
                        checkpoint(state)
                        emit("metric", metric="cache_hit", value=1)
                    else:
                        state = build_graph("company").invoke(state)
                        if state["company_evidence_confidence"] != "INSUFFICIENT":
                            self.store.cache_write(cache_key, lease, {k: state[k] for k in CACHE_FIELDS}, min(int(os.getenv("COMPANY_CACHE_TTL_SECONDS", "1800")), int(os.getenv("NEWS_SEARCH_TTL_SECONDS", "1800"))))
                else:
                    state = build_graph("company").invoke(state)
                if state["company_evidence_confidence"] == "INSUFFICIENT":
                    finish("insufficient_evidence", state["company_brief"]["summary"], state=state)
                else:
                    emit("metric", metric="first_brief_seconds", value=time.monotonic() - start)
                    finish("awaiting_domain_selection", "Your company brief is ready. Choose where you want to focus.", state=state)
            elif run["phase"] == "domain":
                state = build_graph("domain").invoke(state)
                if state["domain_evidence_confidence"] == "INSUFFICIENT":
                    finish("insufficient_evidence", state["domain_brief"]["summary"], state=state)
                else:
                    finish("queued", "Your preparation brief is ready. Preparing the downloadable report.", state=state, phase="export", attempts=0, export_status="queued")
            else:
                from agent.nodes.report import generate_pdf
                emit(stage="export", message="Preparing your downloadable report.")
                update = generate_pdf({**state, "export_id": run_id})
                remaining()
                finish("completed", "Your dossier is ready to read and download.", state={**state, **update}, export_status="ready")
        except (RunCancelled, LeaseLost):
            with suppress(LeaseLost):
                if not self.stop.is_set():
                    finish("cancelled", "Research cancelled. Your completed sections are saved.")
        except Exception as error:
            category = failure_category(error)
            log.warning("Research failed run=%s phase=%s category=%s", run_id, run["phase"], category)
            with suppress(LeaseLost):
                finish("export_failed" if run["phase"] == "export" else "failed",
                       "The PDF could not be prepared. Your web brief is saved." if run["phase"] == "export" else "This research step could not finish. Your completed steps are saved.",
                       failure_category=category,
                       **({"export_status": "failed"} if run["phase"] == "export" else {}))
        finally:
            # Metrics survive a completed lease through a separate fenced event only while owned.
            heartbeat_stop.set()
            heartbeat.join(timeout=1)
            if cache_key:
                self.store.cache_release(cache_key, lease)
            context.reset(token)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from backend.store import Store
    load_dotenv()
    from backend.config import validate_configuration
    validate_configuration()
    logging.basicConfig(level=logging.INFO)
    worker = Worker(Store())
    try:
        worker.loop()
    except KeyboardInterrupt:
        worker.close()
