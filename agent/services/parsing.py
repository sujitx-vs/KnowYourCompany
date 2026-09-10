# ============================================================
# PARSE CONFIDENCE + ANALYSIS RESPONSE
# ============================================================

def parse_confidence_analysis(
    response,
    default_confidence="LOW"
):
    """
    Parse a Gemini response in this format:

    CONFIDENCE: HIGH

    ANALYSIS:
    <analysis text>

    Returns:
        (confidence, analysis_text)
    """

    allowed_confidence = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "INSUFFICIENT"
    }

    confidence = default_confidence
    analysis_text = response.strip()

    if "ANALYSIS:" in response:

        confidence_section, analysis_text = (
            response.split(
                "ANALYSIS:",
                1
            )
        )

        confidence_section = (
            confidence_section
            .replace(
                "CONFIDENCE:",
                ""
            )
            .strip()
            .upper()
        )

        if (
            confidence_section
            in allowed_confidence
        ):
            confidence = (
                confidence_section
            )

        analysis_text = (
            analysis_text.strip()
        )

    return (
        confidence,
        analysis_text
    )


# ============================================================
# FORMAT SEARCH EVIDENCE
# ============================================================

def format_evidence(
    results,
    prefix="S"
):
    """
    Convert normalized search results into a consistent
    evidence block for Gemini prompts.

    Example source IDs:
    S1, S2, S3
    D1, D2, D3
    """

    evidence_text = ""

    for index, result in enumerate(
        results,
        start=1
    ):

        evidence_text += f"""
SOURCE ID: {prefix}{index}

TITLE:
{result.get("title", "")}

URL:
{result.get("url", "")}

CONTENT:
{result.get("content", "")}

-------------------------
"""

    return evidence_text


# ============================================================
# PARSE NUMBERED LIST
# ============================================================

def parse_numbered_list(
    text
):
    """
    Convert:

    1. AI / Machine Learning
    2. Cloud / DevOps

    into:

    [
        "AI / Machine Learning",
        "Cloud / DevOps"
    ]
    """

    items = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        if (
            line[0].isdigit()
            and "." in line
        ):

            item = line.split(
                ".",
                1
            )[-1].strip()

            if (
                item
                and item not in items
            ):

                items.append(
                    item
                )

    return items