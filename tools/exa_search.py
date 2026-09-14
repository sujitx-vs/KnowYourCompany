import os
from tools.provider_http import post_json

def search_exa(query, max_retries=2):
    key = os.getenv("EXA_API_KEY")
    if not key:
        raise RuntimeError("Exa is not configured")
    response = post_json("https://api.exa.ai/search", {
        "query": query, "type": "auto", "numResults": 5,
        "contents": {"text": {"maxCharacters": 4000}},
    }, {"x-api-key": key}, max_retries)
    return [{"title": r.get("title", ""), "url": r.get("url", ""),
             "content": r.get("text", ""), "published_at": r.get("publishedDate"),
             "source": "exa"} for r in response.get("results", [])]
