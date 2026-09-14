from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from threading import Lock
import time
import pytest
from agent.services import search
from agent.services.runtime import context, RunContext, RunCancelled, remaining
from agent.schemas import Brief, validate_citations
from backend.store import Store, LeaseLost
from backend.worker import Worker


def test_exa_content_preserved(monkeypatch):
    monkeypatch.setattr(search, "search_web", lambda _: [])
    monkeypatch.setattr(search, "search_exa", lambda _: [{"url": "https://example.com/A", "content": "Preserve this evidence"}])
    assert search.parallel_search("company")[0]["content"] == "Preserve this evidence"


def test_url_normalization():
    assert search.normalize_url("https://EXAMPLE.com/Case?utm_source=x&v=1#top") == "https://example.com/Case?v=1"
    assert len(search.deduplicate_results([{"url": "https://example.com/A"}, {"url": "https://example.com/a"}])) == 2
    assert search.normalize_url("javascript:alert(1)") == ""


def test_partial_provider_failure(monkeypatch):
    def fail(_):
        raise RuntimeError("not available")
    monkeypatch.setattr(search, "search_web", fail)
    monkeypatch.setattr(search, "search_exa", lambda _: [{"url": "https://example.com", "content": "Available"}])
    assert search.parallel_search("test")[0]["content"] == "Available"
    monkeypatch.setattr(search, "search_exa", fail)
    with pytest.raises(RuntimeError):
        search.parallel_search("test")


def test_concurrency_order_and_speed(monkeypatch):
    lock, active, peak = Lock(), 0, 0
    def provider(query):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.06)
        with lock:
            active -= 1
        return [{"url": "https://example.com/" + query, "content": query}]
    monkeypatch.setattr(search, "search_web", provider)
    monkeypatch.setattr(search, "search_exa", provider)
    monkeypatch.setenv("SEARCH_QUERY_CONCURRENCY", "1")
    start = time.monotonic()
    baseline = search.search_queries([str(i) for i in range(5)])
    sequential = time.monotonic() - start
    monkeypatch.setenv("SEARCH_QUERY_CONCURRENCY", "3")
    start = time.monotonic()
    optimized = search.search_queries([str(i) for i in range(5)])
    concurrent = time.monotonic() - start
    assert 2 < peak <= 6
    assert [r["content"] for r in optimized] == [r["content"] for r in baseline]
    assert concurrent < sequential * 0.8


def test_deadline_and_cancellation():
    token = context.set(RunContext(deadline=time.monotonic() - 1))
    try:
        with pytest.raises(TimeoutError): remaining()
    finally: context.reset(token)
    token = context.set(RunContext(cancelled=lambda: True))
    try:
        with pytest.raises(RunCancelled): remaining()
    finally: context.reset(token)


def test_citation_validation():
    brief = Brief(confidence="HIGH", summary="Coverage", domains=[], sections=[{"title": "Company", "claims": [{"text": "Unsupported", "kind": "fact", "source_ids": ["S99"]}]}])
    with pytest.raises(ValueError): validate_citations(brief, [{"id": "S1"}])
    brief.sections[0].claims[0].source_ids = []
    with pytest.raises(ValueError): validate_citations(brief, [{"id": "S1"}])


def test_wire_schema_keeps_fields_named_title():
    from agent.services.gemini import provider_schema
    wire = provider_schema(Brief)
    assert "title" in wire["$defs"]["Section"]["properties"]
    assert "maxLength" not in wire["$defs"]["Section"]["properties"]["title"]


def test_atomic_claim_and_fencing(db):
    run = db.create("a", "ip", "Example", "", "key-0001")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: db.claim(), range(2)))
    assert sum(r is not None for r in claims) == 1
    claimed = next(r for r in claims if r)
    db.mutate(run["id"], lambda r: r.update(lease_until=0))
    new = db.claim()
    assert new["lease"] != claimed["lease"]
    with pytest.raises(LeaseLost):
        db.mutate(run["id"], lambda r: r.update(status="completed"), lease=claimed["lease"])


def test_cache_freshness_and_coalescing(db):
    assert db.cache_claim("company", "one")[0] == "claimed"
    assert db.cache_claim("company", "two")[0] == "wait"
    db.cache_write("company", "one", {"public": "brief"}, 60)
    assert db.cache_claim("company", "two") == ("hit", {"public": "brief"})
    db.cache_write("company", "one", {}, -1)
    assert db.cache_claim("company", "two")[0] == "claimed"


def test_restart_skips_checkpointed_nodes(db, providers, monkeypatch):
    from agent.graph import durable_node
    from agent.nodes.company import verify_company
    run = db.create("a", "ip", "Northstar Systems", "", "key-0001")
    state = {**run["state"], **verify_company(run["state"]), "completed_nodes": ["verify_company"]}
    db.mutate(run["id"], lambda r: r.update(state=state))
    def fail(_): raise AssertionError("Identity must not repeat")
    monkeypatch.setattr("backend.worker.verify_company", fail)
    assert Worker(db).tick()
    assert db.get(run["id"])["status"] == "awaiting_domain_selection"


def test_production_cannot_fall_back(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError): Store(str(tmp_path / "unsafe.sqlite3"))
