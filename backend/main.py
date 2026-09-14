"""Research API with scoped anonymous ownership and durable background execution."""
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path
from typing import Annotated
import asyncio
import json
import logging
import os
import re
import secrets
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from backend.store import Store, Conflict, QuotaExceeded, ACTIVE
from backend.worker import Worker
from backend.retries import retry_info, retries_used
from backend.config import validate_configuration

log = logging.getLogger(__name__)

class ResearchRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=180)
    company_hint: str = Field(default="", max_length=300)
    refresh: bool = False

class DomainRequest(BaseModel):
    selected_domain: str = Field(min_length=1, max_length=100)

class LegacyDomainRequest(DomainRequest):
    thread_id: str = Field(min_length=1, max_length=100)

class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)

def owner(authorization: Annotated[str | None, Header()] = None):
    value = (authorization or "").removeprefix("Bearer ")
    if not authorization or not authorization.startswith("Bearer ") or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", value):
        raise HTTPException(401, "Your browser session is missing. Reload to create a new session.")
    return sha256(value.encode()).hexdigest()

def public_run(run):
    state = run["state"]
    sources = [{k: r.get(k) for k in ("id", "title", "url", "source", "retrieved_at", "published_at", "official")}
               for r in state.get("search_results", []) + state.get("domain_search_results", [])]
    return {k: run.get(k) for k in ("id", "company_name", "status", "phase", "stage", "message", "created_at", "updated_at", "phase_started_at", "event_seq", "export_status", "feedback")} | {
        "identity": state.get("identity"), "company_brief": state.get("company_brief"),
        "domain_brief": state.get("domain_brief"), "selected_domain": state.get("selected_domain"),
        "sources": sources, "researched_at": state.get("researched_at"), "cached_at": state.get("cached_at"),
        "events": run["events"][-15:], "cancel_requested": run["cancel_requested"],
        "completed_nodes": state.get("completed_nodes", []),
        "timing": timing_summary(run), "eta": estimate_for_run(run),
        **retry_info(run),
    }

def timing_summary(run):
    phases = {"company": None, "domain": None, "export": None}
    for metric in run.get("metrics", []):
        if metric.get("metric") == "phase_seconds" and metric.get("phase") in phases:
            phases[metric["phase"]] = metric.get("value")
    return {"total_seconds": sum(v for v in phases.values() if v is not None) or None, "company_seconds": phases["company"], "domain_seconds": phases["domain"], "export_seconds": phases["export"], "queue_wait_seconds": run.get("queue_wait_seconds"), "automatic_retries": sum(run.get("automatic_retries", {}).values()), "manual_retries": run.get("retries", 0), "completed_through_retry": bool(run.get("retries", 0) or sum(run.get("automatic_retries", {}).values()))}

