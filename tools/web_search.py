import os
from tools.provider_http import post_json

def search_web(query, max_retries=2):
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("Tavily is not configured")
    response = post_json("https://api.tavily.com/search", {
        "query": query, "search_depth": os.getenv("TAVILY_SEARCH_DEPTH", "basic"),
        "max_results": 5, "include_raw_content": False,
    }, {"Authorization": f"Bearer {key}"}, max_retries)
    return response.get("results", [])
