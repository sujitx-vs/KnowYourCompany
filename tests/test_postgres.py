"""Runs in CI against a dedicated PostgreSQL service, never the app database."""
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.store import Store


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Dedicated test PostgreSQL not configured")
def test_postgres_durability_and_atomic_claim(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    db = Store(os.environ["TEST_POSTGRES_URL"])
    owner = secrets.token_hex(32)
    run = db.create(owner, owner, "Database fixture", "", secrets.token_hex(16))
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda _: db.claim(), range(2)))
        assert sum(c is not None and c["id"] == run["id"] for c in claims) == 1
        fresh = Store(os.environ["TEST_POSTGRES_URL"])
        assert fresh.get(run["id"], owner)["company_name"] == "Database fixture"
        assert fresh.get(run["id"], "other") is None
        with fresh.tx() as conn:
            assert conn.execute("SELECT current_schema() AS name").fetchone()["name"] == "kyc_private"
    finally:
        with db.tx() as conn:
            db.sql(conn, "DELETE FROM research_runs WHERE id=?", (run["id"],))
