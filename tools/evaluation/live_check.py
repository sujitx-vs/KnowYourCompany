"""Opt-in bounded live smoke test. Saves local results; never uploads a report."""
import argparse
import json
import os
from pathlib import Path
import secrets
import time
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", default="")
    parser.add_argument("--resume-run")
    parser.add_argument("--hint", default="")
    parser.add_argument("--include-domain", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    os.environ["APP_ENV"] = "test"
    os.environ["SEARCH_CACHE_ENABLED"] = "false"
    os.environ["RESEARCH_CACHE_ENABLED"] = "false"
    from backend.store import Store
    from backend.worker import Worker
    from backend.main import public_run
    store = Store("outputs/live-verification.sqlite3")
    if args.resume_run:
        run = store.get(args.resume_run)
        if not run:
            parser.error("Unknown verification run")
        def reset(r):
            r.update(status="queued", cancel_requested=False, attempts=0, lease="", lease_until=0)
            r.pop("phase_started_at", None)
        store.mutate(run["id"], reset)
    else:
        if not args.company:
            parser.error("Provide --company or --resume-run")
        run = store.create(secrets.token_hex(32), "local-verification", args.company, args.hint, secrets.token_hex(16), True)
    worker = Worker(store)
    start = time.monotonic()
    worker.tick()
    run = store.get(run["id"])
    company_seconds = time.monotonic() - start
    print(json.dumps({"phase": "company", "status": run["status"], "seconds": round(company_seconds, 2)}), flush=True)
    domain_seconds = None
    if args.include_domain and run["status"] == "awaiting_domain_selection":
        selected = run["state"]["available_domains"][0]
        def resume(r):
            r["state"]["selected_domain"] = selected
            r.update(status="queued", phase="domain", attempts=0)
            r.pop("phase_started_at", None)
        store.mutate(run["id"], resume)
        start = time.monotonic()
        worker.tick()
        domain_seconds = time.monotonic() - start
        run = store.get(run["id"])
    # Do not leave export jobs queued in the verification database.
    store.mutate(run["id"], lambda r: r.update(status="cancelled", cancel_requested=True))
    record = {"company_seconds": company_seconds, "domain_seconds": domain_seconds, "run": public_run(run), "metrics": run["metrics"]}
    output = Path("outputs/live-verification.json")
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps({"status": run["status"], "output": str(output), "domain_seconds": domain_seconds}))


if __name__ == "__main__":
    main()