def estimate_for_run(run, history=None):
    phase = run.get("phase", "company")
    default = {"company": 180, "domain": 180, "export": 45}.get(phase, 180)
    samples = [timing_summary(item).get(f"{phase}_seconds") for item in (history or []) if item.get("status") == "completed"]
    samples = sorted(value for value in samples if value)
    if samples:
        default = samples[len(samples) // 2]
    return {"remaining_minutes": [max(1, round(default / 60 - 0.5)), max(2, round(default / 60 + 0.5))], "confidence": "medium" if samples else "low", "label": "Based on recent completed runs" if samples else "Approximation based on configured phase limits"}

def summary(runs):
    durations = sorted(sum(m.get("value", 0) for m in r["metrics"] if m.get("metric") == "phase_seconds") for r in runs if r["status"] == "completed")
    tokens_in = sum(m.get("input_tokens", 0) for r in runs for m in r["metrics"])
    tokens_out = sum(m.get("output_tokens", 0) for r in runs for m in r["metrics"])
    # Missing prices remain unknown, rather than reporting a misleading zero.
    prices = json.loads(os.getenv("MODEL_PRICES_JSON", "{}"))
    search_prices = json.loads(os.getenv("SEARCH_PRICES_JSON", "{}"))
    model_cost, search_cost, model_known, search_known = 0.0, 0.0, True, True
    for run in runs:
        for metric in run["metrics"]:
            if metric.get("metric") == "llm_usage":
                rate = prices.get(metric.get("model"))
                if rate and "input" in rate and "output" in rate:
                    model_cost += (metric.get("input_tokens", 0) * rate["input"] + metric.get("output_tokens", 0) * rate["output"]) / 1e6
                else:
                    model_known = False
            elif metric.get("metric") == "provider_seconds":
                rate = search_prices.get(metric.get("provider"))
                if rate is not None:
                    search_cost += rate
                else:
                    search_known = False
    completed = sum(r["status"] == "completed" for r in runs)
    total_cost = model_cost + search_cost if model_known and search_known else None
    return {"runs": len(runs), "completed": sum(r["status"] == "completed" for r in runs),
            "failed": sum(r["status"] in {"failed", "export_failed"} for r in runs),
            "activated": sum(bool(r["state"].get("selected_domain")) for r in runs),
            "cancelled": sum(r["status"] == "cancelled" for r in runs),
            "cache_hits": sum(m.get("metric") == "cache_hit" for r in runs for m in r["metrics"]),
            "input_tokens": tokens_in, "output_tokens": tokens_out,
            "median_compute_seconds": durations[len(durations)//2] if durations else None,
            "p95_compute_seconds": durations[min(len(durations)-1, int(len(durations)*0.95))] if durations else None,
            "estimated_llm_cost_usd": round(model_cost, 4) if model_known else None,
            "estimated_provider_cost_usd": round(total_cost, 4) if total_cost is not None else None,
            "estimated_cost_per_completed_brief_usd": round(total_cost / completed, 4) if total_cost is not None and completed else None,
            "feedback_count": sum(bool(r["feedback"]) for r in runs),
            "returning_sessions": sum(sum(r["owner"] == owner for r in runs) > 1 for owner in {r["owner"] for r in runs}),
            "cost_note": "Estimates use configured model token prices and search request prices; retries, taxes and hosting may add charges."}

def create_app(store=None, start_worker=True):
    load_dotenv()
    @asynccontextmanager
    async def lifespan(app):
        validate_configuration()
        app.state.store = store or Store()
        worker = Worker(app.state.store)
        app.state.worker = worker
        if start_worker and os.getenv("EMBEDDED_WORKER", "true").lower() == "true":
            worker.start()
        yield
        worker.close()

    app = FastAPI(title="KnowYourCompany", version="2.0.0", lifespan=lifespan)
    origins = [s.strip().rstrip("/") for s in os.getenv("FRONTEND_URL", "http://localhost:3000,http://127.0.0.1:3000").split(",") if s.strip()]
    if os.getenv("APP_ENV") != "production":
        origins = list(set(origins + ["http://localhost:3000", "http://127.0.0.1:3000"]))
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID", "X-Admin-Key"])

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Conflict)
    async def conflict_handler(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(QuotaExceeded)
    async def quota_handler(request, error):
        return JSONResponse({"detail": str(error)}, status_code=429, headers={"Retry-After": "3600"})

    @app.exception_handler(Exception)
    async def safe_error(request, error):
        reference = secrets.token_hex(6)
        log.error("Request failed reference=%s", reference, exc_info=error)
        return JSONResponse({"detail": f"Something went wrong. Reference: {reference}"}, status_code=500)

    def get_store(request: Request):
        return request.app.state.store

    def owned(db, run_id, session):
        run = db.get(run_id, session)
        if not run:
            raise HTTPException(404, "This saved research is unavailable in your browser session.")
        return run

    @app.get("/")
    def health():
        return {"status": "ok", "version": "2.0.0"}

    @app.get("/ready")
    def readiness(db=Depends(get_store)):
        with db.tx() as connection:
            connection.execute("SELECT 1")
        return {"status": "ready", "persistence": "postgres" if db.postgres else "sqlite"}

    @app.post("/runs", status_code=202)
    @app.post("/research", status_code=202, deprecated=True)
    def start(request: Request, body: ResearchRequest, session=Depends(owner), db=Depends(get_store),
              idempotency_key: Annotated[str | None, Header()] = None):
        company = body.company_name.strip()
        if not company:
            raise HTTPException(422, "Enter a company name.")
        key = idempotency_key or secrets.token_hex(16)
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", key):
            raise HTTPException(422, "Invalid request key.")
        # Use the server's resolved client address. Trust proxy headers only through a configured ASGI proxy.
        ip_hash = sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
        return public_run(db.create(session, ip_hash, company, body.company_hint.strip(), key, body.refresh))

    @app.get("/runs")
    def history(session=Depends(owner), db=Depends(get_store)):
        runs = db.list(session)
        return [{**public_run(r), "eta": estimate_for_run(r, runs)} for r in runs]

    @app.get("/usage")
    def usage(session=Depends(owner), db=Depends(get_store)):
        runs = db.list(session)
        return {**summary(runs), "daily_limit": int(os.getenv("DAILY_RUN_LIMIT", "10")),
                "used_today": sum(r["created_at"] > time.time() - 86400 for r in runs)}

    @app.get("/admin/metrics")
    def metrics(x_admin_key: Annotated[str | None, Header()] = None, db=Depends(get_store)):
        expected = os.getenv("ADMIN_API_KEY", "")
        if len(expected) < 32 or not secrets.compare_digest(x_admin_key or "", expected):
            raise HTTPException(401, "Operator access is required.")
        return {"period_days": 30, **summary(db.recent())}

    @app.get("/runs/{run_id}")
    def status(run_id: str, session=Depends(owner), db=Depends(get_store)):
        return public_run(owned(db, run_id, session))

    @app.get("/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0, session=Depends(owner), db=Depends(get_store),
                     last_event_id: Annotated[str | None, Header()] = None):
        await asyncio.to_thread(owned, db, run_id, session)
        try:
            cursor = max(after, int(last_event_id or 0))
        except ValueError:
            raise HTTPException(422, "Invalid event cursor.")
        async def stream():
            nonlocal cursor
            last_heartbeat = 0
            while not await request.is_disconnected():
                run = await asyncio.to_thread(db.get, run_id, session)
                if not run:
                    break
                for event in run["events"]:
                    if event["id"] > cursor:
                        cursor = event["id"]
                        yield f"id: {cursor}\nevent: progress\ndata: {json.dumps(event)}\n\n"
                if time.monotonic() - last_heartbeat > 10:
                    yield ": heartbeat\n\n"
                    last_heartbeat = time.monotonic()
                if run["status"] not in ACTIVE:
                    yield f"event: snapshot\ndata: {json.dumps(public_run(run))}\n\n"
                    break
                await asyncio.sleep(0.75)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    def transition(db, run_id, session, action):
        owned(db, run_id, session)
        return public_run(db.mutate(run_id, action, owner=session))

    @app.post("/runs/{run_id}/confirm")
    def confirm(run_id: str, session=Depends(owner), db=Depends(get_store)):
        def action(run):
            if run["status"] != "needs_company_confirmation":
                raise Conflict("This research is not waiting for company confirmation.")
            run["state"]["identity_confirmed"] = True
            run.update(status="queued", attempts=0, phase="company")
            run.pop("phase_started_at", None)
            db.event(run, "state", message="Company confirmed. Continuing research.")
        return transition(db, run_id, session, action)

    def choose(run_id, body, session, db):
        def action(run):
            if run["status"] != "awaiting_domain_selection":
                raise Conflict("This research is not waiting for a domain.")
            if body.selected_domain not in run["state"].get("available_domains", []):
                raise HTTPException(422, "Choose one of the offered domains.")
            run["state"]["selected_domain"] = body.selected_domain
            run.update(status="queued", phase="domain", attempts=0, not_before=0)
            run.pop("phase_started_at", None)
            db.event(run, "state", message="Your preparation research is queued.")
        return transition(db, run_id, session, action)

    @app.post("/runs/{run_id}/domain", status_code=202)
    def domain(run_id: str, body: DomainRequest, session=Depends(owner), db=Depends(get_store)):
        return choose(run_id, body, session, db)

    @app.post("/select-domain", status_code=202, deprecated=True)
    def legacy_domain(body: LegacyDomainRequest, session=Depends(owner), db=Depends(get_store)):
        return choose(body.thread_id, body, session, db)

    @app.post("/runs/{run_id}/cancel")
    def cancel(run_id: str, session=Depends(owner), db=Depends(get_store)):
        def action(run):
            if run["status"] in ACTIVE or run["status"] in {"awaiting_domain_selection", "needs_company_confirmation"}:
                run["cancel_requested"] = True
                run.update(status="cancelled")
                db.event(run, "state", message="Research cancelled. Completed sections are saved.")
        return transition(db, run_id, session, action)

    @app.post("/runs/{run_id}/retry", status_code=202)
    def retry(run_id: str, session=Depends(owner), db=Depends(get_store)):
        def action(run):
            if run["status"] not in {"failed", "export_failed"}:
                raise Conflict("Only a failed step can be retried.")
            if run["lease_until"] > time.time():
                raise Conflict("The previous attempt is still stopping. Please try again shortly.")
            if retries_used(run) >= 3:
                raise HTTPException(429, "No manual retries remain for this retry budget. Waiting does not reset it.", headers={"X-Failure-Category": "manual_retries_exhausted"})
            if "phase_retries" in run:
                run["phase_retries"][run["phase"]] = retries_used(run) + 1
            run.pop("failure_category", None)
            run.update(status="queued", attempts=0, not_before=0, retries=run["retries"]+1)
            run.pop("phase_started_at", None)
            db.event(run, "state", message="Retrying from the last saved step.")
        return transition(db, run_id, session, action)

    @app.post("/runs/{run_id}/feedback")
    def feedback(run_id: str, body: FeedbackRequest, session=Depends(owner), db=Depends(get_store)):
        return transition(db, run_id, session, lambda r: r.update(feedback=body.model_dump()))

    @app.get("/reports/{run_id}/{action}")
    def report(run_id: str, action: str, session=Depends(owner), db=Depends(get_store)):
        if action not in {"view", "download"}:
            raise HTTPException(404)
        run = owned(db, run_id, session)
        if run["export_status"] != "ready":
            raise HTTPException(409, "The PDF is not ready yet.")
        path = run["state"].get("pdf_path", "")
        if path.startswith("reports/"):
            from backend.supabase_client import get_report_signed_url
            return RedirectResponse(get_report_signed_url(path, download=action == "download"), status_code=303)
        root = Path(os.getenv("REPORT_DIR", "outputs")).resolve()
        target = Path(path).resolve()
        if not target.is_relative_to(root) or target.suffix.lower() != ".pdf" or not target.is_file():
            raise HTTPException(404, "The report file is unavailable.")
        return FileResponse(target, media_type="application/pdf",
                            filename=f"{run['id']}-company-dossier.pdf",
                            content_disposition_type="attachment" if action == "download" else "inline")

    @app.get("/view-pdf", deprecated=True)
    @app.get("/download-pdf", deprecated=True)
    def retired_report_route():
        raise HTTPException(410, "Use an authenticated report ID. File paths are no longer accepted.")

    return app

app = create_app()
