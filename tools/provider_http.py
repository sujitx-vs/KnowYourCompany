"""A single bounded HTTP retry policy shared by search providers."""
import os
import random
import time
import httpx
from agent.services.runtime import remaining, emit

def post_json(url, payload, headers=None, attempts=2):
    attempts = min(attempts, int(os.getenv("PROVIDER_ATTEMPTS", "2")))
    for attempt in range(attempts):
        try:
            timeout = remaining(float(os.getenv("SEARCH_TIMEOUT_SECONDS", "18")))
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
            transient = not isinstance(error, httpx.HTTPStatusError) or error.response.status_code in {429, 500, 502, 503, 504}
            if not transient or attempt + 1 >= attempts:
                raise
            delay = min(remaining(2), 0.5 * (2 ** attempt) + random.random() * 0.2)
            emit("metric", metric="provider_retry", value=1)
            time.sleep(delay)
    raise RuntimeError("Provider attempts must be positive")
