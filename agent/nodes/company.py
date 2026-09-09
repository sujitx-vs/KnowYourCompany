from agent.state import ResearchState

from agent.services.gemini import (
    extract_text,
    invoke_gemini
)

from agent.services.search import (
    parallel_search,
    deduplicate_results
)

from agent.services.evidence import (
    filter_relevant_results
)


# ============================================================
# VERIFY COMPANY
# ============================================================

def verify_company(
    state: ResearchState
):

    if state.get("company_identity"):
        print("\nUsing cached company identity.")
        return {}

    company = state[
        "company_name"
    ]

    print(
        f"\nVerifying company identity: "
        f"{company}..."
    )

    query = (
        f'"{company}" '
        f'company official website '
        f'location industry'
    )

    results = parallel_search(
        query
    )

    research_text = ""

    for result in results:

        research_text += (
            f"\nTitle: "
            f"{result.get('title', '')}\n"
        )

        research_text += (
            f"URL: "
            f"{result.get('url', '')}\n"
        )

        research_text += (
            f"Content: "
            f"{result.get('content', '')}\n"
        )

    prompt = f"""
You are verifying the identity of a company before
a research agent performs deeper research.

User-provided company name:

{company}

Search results:

{research_text}

Determine the most likely company identity.

Return:

Company Name:
Location:
Industry:
Official Website:
Identity Confidence:

Rules:

- Do not guess.
- Do not infer an industry from the company name.
- Use only evidence found in the supplied search results.
- If a field cannot be verified, write "Not verified".
- Identity Confidence must be one of:
  High
  Medium
  Low

Your task is ONLY to establish which company the user
most likely means.

Do not provide products, technologies, interview advice,
or general company research.
"""

    identity = invoke_gemini(
        prompt
    )

    identity = extract_text(
        identity
    )

    print(
        "\nCompany identity verified."
    )

    return {
        "company_identity":
            identity
    }


# ============================================================
# RESEARCH COMPANY
# ============================================================

def research_company(
    state: ResearchState
):

    if state.get("search_results"):
        print("\nUsing cached company research results.")
        return {}

    print(
        f"\nResearching "
        f"{state['company_name']}..."
    )

    company = state[
        "company_name"
    ]

    queries = [
        f"{company} company overview",
        f"{company} products services technologies",
        f"{company} business areas industries",
        f"{company} recent news developments",
        f"{company} technology initiatives"
    ]

    all_results = []


    # --------------------------------------------------------
    # COLLECT RESULTS FROM ALL SEARCH QUERIES
    # --------------------------------------------------------

    for query in queries:

        results = parallel_search(
            query
        )

        all_results.extend(
            results
        )


    # --------------------------------------------------------
    # REMOVE DUPLICATES ACROSS ALL QUERIES
    # --------------------------------------------------------

    all_results = deduplicate_results(
        all_results
    )


    # --------------------------------------------------------
    # ONE GEMINI RELEVANCE FILTER PASS
    # --------------------------------------------------------

    filtered_results = (
        filter_relevant_results(
            all_results,
            state[
                "company_identity"
            ]
        )
    )


    return {
        "search_results":
            filtered_results
    }


# ============================================================
# ANALYZE COMPANY RESEARCH + ASSESS CONFIDENCE
# ============================================================

def analyze_research(
    state: ResearchState
):

    print(
        "\nAnalyzing research and "
        "assessing evidence confidence..."
    )


    # --------------------------------------------------------
    # HANDLE EMPTY EVIDENCE WITHOUT GEMINI
    # --------------------------------------------------------

    if not state["search_results"]:

        confidence = "INSUFFICIENT"

        print(
            f"\nCompany evidence confidence: "
            f"{confidence}"
        )

        return {
            "company_evidence_confidence":
                confidence,

            "analysis":
                (
                    "Insufficient verified evidence is "
                    "available to produce a reliable "
                    "company research summary. "
                    "The available public sources do not "
                    "provide enough company-specific "
                    "information."
                )
        }


    # --------------------------------------------------------
    # BUILD RESEARCH EVIDENCE TEXT
    # --------------------------------------------------------

    research_text = ""

    for index, result in enumerate(
        state["search_results"],
        start=1
    ):

        research_text += f"""
SOURCE ID: S{index}

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
    # CONFIDENCE + COMPANY ANALYSIS
    # --------------------------------------------------------

    prompt = f"""
You are researching a company for a student preparing
for campus placement.

Verified Company Identity:

{state['company_identity']}

User-provided Company Name:

{state['company_name']}

Below are filtered web sources believed to refer to
this company.

{research_text}


You have TWO responsibilities:

1. Assess the quality of the available evidence.
2. Produce a reliable company-level research analysis.


============================================================
TASK 1 — EVIDENCE CONFIDENCE
============================================================

Classify the evidence into exactly ONE of:

HIGH
MEDIUM
LOW
INSUFFICIENT


Use these rules:

HIGH:
- multiple relevant sources
- strong agreement between sources
- includes authoritative sources such as official company
  pages, reports, careers pages or press releases

MEDIUM:
- relevant evidence exists
- multiple sources support important facts
- but official or authoritative evidence is limited

LOW:
- only a small amount of relevant information exists
- evidence is mostly third-party
- important details remain uncertain

INSUFFICIENT:
- evidence is too weak to reliably describe the company
- results contain very little company-specific information
- important claims cannot be verified

Do not judge evidence quality only by the number of
sources.

Source quality, relevance and agreement matter more.


============================================================
TASK 2 — COMPANY ANALYSIS
============================================================

Analyze the sources and provide a reliable
company-level research summary.

Cover:

