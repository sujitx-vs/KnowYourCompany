from agent.services.gemini import (
    extract_text,
    invoke_gemini
)


# ============================================================
# FILTER RELEVANT SEARCH RESULTS
# ============================================================

def filter_relevant_results(
    results,
    company_identity
):
    """
    Filter search results so only results clearly related
    to the verified company are kept.

    This function performs one Gemini call for the entire
    batch of search results.
    """

    # --------------------------------------------------------
    # HANDLE EMPTY RESULTS WITHOUT GEMINI
    # --------------------------------------------------------

    if not results:
        return []


    # --------------------------------------------------------
    # BUILD SEARCH RESULT TEXT
    # --------------------------------------------------------

    results_text = ""

    for index, result in enumerate(
        results,
        start=1
    ):

        results_text += f"""
RESULT {index}

TITLE:
{result.get("title", "")}

URL:
{result.get("url", "")}

CONTENT:
{result.get("content", "")}

-------------------------
"""


    # --------------------------------------------------------
    # GEMINI RELEVANCE FILTER
    # --------------------------------------------------------

    prompt = f"""
You are filtering web search results for company research.

Verified company identity:

{company_identity}

Search results:

{results_text}

Determine which results clearly refer to the verified
company.

Reject results that:

- refer to a different company
- refer to a different organization with a similar name
- are about an unrelated topic with similar keywords
- contain generic information with no clear connection
  to the verified company
- cannot reasonably be connected to the verified company

Do not include a result merely because its wording is
similar to the company name.

Return ONLY the result numbers that are relevant.

Return one number per line.

Example:

1
3
5

If none of the results are relevant, return:

NONE
"""

    response = invoke_gemini(
        prompt
    )

    response = extract_text(
        response
    )


    # --------------------------------------------------------
    # HANDLE NONE RESPONSE
    # --------------------------------------------------------

    if response.strip().upper() == "NONE":
        return []


    # --------------------------------------------------------
    # PARSE SELECTED RESULT NUMBERS
    # --------------------------------------------------------

    selected_indexes = []

    for line in response.splitlines():

        line = line.strip()

        if line.isdigit():

            selected_indexes.append(
                int(line) - 1
            )


    # --------------------------------------------------------
    # BUILD FILTERED RESULT LIST
    # --------------------------------------------------------

    filtered_results = []

    for index in selected_indexes:

        if (
            0 <= index
            < len(results)
        ):

            filtered_results.append(
                results[index]
            )


    return filtered_results