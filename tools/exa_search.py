import os
import time
import requests

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


EXA_API_KEY = os.getenv("EXA_API_KEY")

EXA_SEARCH_URL = "https://api.exa.ai/search"


# ============================================================
# EXA SEARCH
# ============================================================

def search_exa(query, max_retries=3):

    if not EXA_API_KEY:
        raise ValueError(
            "EXA_API_KEY was not found in .env"
        )

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,

        # Let Exa choose the best search approach
        "type": "auto",

        # Keep result count reasonable
        "numResults": 5,

        # Ask Exa to return page text
        "contents": {
            "text": True
        }
    }

    last_error = None

    for attempt in range(max_retries):

        try:

            response = requests.post(
                EXA_SEARCH_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            results = []

            for result in data.get(
                "results",
                []
            ):

                results.append({
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

                    # IMPORTANT:
                    # Convert Exa's "text"
                    # into our common "content" field
                    "content":
                        result.get(
                            "text",
                            ""
                        ),

                    "source":
                        "exa"
                })

            return results

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout
        ) as e:

            last_error = e

            if attempt < max_retries - 1:

                time.sleep(
                    2 * (attempt + 1)
                )

                continue

            raise

        except requests.exceptions.HTTPError:

            # Authentication errors,
            # rate limits, invalid request, etc.
            raise

    raise last_error