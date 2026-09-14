from urllib.parse import urlsplit
import os
import re
from agent.services.runtime import emit


def select_evidence(results, website="", prefix="S"):
    """Bound text before LLM calls; prefer official pages without excluding disagreements."""
    host = (urlsplit(website).hostname or "").removeprefix("www.")
    def official(result):
        candidate = (urlsplit(result["url"]).hostname or "").removeprefix("www.")
        return bool(host and (candidate == host or candidate.endswith("." + host)))
    # Reserve room for independent sources and possible disagreement, even when
    # many official pages were returned. Do not equate repetition with confidence.
    official_pages = [r for r in results if official(r)]
    independent = [r for r in results if not official(r)]
    ranked = official_pages[:3]
    for index in range(max(len(official_pages[3:]), len(independent))):
        if index < len(independent):
            ranked.append(independent[index])
        if index < len(official_pages[3:]):
            ranked.append(official_pages[3:][index])
    # A UTF-8 byte budget is a conservative upper bound for byte-fallback tokenizers.
    budget = max(2000, int(os.getenv("EVIDENCE_BYTE_BUDGET", "24000")))
    selected, seen_text = [], set()
    for result in ranked[:24]:
        content = re.sub(r"\s+", " ", result.get("content", "")).strip()
        if not content or content in seen_text:
            continue
        seen_text.add(content)
        content = content.encode("utf-8")[:min(2200, budget)].decode("utf-8", errors="ignore")
        if not content:
            break
        selected.append({**result, "content": content, "id": f"{prefix}{len(selected)+1}", "official": official(result)})
        budget -= len(content.encode("utf-8"))
        if budget < 200:
            break
    emit("metric", metric="evidence_bytes", value=sum(len(s["content"].encode("utf-8")) for s in selected))
    return selected
