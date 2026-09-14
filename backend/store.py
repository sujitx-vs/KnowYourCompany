"""Durable run queue. SQLite for development; PostgreSQL is required in production.

All mutations use short transactions; a transaction lock makes quota checks, leases,
events and state changes atomic across API and worker processes. No provider work
is performed while holding a database transaction.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
import time

ACTIVE = {"queued", "researching_company", "researching_domain", "preparing_export"}
TERMINAL = {"completed", "insufficient_evidence", "failed", "cancelled", "export_failed"}


class Conflict(Exception):
    pass


class QuotaExceeded(Exception):
    pass


class LeaseLost(Exception):
    pass


class Store:
    def __init__(self, url=None):
        self.url = url if url is not None else os.getenv("RUN_DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL", "")
        self.postgres = self.url.startswith(("postgres://", "postgresql://"))
        if os.getenv("APP_ENV") == "production" and not self.postgres:
            raise RuntimeError("Production requires a PostgreSQL RUN_DATABASE_URL")
        self.path = self.url or os.getenv("RUN_DB_PATH", "outputs/research.sqlite3")
        if self.postgres:
            import psycopg
            with psycopg.connect(self.url, connect_timeout=10) as conn:
                conn.execute("CREATE SCHEMA IF NOT EXISTS kyc_private")
                conn.execute("REVOKE ALL ON SCHEMA kyc_private FROM PUBLIC")
                # Supabase API roles must not inherit access to queue data.
                for role in ("anon", "authenticated"):
                    if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                        conn.execute(f"REVOKE ALL ON SCHEMA kyc_private FROM {role}")
        else:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.tx() as db:
            db.execute("CREATE TABLE IF NOT EXISTS research_runs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, created DOUBLE PRECISION NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS research_owner ON research_runs(owner, created)")
            db.execute("CREATE TABLE IF NOT EXISTS research_cache (key TEXT PRIMARY KEY, payload TEXT NOT NULL, expires DOUBLE PRECISION NOT NULL, lease TEXT NOT NULL, lease_until DOUBLE PRECISION NOT NULL)")

    @contextmanager
    def tx(self):
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self.url, row_factory=dict_row, connect_timeout=10) as conn:
                conn.execute("SET LOCAL search_path TO kyc_private")
                conn.execute("SELECT pg_advisory_xact_lock(71826491)")
                yield conn
        else:
            conn = sqlite3.connect(self.path, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            finally:
                conn.close()

    def sql(self, db, statement, args=()):
        return db.execute(statement.replace("?", "%s") if self.postgres else statement, args)

    def _get(self, db, run_id):
        row = self.sql(db, "SELECT payload FROM research_runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def _save(self, db, run):
        run["updated_at"] = time.time()
        self.sql(db, "UPDATE research_runs SET payload=? WHERE id=?", (json.dumps(run), run["id"]))

    @staticmethod
    def event(run, event_type="progress", **data):
        event = {"schema_version": 1, "run_id": run["id"], "id": run["event_seq"] + 1,
                 "timestamp": time.time(), "phase": run["phase"], "stage": run.get("stage", "queued"),
                 "event_type": event_type, **data}
        run["event_seq"] = event["id"]
        run["events"].append(event)
        # Snapshot is authoritative if a reconnect cursor predates this bounded log.
        run["events"] = run["events"][-250:]
        if data.get("message"):
            run["message"] = data["message"]
        return event

    def create(self, owner, ip_hash, company, hint, key, refresh=False):
        fingerprint = hashlib.sha256(json.dumps([company, hint, refresh]).encode()).hexdigest()
        with self.tx() as db:
            rows = self.sql(db, "SELECT payload FROM research_runs WHERE created>?", (time.time() - 86400,)).fetchall()
            recent = [json.loads(r["payload"]) for r in rows]
            for run in recent:
                if run["owner"] == owner and run["idempotency_key"] == key:
                    if run["fingerprint"] != fingerprint:
                        raise Conflict("This request key was already used for different research.")
                    return run
            owned = [r for r in recent if r["owner"] == owner]
            daily_limit = int(os.getenv("DAILY_RUN_LIMIT", "10"))
            if len(owned) >= daily_limit or sum(r["ip_hash"] == ip_hash for r in recent) >= int(os.getenv("IP_DAILY_RUN_LIMIT", "30")) or len(recent) >= int(os.getenv("GLOBAL_DAILY_RUN_LIMIT", "200")):
                raise QuotaExceeded("Today's research allowance is used. Your saved briefs are still available.")
            if any(r["status"] in ACTIVE for r in owned):
                raise Conflict("Finish or cancel your current research before starting another.")
            now = time.time()
            run = {"id": secrets.token_hex(16), "owner": owner, "ip_hash": ip_hash, "created_at": now,
                   "updated_at": now, "idempotency_key": key, "fingerprint": fingerprint,
                   "company_name": company, "status": "queued", "phase": "company", "stage": "queued",
                   "state": {"company_name": company, "company_hint": hint, "completed_nodes": []},
                   "events": [], "event_seq": 0, "lease": "", "lease_until": 0, "attempts": 0,
                   "cancel_requested": False, "refresh": refresh, "feedback": None, "metrics": [],
                   "not_before": 0, "retries": 0, "phase_retries": {"company": 0, "domain": 0, "export": 0}, "export_status": "not_started"}
            self.event(run, message="Your research is queued.")
            self.sql(db, "INSERT INTO research_runs(id,owner,created,payload) VALUES(?,?,?,?)", (run["id"], owner, now, json.dumps(run)))
            return run

    def get(self, run_id, owner=None):
        with self.tx() as db:
            run = self._get(db, run_id)
        if not run or (owner is not None and run["owner"] != owner):
            return None
        return run

    def list(self, owner):
        with self.tx() as db:
            rows = self.sql(db, "SELECT payload FROM research_runs WHERE owner=? ORDER BY created DESC LIMIT 50", (owner,)).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def recent(self, days=30):
        with self.tx() as db:
            rows = self.sql(db, "SELECT payload FROM research_runs WHERE created>?", (time.time() - days * 86400,)).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def cleanup(self, days=30):
        """Explicit operator maintenance: retain active work and remove expired cache."""
        with self.tx() as db:
            rows = self.sql(db, "SELECT payload FROM research_runs WHERE created<?", (time.time() - days * 86400,)).fetchall()
            removed = 0
            for row in rows:
                run = json.loads(row["payload"])
                if run["status"] not in ACTIVE:
                    self.sql(db, "DELETE FROM research_runs WHERE id=?", (run["id"],))
                    removed += 1
            self.sql(db, "DELETE FROM research_cache WHERE expires<? AND lease_until<?", (time.time(), time.time()))
        return removed

    def mutate(self, run_id, action, owner=None, lease=None):
        with self.tx() as db:
            run = self._get(db, run_id)
            if not run or (owner is not None and run["owner"] != owner):
                raise KeyError(run_id)
            if lease is not None and (run["lease"] != lease or run["lease_until"] < time.time()):
                raise LeaseLost()
            action(run)
            self._save(db, run)
            return run

    def claim(self):
        now = time.time()
        with self.tx() as db:
            rows = self.sql(db, "SELECT payload FROM research_runs ORDER BY created ASC").fetchall()
            for row in rows:
                run = json.loads(row["payload"])
                if run["status"] not in ACTIVE or run["lease_until"] > now or run["not_before"] > now:
                    continue
                if run["cancel_requested"]:
                    run["status"] = "cancelled"
                    self._save(db, run)
                    continue
                if run["attempts"] >= 4:
                    run["status"] = "failed"
                    run["failure_category"] = "worker_attempts_exhausted"
                    self.event(run, "error", message="Research was interrupted repeatedly. Completed steps are saved.")
                    self._save(db, run)
                    continue
                run["attempts"] += 1
                run["claimed_at"] = now
                run.setdefault("phase_started_at", now)
                run["queue_wait_seconds"] = max(0, now - run["updated_at"])
                run["lease"] = secrets.token_hex(16)
                run["lease_until"] = now + 60
                run["status"] = {"company": "researching_company", "domain": "researching_domain", "export": "preparing_export"}[run["phase"]]
                self.event(run, message="Research resumed from the last saved step." if run["attempts"] > 1 else "Your researcher is starting.")
                self._save(db, run)
                return run
        return None

    def append(self, run_id, lease, **event):
        def action(run):
            if event.get("event_type") == "metric":
                run["metrics"].append({**event, "timestamp": time.time()})
            else:
                if event.get("stage"):
                    run["stage"] = event["stage"]
                self.event(run, **event)
        return self.mutate(run_id, action, lease=lease)

    def cache_claim(self, key, lease, ttl=60):
        with self.tx() as db:
            row = self.sql(db, "SELECT * FROM research_cache WHERE key=?", (key,)).fetchone()
            now = time.time()
            if row and row["expires"] > now:
                return "hit", json.loads(row["payload"])
            if row and row["lease_until"] > now and row["lease"] != lease:
                return "wait", None
            self.sql(db, "INSERT INTO research_cache(key,payload,expires,lease,lease_until) VALUES(?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET lease=excluded.lease, lease_until=excluded.lease_until", (key, "{}", 0, lease, now + ttl))
            return "claimed", None

    def cache_write(self, key, lease, value, ttl):
        with self.tx() as db:
            self.sql(db, "UPDATE research_cache SET payload=?,expires=?,lease_until=0 WHERE key=? AND lease=?", (json.dumps(value), time.time() + ttl, key, lease))

    def cache_release(self, key, lease):
        with self.tx() as db:
            self.sql(db, "UPDATE research_cache SET lease_until=0 WHERE key=? AND lease=?", (key, lease))
