"""Fail early on invalid deployment settings without printing credentials."""
import json
import os
from urllib.parse import urlsplit


def validate_configuration():
    bounds = {
        "WORKER_CONCURRENCY": (1, 4), "SEARCH_QUERY_CONCURRENCY": (1, 3),
        "PROVIDER_ATTEMPTS": (1, 2), "SEARCH_TIMEOUT_SECONDS": (1, 60),
        "RUN_PHASE_TIMEOUT_SECONDS": (10, 600), "EVIDENCE_BYTE_BUDGET": (2000, 64000),
        "DAILY_RUN_LIMIT": (1, 1000), "IP_DAILY_RUN_LIMIT": (1, 10000),
        "GLOBAL_DAILY_RUN_LIMIT": (1, 100000), "NEWS_SEARCH_TTL_SECONDS": (1, 86400),
        "STABLE_SEARCH_TTL_SECONDS": (1, 604800), "COMPANY_CACHE_TTL_SECONDS": (1, 86400),
    }
    for name, (minimum, maximum) in bounds.items():
        if name in os.environ:
            try:
                value = int(os.environ[name])
            except ValueError:
                raise RuntimeError(f"{name} must be an integer") from None
            if not minimum <= value <= maximum:
                raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    for name in ("EMBEDDED_WORKER", "RESEARCH_CACHE_ENABLED", "SEARCH_CACHE_ENABLED"):
        if os.getenv(name, "true").lower() not in {"true", "false"}:
            raise RuntimeError(f"{name} must be true or false")
    for name in ("MODEL_PRICES_JSON", "SEARCH_PRICES_JSON"):
        try:
            prices = json.loads(os.getenv(name, "{}"))
            if not isinstance(prices, dict):
                raise ValueError()
            for rate in prices.values():
                values = [rate["input"], rate["output"]] if name == "MODEL_PRICES_JSON" else [rate]
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 for v in values):
                    raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise RuntimeError(f"{name} must contain non-negative numeric prices") from None
    if os.getenv("APP_ENV") == "production":
        for name in ("GOOGLE_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "FRONTEND_URL"):
            if not os.getenv(name):
                raise RuntimeError(f"Production requires {name}")
        if not (os.getenv("TAVILY_API_KEY") or os.getenv("EXA_API_KEY")):
            raise RuntimeError("Production requires a search provider API key")
        for origin in os.environ["FRONTEND_URL"].split(","):
            parsed = urlsplit(origin.strip())
            if parsed.scheme != "https" or not parsed.hostname or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username or "*" in origin:
                raise RuntimeError("Production FRONTEND_URL must list exact HTTPS origins")
