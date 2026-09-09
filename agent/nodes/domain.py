from langgraph.types import interrupt

from agent.state import ResearchState

from agent.services.gemini import (
    extract_text,
    invoke_gemini
)

from agent.services.evidence import (
    filter_relevant_results
)

from agent.services.search import (
    parallel_search,
    deduplicate_results
)


# ============================================================
# HUMAN DOMAIN SELECTION
# ============================================================

def select_domain(
    state: ResearchState
):

    print(
        "\nWaiting for domain selection..."
    )

    selected_domain = interrupt({
        "message":
            "Please select a job domain "
            "to focus on.",

        "available_domains":
            state[
                "available_domains"
            ]
    })

    return {
        "selected_domain":
            selected_domain
    }


# ============================================================
# RESEARCH SELECTED DOMAIN
# ============================================================

def research_selected_domain(
    state: ResearchState
):

    print(
        f"\nResearching selected domain: "
        f"{state['selected_domain']}..."
    )

    company = state[
        "company_name"
    ]

    domain = state[
        "selected_domain"
    ]

    queries = [
        f"{company} {domain}",
        f"{company} {domain} technologies",
        f"{company} {domain} solutions",
        f"{company} {domain} initiatives",
        f"{company} {domain} careers skills"
    ]

    all_domain_results = []


    # --------------------------------------------------------
    # COLLECT RESULTS FROM ALL DOMAIN QUERIES
    # --------------------------------------------------------

    for query in queries:

        results = parallel_search(
            query
        )

        all_domain_results.extend(
            results
        )


    # --------------------------------------------------------
    # REMOVE DUPLICATES ACROSS ALL DOMAIN QUERIES
    # --------------------------------------------------------

    all_domain_results = (
        deduplicate_results(
            all_domain_results
        )
    )


    # --------------------------------------------------------
    # ONE GEMINI RELEVANCE FILTER PASS
    # --------------------------------------------------------

    filtered_results = (
        filter_relevant_results(
            all_domain_results,
            state[
                "company_identity"
            ]
        )
    )


    return {
        "domain_search_results":
            filtered_results
    }


# ============================================================
# ANALYZE DOMAIN + ASSESS CONFIDENCE
# ============================================================

def analyze_domain(
    state: ResearchState
):

    print(
        f"\nAnalyzing "
        f"{state['selected_domain']} "
        f"domain and assessing evidence confidence..."
    )


    # --------------------------------------------------------
    # HANDLE EMPTY EVIDENCE WITHOUT GEMINI
    # --------------------------------------------------------

    if not state["domain_search_results"]:

        confidence = "INSUFFICIENT"

        print(
            f"\nDomain evidence confidence: "
            f"{confidence}"
        )

        return {
            "domain_evidence_confidence":
                confidence,

            "domain_analysis":
                (
                    "Insufficient verified company-specific "
                    "evidence is available for this domain. "
                    "General preparation advice cannot be "
                    "presented as company-specific "
                    "information."
                )
        }


    # --------------------------------------------------------
    # BUILD DOMAIN RESEARCH EVIDENCE
    # --------------------------------------------------------

    research_text = ""

    for index, result in enumerate(
        state[
            "domain_search_results"
        ],
        start=1
    ):

        research_text += f"""
SOURCE ID: D{index}

TITLE:
{result["title"]}

URL:
{result["url"]}

CONTENT:
{result["content"]}

-------------------------
"""


    # --------------------------------------------------------
    # ONE GEMINI CALL:
    # DOMAIN CONFIDENCE + DOMAIN ANALYSIS
    # --------------------------------------------------------

    prompt = f"""
You are a technical career research assistant helping
a college student prepare for campus placement.

Verified Company Identity:

{state['company_identity']}

Company:

{state['company_name']}

Selected Domain:

{state['selected_domain']}

Filtered domain research:

{research_text}


You have TWO responsibilities:

1. Assess the quality of the evidence for this selected domain.
2. Analyze the selected domain in relation to the verified company.


============================================================
TASK 1 — DOMAIN EVIDENCE CONFIDENCE
============================================================

Classify the available domain evidence into exactly ONE of:

HIGH
MEDIUM
LOW
INSUFFICIENT


Use these rules:

HIGH:
- multiple relevant sources
- strong agreement between sources
- includes authoritative company-specific evidence
- technologies, products, services or initiatives are clearly
  connected to the selected domain

MEDIUM:
- relevant company-specific evidence exists
- multiple sources support important details
- but authoritative evidence is limited or some areas remain uncertain

LOW:
- only a small amount of company-specific evidence exists
- most evidence is third-party
- the relationship between the company and selected domain
  is only partially supported

INSUFFICIENT:
- evidence is too weak to reliably connect the selected domain
  to the company
- very little company-specific information exists
- important domain-specific claims cannot be verified

Do not judge only by the number of sources.

Source quality, relevance and agreement matter more.


============================================================
TASK 2 — DOMAIN ANALYSIS
============================================================

Analyze the selected domain specifically in relation
to the verified company.

Cover:

1. Domain Relevance to the Company
2. Relevant Technologies & Tools
3. Skills to Prepare
4. Important Concepts to Study
5. Relevant Project Areas
6. Likely Technical Interview Topics
7. Company-Specific Preparation Advice


EVIDENCE RULES:

Every COMPANY-SPECIFIC factual claim must be supported
by one or more supplied source IDs.

Use citations such as:

[D1]
[D2][D5]


Do not claim that the company:

- uses a technology
- develops a product
- runs a project
- uses an AI model
- operates a platform
- follows a specific engineering practice

unless this is explicitly supported by the supplied
sources.


Do not infer company technologies from generic
information about the selected domain.


If company-specific evidence is unavailable, write:

"Insufficient verified company-specific evidence."


Recommendations for what a student should study are
allowed, but clearly label them as recommendations
rather than company facts.


Do not invent:

- technologies
- projects
- products
- engineering practices
- interview questions
- company-specific requirements


============================================================
RESPONSE FORMAT
============================================================

Return exactly this structure:

CONFIDENCE: HIGH

ANALYSIS:
<domain analysis here>


The confidence value MUST be exactly one of:

HIGH
MEDIUM
LOW
INSUFFICIENT
"""

    response = invoke_gemini(
        prompt
    )

    response = extract_text(
        response
    )


    # --------------------------------------------------------
    # PARSE CONFIDENCE + ANALYSIS
    # --------------------------------------------------------

    confidence = "LOW"
    domain_text = ""

    if "ANALYSIS:" in response:

        confidence_section, domain_text = (
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

        allowed_confidence = {
            "HIGH",
            "MEDIUM",
            "LOW",
            "INSUFFICIENT"
        }

        if (
            confidence_section
            in allowed_confidence
        ):

            confidence = (
                confidence_section
            )

        domain_text = (
            domain_text.strip()
        )

    else:

        domain_text = (
            response.strip()
        )


    print(
        f"\nDomain evidence confidence: "
        f"{confidence}"
    )


    # --------------------------------------------------------
    # HANDLE INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    if confidence == "INSUFFICIENT":

        return {
            "domain_evidence_confidence":
                confidence,

            "domain_analysis":
                (
                    "Insufficient verified company-specific "
                    "evidence is available for this domain. "
                    "General preparation advice cannot be "
                    "presented as company-specific "
                    "information."
                )
        }


    # --------------------------------------------------------
    # RETURN COMBINED RESULT
    # --------------------------------------------------------

    return {
        "domain_analysis":
            domain_text,

        "domain_evidence_confidence":
            confidence
    }