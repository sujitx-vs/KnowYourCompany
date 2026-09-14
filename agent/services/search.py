"""Bounded provider work, stable ordering and a single normalized evidence contract."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
from datetime import datetime, timezone
from threading import BoundedSemaphore
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import os
import time
import hashlib
import json
from tools.web_search import search_web
from tools.exa_search import search_exa
from agent.services.runtime import emit, remaining, RunCancelled, context

POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="search")
LIMITS = {name: BoundedSemaphore(3) for name in ("tavily", "exa")}

def normalize_url(url):
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username:
            return ""
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))
    except ValueError:
        return ""

def deduplicate_results(results):
    seen, unique = {}, []
    for result in results:
        url = normalize_url(result.get("url", ""))
        if not url:
            continue
        item = {**result, "url": url}
        if url in seen:
            old = unique[seen[url]]
            if len(item.get("content", "")) > len(old.get("content", "")):
                unique[seen[url]] = item
        else:
            seen[url] = len(unique)
            unique.append(item)
    return unique

def _search(provider, query):
    start = time.monotonic()
    ctx = context.get()
    cache = ctx.cache if ctx and not ctx.refresh and os.getenv("SEARCH_CACHE_ENABLED", "true") == "true" else None
    key = "search:" + hashlib.sha256(json.dumps([provider, query, "normalized-v2", os.getenv("TAVILY_SEARCH_DEPTH", "basic")]).encode()).hexdigest()
    claimed = False
    if cache:
        outcome, value = cache.cache_claim(key, ctx.cache_lease, ttl=60)
        if outcome == "hit":
            emit("metric", metric="search_cache_hit", provider=provider, value=1)
            return value
        claimed = outcome == "claimed"
    if not LIMITS[provider].acquire(timeout=remaining(30)):
        raise TimeoutError("Provider capacity exhausted")
    try:
        remaining()
        results = (search_web if provider == "tavily" else search_exa)(query)
        now = datetime.now(timezone.utc).isoformat()
        normalized = [{"title": str(r.get("title", ""))[:300], "url": r.get("url", ""),
                 "content": str(r.get("content") or r.get("text") or "")[:6000],
                 "source": provider, "retrieved_at": now,
                 "published_at": r.get("published_at") or r.get("published_date")} for r in results]
        if claimed and normalized:
            # News expires sooner than stable public company pages. This cache
            # contains provider evidence only, never a user's preparation brief.
            ttl = int(os.getenv("NEWS_SEARCH_TTL_SECONDS", "1800")) if any(word in query.lower() for word in ("recent", "news", "developments")) else int(os.getenv("STABLE_SEARCH_TTL_SECONDS", "21600"))
            cache.cache_write(key, ctx.cache_lease, normalized, ttl)
        return normalized
    finally:
        LIMITS[provider].release()
        if claimed:
            cache.cache_release(key, ctx.cache_lease)
        emit("metric", metric="provider_seconds", provider=provider, value=round(time.monotonic() - start, 3))

def search_queries(queries):
    width = max(1, min(3, int(os.getenv("SEARCH_QUERY_CONCURRENCY", "3"))))
    ordered, completed, successes = {}, 0, 0
    for offset in range(0, len(queries), width):
        remaining()
        pending = {POOL.submit(copy_context().run, _search, provider, query): (offset + i, provider)
                   for i, query in enumerate(queries[offset:offset + width]) for provider in LIMITS}
        per_query = {}
        try:
            for future in as_completed(pending, timeout=remaining(90)):
                index, provider = pending[future]
                try:
                    ordered[(index, provider)] = future.result()
                    successes += 1
                except RunCancelled:
                    raise
                except Exception:
                    ordered[(index, provider)] = []
                    emit("warning", message="One source service is unavailable. Continuing with the available sources.")
                per_query[index] = per_query.get(index, 0) + 1
                if per_query[index] == 2:
                    completed += 1
                    emit(message=f"Completed {completed} of {len(queries)} research searches.", completed=completed, total=len(queries))
                remaining()
        finally:
            for future in pending:
                future.cancel()
    if not successes:
        raise RuntimeError("Search providers are unavailable")
    return deduplicate_results([r for key in sorted(ordered) for r in ordered[key]])

def parallel_search(query):
    return search_queries([query])
