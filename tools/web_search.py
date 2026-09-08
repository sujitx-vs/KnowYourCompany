from tavily import TavilyClient
from dotenv import load_dotenv

import os
import time
import requests


load_dotenv()


tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


def search_web(query, max_retries=3):

    last_error = None

    for attempt in range(max_retries):

        try:

            response = tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=5
            )

            return response.get(
                "results",
                []
            )

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

    raise last_error