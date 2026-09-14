"""Additive phase retry policy; old shared budgets stay shared and unchanged."""
import time

PHASES = ("company", "domain", "export")


def retries_used(run):
    counters = run.get("phase_retries")
    return counters.get(run["phase"], 0) if isinstance(counters, dict) else run.get("retries", 0)


def retry_info(run):
    left = max(0, 3 - retries_used(run))
    failed = run["status"] in {"failed", "export_failed"}
    return {"retry_allowed": failed and left > 0 and run.get("lease_until", 0) <= time.time(),
            "retries_remaining": left, "retry_scope": "phase" if "phase_retries" in run else "legacy_shared",
            "failure_category": run.get("failure_category")}
