from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from langchain_google_genai import ChatGoogleGenerativeAI

from dotenv import load_dotenv

from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

import os
from concurrent.futures import ThreadPoolExecutor

from agent.state import ResearchState
from tools.web_search import search_web
from tools.exa_search import search_exa
from tools.pdf_generator import create_placement_pdf


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

    # Already plain text
    if isinstance(value, str):
        return value.strip()

    # AIMessage / LangChain message object
    if hasattr(value, "content"):
        return extract_text(value.content)

    # Structured content blocks
    if isinstance(value, list):

        text_parts = []

        for block in value:

            text = extract_text(block)

            if text:
                text_parts.append(text)

        return "\n".join(text_parts).strip()

    # Gemini/LangChain dictionary content block
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
    Call Gemini silently.

    No Gemini response is printed.
    No Gemini SDK warning is printed.
    Returns only plain text.
    """

    last_error = None

    for model_name in GEMINI_MODELS:

        try:

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )

            # ------------------------------------------------
            # Suppress SDK stdout/stderr
            # ------------------------------------------------

            silent_stdout = StringIO()
            silent_stderr = StringIO()

            with redirect_stdout(silent_stdout), redirect_stderr(silent_stderr):

                response = llm.invoke(prompt)

            # Always convert response to normal string
            text = extract_text(response)

            if not text:
                raise ValueError(
                    f"Gemini model {model_name} "
                    f"returned no usable text."
                )

            return text

        except Exception as e:

            last_error = e

            error_text = str(e)

            fallback_errors = [
                "404",
                "429",
                "503",
                "NOT_FOUND",
                "RESOURCE_EXHAUSTED",
                "UNAVAILABLE"
            ]

            should_fallback = any(
                error in error_text
                for error in fallback_errors
            )

            if should_fallback:
                continue

            raise

    raise last_error


# ============================================================
# COMPANY RESEARCH
# ============================================================

def parallel_search(query):

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


    # ================================================
    # NORMALIZE TAVILY
    # ================================================

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


    # ================================================
    # NORMALIZE EXA
    # ================================================

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


    # ================================================
    # MERGE
    # ================================================

    return (
        normalized_tavily
        +
        normalized_exa
    )

def filter_relevant_results(
    results,
    company_identity
):

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

    selected_indexes = []

    for line in response.splitlines():

        line = line.strip()

        if line.isdigit():

            selected_indexes.append(
                int(line) - 1
            )

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

def assess_evidence_confidence(
    results,
    company_identity,
    context
):

    if not results:
        return "INSUFFICIENT"

    results_text = ""

    for index, result in enumerate(
        results,
        start=1
    ):

        results_text += f"""
SOURCE {index}

TITLE:
{result.get("title", "")}

URL:
{result.get("url", "")}

CONTENT:
{result.get("content", "")}

-------------------------
"""

    prompt = f"""
You are evaluating the quality of evidence collected
for company research.

Verified company identity:

{company_identity}

Research context:

{context}

Sources:

{results_text}

Classify the available evidence into exactly ONE of:

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

Do not judge based only on the number of sources.

Source quality, relevance and agreement matter more.

Return ONLY:

HIGH

or

MEDIUM

or

LOW

or

INSUFFICIENT
"""

    response = invoke_gemini(
        prompt
    )

    confidence = (
        extract_text(response)
        .strip()
        .upper()
    )

    allowed = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "INSUFFICIENT"
    }

    if confidence not in allowed:
        return "LOW"

    return confidence

def verify_company(
    state: ResearchState
):

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

def research_company(state: ResearchState):

    print(
        f"\nResearching "
        f"{state['company_name']}..."
    )

    company = state["company_name"]

    queries = [
        f"{company} company overview",
        f"{company} products services technologies",
        f"{company} business areas industries",
        f"{company} recent news developments",
        f"{company} technology initiatives"
    ]

    all_results = []

    for query in queries:

        results = parallel_search(
            query
        )
        
        filtered_results = (
            filter_relevant_results(
                results,
                state["company_identity"]
            )
        )
        
        all_results.extend(
            filtered_results
        )
        
    return {
        "search_results": all_results
    }


# ============================================================
# ANALYZE COMPANY RESEARCH
# ============================================================

def analyze_research(state: ResearchState):

    print("\nAnalyzing research...")

    confidence = assess_evidence_confidence(
        results=state["search_results"],
        company_identity=state["company_identity"],
        context="General company research"
    )

    print(
        f"\nCompany evidence confidence: "
        f"{confidence}"
    )
    if confidence == "INSUFFICIENT":

        return {
            "company_evidence_confidence":
                confidence,
    
            "analysis":
                (
                    "Insufficient verified evidence is available "
                    "to produce a reliable company research summary. "
                    "The available public sources do not provide enough "
                    "company-specific information."
                )
        }
    
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

If evidence is insufficient, explicitly write:

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
"""

    analysis_text = invoke_gemini(prompt)

    # Defensive conversion
    analysis_text = extract_text(analysis_text)

    return {
    "analysis":
        analysis_text,

    "company_evidence_confidence":
        confidence
    }


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_report(state: ResearchState):

    print("\nGenerating structured report...")

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

    report_text = invoke_gemini(prompt)

    report_text = extract_text(
        report_text
    )

    return {
        "report": report_text
    }