- Company overview
- Major products and services
- Business areas and industries
- Important technologies
- Major technology initiatives
- Recent developments
- Technical and non-technical job domains that appear
  relevant to this company


EVIDENCE RULES:

Every factual company-specific claim MUST be directly
supported by at least one supplied source.

Add the supporting SOURCE ID after factual claims.

Example:

The company provides cloud communication services. [S2]

If multiple sources support a statement:

The company operates across cloud and cybersecurity
services. [S1][S4]


Do NOT:

- infer technologies merely because they are common
  in the company's industry
- infer products from the company name
- infer technologies from job-domain terminology
- combine unrelated facts into a new unsupported claim
- use general knowledge not contained in these sources
- invent missing details


If the evidence does not support a requested detail,
write:

"Insufficient verified evidence."


SOURCE RELIABILITY:

Prefer, in this order:

1. Official company website
2. Official reports or documents
3. Official career pages
4. Official press releases
5. Reliable third-party sources

If sources disagree, prefer the more authoritative
source and mention the uncertainty.


JOB DOMAIN RULES:

Identify broad career or technical domains,
not individual vacancies.

Only include a domain when there is evidence in the
provided sources that it is relevant to this company.

Do not assume that common domains such as AI,
Machine Learning, Cloud, Cybersecurity or DevOps
exist at the company unless supported by evidence.

Keep the analysis factual and concise.


============================================================
RESPONSE FORMAT
============================================================

Return exactly this structure:

CONFIDENCE: HIGH

ANALYSIS:
<company analysis here>


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
    analysis_text = ""

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

        analysis_text = (
            analysis_text.strip()
        )

    else:

        analysis_text = (
            response.strip()
        )


    print(
        f"\nCompany evidence confidence: "
        f"{confidence}"
    )


    # --------------------------------------------------------
    # HANDLE INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    if confidence == "INSUFFICIENT":

        return {
            "company_evidence_confidence":
                confidence,

            "analysis":
                (
                    "Insufficient verified evidence is "
                    "available to produce a reliable "
                    "company research summary. "
                    "The available public sources do not "
                    "provide enough company-specific "
                    "information."
                )
        }


    # --------------------------------------------------------
    # RETURN COMBINED RESULT
    # --------------------------------------------------------

    return {
        "analysis":
            analysis_text,

        "company_evidence_confidence":
            confidence
    }


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_report(
    state: ResearchState
):

    print(
        "\nGenerating structured report..."
    )

    prompt = f"""
You are an expert career research assistant helping a student
prepare for a campus placement.

Company:
{state['company_name']}

Use the analysis below:

{state['analysis']}

Create PART A of the placement preparation report.

Use exactly this structure:

# {state['company_name']} - Placement Preparation Report

## 1. Company Overview

Explain:
- what the company does
- its major business areas
- industries or markets it serves
- important company context useful for a placement candidate

## 2. Products & Services

Explain the company's important products, platforms,
solutions and services supported by the research.

## 3. Technologies & Business Domains

Explain:
- important technologies used by the company
- major technical areas
- major business domains
- technology initiatives supported by the research

Do NOT provide candidate preparation advice here.

## 4. Recent Developments

Summarize important recent developments, initiatives,
partnerships, launches or technology changes supported
by the research.

## 5. Roles & Hiring Areas

Explain the broad technical and non-technical career
domains that appear relevant to the company.

Keep this section at the DOMAIN level.

For example:
- Networking
- Cloud
- Cybersecurity
- Software Engineering
- Enterprise Sales

Do NOT provide:
- skills to prepare
- interview questions
- technical interview topics
- preparation recommendations
- project recommendations

These topics will be covered separately after the student
selects a specific domain.

Rules:

- Use only information supported by the analysis.
- Do not invent company facts.
- Clearly distinguish confirmed company information from
  general observations.
- Keep the report concise and practical.
- Avoid repeating the same information across sections.
- Do not include a "Skills to Prepare" section.
- Do not include a "Likely Technical Interview Topics" section.
- Do not include a "Company-Specific Interview Preparation" section.
- Do not include candidate recommendations in PART A.
"""

    report_text = invoke_gemini(
        prompt
    )

    report_text = extract_text(
        report_text
    )

    return {
        "report":
            report_text
    }


# ============================================================
# GENERATE DOMAINS
# ============================================================

def generate_domains(
    state: ResearchState
):

    if state.get("available_domains"):
        print("\nUsing cached domain list.")
        return {}

    print(
        "\nIdentifying relevant job domains..."
    )

    prompt = f"""
You are analyzing a company for a college student preparing
for campus placement.

Company:
{state['company_name']}

Company research:

{state['analysis']}

Based ONLY on this research, identify broad job domains
relevant to this company.

Important:

- Identify domains, not individual job postings.
- Do NOT list vacancies.
- Do NOT invent unsupported domains.
- Keep them broad.

Return ONLY a numbered list.

Example:

1. AI / Machine Learning
2. Cloud / DevOps
3. Software Development
4. Cybersecurity
"""

    domains_text = invoke_gemini(
        prompt
    )

    domains_text = extract_text(
        domains_text
    )

    if not isinstance(
        domains_text,
        str
    ):

        raise TypeError(
            "Domain response could not "
            "be converted to text."
        )

    domains = []

    for line in (
        domains_text.splitlines()
    ):

        line = line.strip()

        if not line:
            continue

        if (
            line[0].isdigit()
            and "." in line
        ):

            domain = line.split(
                ".",
                1
            )[-1].strip()

            if domain:

                domains.append(
                    domain
                )

    if not domains:

        raise ValueError(
            "Gemini did not return "
            "any valid job domains."
        )

    return {
        "available_domains":
            domains
    }