import os
import requests

from dotenv import load_dotenv


# Load environment variables
load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")

EXA_SEARCH_URL = "https://api.exa.ai/search"


def search_exa(query):

    if not EXA_API_KEY:
        raise ValueError(
            "EXA_API_KEY not found in .env"
        )

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "type": "auto",
        "numResults": 5,
        "contents": {
            "text": True
        }
    }

    response = requests.post(
        EXA_SEARCH_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    query = input(
        "\nEnter search query: "
    ).strip()

    print("\nSearching Exa...\n")

    results = search_exa(query)

    print(
        f"Found {len(results)} results\n"
    )

    for i, result in enumerate(
        results,
        start=1
    ):

        print("=" * 70)
        print(f"RESULT {i}")
        print("=" * 70)

        print(
            "Title:",
            result.get("title")
        )

        print(
            "URL:",
            result.get("url")
        )

        print(
            "Published Date:",
            result.get("publishedDate")
        )

        print("\nContent:")

        text = result.get(
            "text",
            ""
        )

        print(text[:1000])

        print()