# ============================================================
# GENERATE DOMAINS
# ============================================================

def generate_domains(state: ResearchState):

    print("\nIdentifying relevant job domains...")

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

    domains_text = invoke_gemini(prompt)

    # --------------------------------------------------------
    # IMPORTANT:
    # Force conversion again here so splitlines ALWAYS
    # receives a string.
    # --------------------------------------------------------

    domains_text = extract_text(domains_text)

    if not isinstance(domains_text, str):
        raise TypeError(
            "Domain response could not be converted to text."
        )

    domains = []

    for line in domains_text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Handle numbered Gemini output:
        # 1. Networking
        # 2. Cybersecurity
        if line[0].isdigit() and "." in line:

            domain = line.split(
                ".",
                1
            )[-1].strip()

            if domain:
                domains.append(domain)

    if not domains:

        raise ValueError(
            "Gemini did not return any valid job domains."
        )

    return {
        "available_domains": domains
    }


# ============================================================
# HUMAN DOMAIN SELECTION
# ============================================================

def select_domain(state: ResearchState):

    print("\nWaiting for domain selection...")

    selected_domain = interrupt({
        "message":
            "Please select a job domain to focus on.",

        "available_domains":
            state["available_domains"]
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

    company = state["company_name"]
    domain = state["selected_domain"]

    queries = [
        f"{company} {domain}",
        f"{company} {domain} technologies",
        f"{company} {domain} solutions",
        f"{company} {domain} initiatives",
        f"{company} {domain} careers skills"
    ]

    domain_results = []

    for query in queries:

        results = search_web(
            query
        )

        filtered_results = (
            filter_relevant_results(
                results,
                state["company_identity"]
            )
        )

        domain_results.extend(
            filtered_results
        )
    return {
        "domain_search_results":
            domain_results
    }


# ============================================================
# ANALYZE SELECTED DOMAIN
# ============================================================

def analyze_domain(state: ResearchState):

    confidence = assess_evidence_confidence(
        results=state["domain_search_results"],
        company_identity=state["company_identity"],
        context=(
            f"Selected domain: "
            f"{state['selected_domain']}"
        )
    )

    print(
        f"\nDomain evidence confidence: "
        f"{confidence}"
    )

    if confidence == "INSUFFICIENT":

        return {
            "domain_evidence_confidence":
                confidence,

            "domain_analysis":
                (
                    "Insufficient verified company-specific "
                    "evidence is available for this domain. "
                    "General preparation advice cannot be presented "
                    "as company-specific information."
                )
        }

    print(
        f"\nAnalyzing "
        f"{state['selected_domain']} domain..."
    )

    research_text = ""

    for index, result in enumerate(
        state["domain_search_results"],
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

Analyze this selected domain specifically in relation
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

Do not invent technologies, projects or interview
questions.
"""

    domain_text = invoke_gemini(prompt)

    domain_text = extract_text(domain_text)

    return {
    "domain_analysis":
        domain_text,

    "domain_evidence_confidence":
        confidence
    }
# ============================================================
# GENERATE PDF
# ============================================================

def generate_pdf(
    state: ResearchState
):

    print(
        "\nGenerating PDF report..."
    )


    pdf_path = create_placement_pdf(

        company_name=
            state["company_name"],

        report=
            state["report"],

        selected_domain=
            state["selected_domain"],

        domain_analysis=
            state["domain_analysis"]
    )


    print(
        f"\nPDF created: "
        f"{pdf_path}"
    )


    return {}
def route_after_company_analysis(
    state: ResearchState
):

    confidence = state[
        "company_evidence_confidence"
    ]

    if confidence == "INSUFFICIENT":
        return "stop"

    return "continue"
# ============================================================
# BUILD GRAPH
# ============================================================

builder = StateGraph(
    ResearchState
)

builder.add_node(
    "verify_company",
    verify_company
)

builder.add_node(
    "research_company",
    research_company
)

builder.add_node(
    "analyze_research",
    analyze_research
)

builder.add_node(
    "generate_report",
    generate_report
)

builder.add_node(
    "generate_domains",
    generate_domains
)

builder.add_node(
    "select_domain",
    select_domain
)

builder.add_node(
    "research_selected_domain",
    research_selected_domain
)

builder.add_node(
    "analyze_domain",
    analyze_domain
)

builder.add_node(
    "generate_pdf",
    generate_pdf
)


# ============================================================
# EDGES
# ============================================================

builder.add_edge(
    START,
    "verify_company"
)

builder.add_edge(
    "verify_company",
    "research_company"
)
builder.add_edge(
    "research_company",
    "analyze_research"
)

builder.add_conditional_edges(
    "analyze_research",
    route_after_company_analysis,
    {
        "continue":
            "generate_report",

        "stop":
            END
    }
)

builder.add_edge(
    "generate_report",
    "generate_domains"
)

builder.add_edge(
    "generate_domains",
    "select_domain"
)

builder.add_edge(
    "select_domain",
    "research_selected_domain"
)

builder.add_edge(
    "research_selected_domain",
    "analyze_domain"
)

builder.add_edge(
    "analyze_domain",
    "generate_pdf"
)

builder.add_edge(
    "generate_pdf",
    END
)


# ============================================================
# MEMORY
# ============================================================

memory = MemorySaver()

graph = builder.compile(
    checkpointer=memory
)
