"""Repeatable offline latency benchmark. No provider requests or credentials."""
import json
from pathlib import Path
import statistics
import time
from unittest.mock import patch
from agent.services.search import search_queries


def provider(query):
    time.sleep(0.1)
    return [{"url": "https://example.com/" + query, "content": "Evidence for " + query}]


def main():
    records = {}
    with patch("agent.services.search.search_web", provider), patch("agent.services.search.search_exa", provider):
        for label, width in [("sequential_queries", "1"), ("bounded_parallel_queries", "3")]:
            durations = []
            with patch.dict("os.environ", {"SEARCH_QUERY_CONCURRENCY": width}):
                for _ in range(10):
                    start = time.perf_counter()
                    result = search_queries([str(i) for i in range(5)])
                    durations.append(time.perf_counter() - start)
                    assert len(result) == 5
            records[label] = {"median_seconds": statistics.median(durations), "p95_seconds": sorted(durations)[-1]}
    records["median_reduction_percent"] = round(100 * (1 - records["bounded_parallel_queries"]["median_seconds"] / records["sequential_queries"]["median_seconds"]), 1)
    records["scope"] = "Synthetic search scheduling only; 100ms provider fixtures, ten repeats. Not end-to-end live research."
    path = Path("docs/verification/search-benchmark.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
