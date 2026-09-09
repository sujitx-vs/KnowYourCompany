from concurrent.futures import ThreadPoolExecutor

from tools.web_search import search_web
from tools.exa_search import search_exa


# ============================================================
# DEDUPLICATE SEARCH RESULTS
# ============================================================

def deduplicate_results(results):
    """
    Remove duplicate search results using normalized URLs.

    Example:
    https://www.tcs.com/careers
    https://www.tcs.com/careers/

    These will be treated as the same result.
    """

    seen_urls = set()
    unique_results = []

    for result in results:

        url = (
            result.get("url", "")
            .strip()
            .lower()
            .rstrip("/")
        )

        # ----------------------------------------------------
        # If URL is missing, keep the result.
        # We cannot reliably determine whether it is duplicate.
        # ----------------------------------------------------

        if not url:
            unique_results.append(
                result
            )
            continue

        # ----------------------------------------------------
        # Skip duplicate URL
        # ----------------------------------------------------

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        unique_results.append(
            result
        )

    return unique_results


# ============================================================
# PARALLEL WEB SEARCH
# ============================================================

def parallel_search(query):
    """
    Search Tavily and Exa concurrently.

    Then:
    1. Normalize both providers
    2. Merge the results
    3. Remove duplicate URLs

    Returns:
        A normalized and deduplicated list of search results.
    """

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:

        tavily_future = executor.submit(
            search_web,
            query
        )

        exa_future = executor.submit(
            search_exa,
            query
        )

        tavily_results = (
            tavily_future.result()
        )

        exa_results = (
            exa_future.result()
        )


    # ========================================================
    # NORMALIZE TAVILY
    # ========================================================

    normalized_tavily = []

    for result in tavily_results:

        normalized_tavily.append({
            "title":
                result.get(
                    "title",
                    ""
                ),

            "url":
                result.get(
                    "url",
                    ""
                ),

            "content":
                result.get(
                    "content",
                    ""
                ),

            "source":
                "tavily"
        })


    # ========================================================
    # NORMALIZE EXA
    # ========================================================

    normalized_exa = []

    for result in exa_results:

        normalized_exa.append({
            "title":
                result.get(
                    "title",
                    ""
                ),

            "url":
                result.get(
                    "url",
                    ""
                ),

            "content":
                result.get(
                    "text",
                    ""
                ),

            "source":
                "exa"
        })


    # ========================================================
    # MERGE PROVIDER RESULTS
    # ========================================================

    merged_results = (
        normalized_tavily
        +
        normalized_exa
    )


    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique_results = (
        deduplicate_results(
            merged_results
        )
    )


    return unique_results