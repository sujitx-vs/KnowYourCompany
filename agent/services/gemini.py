from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GEMINI MODELS
# ============================================================

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash"
]


# ============================================================
# NORMALIZE GEMINI RESPONSE TO PLAIN TEXT
# ============================================================

def extract_text(value):
    """
    Convert Gemini / LangChain responses into plain text.

    Handles:
    - normal string
    - AIMessage
    - structured content list
    - dictionary text blocks
    """

    if isinstance(value, str):
        return value.strip()

    if hasattr(value, "content"):
        return extract_text(value.content)

    if isinstance(value, list):

        text_parts = []

        for block in value:

            text = extract_text(block)

            if text:
                text_parts.append(text)

        return "\n".join(text_parts).strip()

    if isinstance(value, dict):

        text = value.get("text")

        if isinstance(text, str):
            return text.strip()

        return ""

    return ""


# ============================================================
# GEMINI FALLBACK
# ============================================================

def invoke_gemini(prompt):
    """
    Call Gemini silently using fallback models.

    Returns:
        Plain-text Gemini response.
    """

    last_error = None

    for model_name in GEMINI_MODELS:

        try:

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=os.getenv(
                    "GOOGLE_API_KEY"
                )
            )

            silent_stdout = StringIO()
            silent_stderr = StringIO()

            with (
                redirect_stdout(silent_stdout),
                redirect_stderr(silent_stderr)
            ):

                response = llm.invoke(
                    prompt
                )

            text = extract_text(
                response
            )

            if not text:

                raise ValueError(
                    f"Gemini model {model_name} "
                    f"returned no usable text."
                )

            return text

        except Exception as error:

            last_error = error

            error_text = str(
                error
            )

            fallback_errors = [
                "404",
                "429",
                "503",
                "NOT_FOUND",
                "RESOURCE_EXHAUSTED",
                "UNAVAILABLE"
            ]

            should_fallback = any(
                fallback_error in error_text
                for fallback_error
                in fallback_errors
            )

            if should_fallback:
                continue

            raise

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "No Gemini models were available."
    )