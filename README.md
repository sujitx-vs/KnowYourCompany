# KnowYourCompany

**KnowYourCompany** is an AI-powered company research and
campus-placement preparation agent built with **LangGraph**, **Gemini**,
**Tavily**, and **Exa**.

The project researches a company from multiple web sources, verifies
that retrieved information belongs to the correct company, evaluates
evidence quality, generates a structured placement-oriented company
report, pauses for Human-in-the-Loop career-domain selection, performs
domain-specific research, and exports the result as a PDF.

> **Current milestone:** CLI version

------------------------------------------------------------------------

## Overview

Students preparing for campus placements often collect information from
company websites, search engines, news articles, career pages, and other
public sources before an interview.

KnowYourCompany automates much of this research while addressing a major
problem in AI research systems: **unsupported or incorrectly attributed
company information**.

Instead of simply searching the web and asking an LLM to summarize
everything, the agent uses four validation layers:

1.  Verify the company identity.
2.  Filter search results that do not clearly belong to the verified
    company.
3.  Require company-specific claims to be grounded in retrieved
    evidence.
4.  Assess evidence confidence and stop the workflow when reliable
    information is insufficient.

The guiding principle is:

> **A smaller amount of verified information is better than a detailed
> report containing unsupported information.**

------------------------------------------------------------------------

## Key Features

-   Multi-source company research with **Tavily** and **Exa**
-   Parallel Tavily + Exa retrieval for company research
-   Company identity verification before deeper research
-   Filtering of irrelevant or similarly named entities
-   Evidence-grounded analysis using source IDs
-   Evidence confidence levels: `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`
-   Conditional LangGraph routing when evidence is insufficient
-   Structured company research report
-   Automatic identification of broad career domains
-   LangGraph **Human-in-the-Loop** domain selection
-   Domain-specific follow-up research
-   Separation of verified company facts from general student
    recommendations
-   Gemini model fallback handling
-   LangGraph checkpointing with `MemorySaver`
-   PDF generation with ReportLab
-   CLI application workflow

------------------------------------------------------------------------

## Agent Workflow

``` text
START
  ↓
verify_company
  ↓
research_company
  ↓
analyze_research
  ↓
Check Company Evidence Confidence
  │
  ├── INSUFFICIENT ───────────────→ END
  │
  └── HIGH / MEDIUM / LOW
              ↓
       generate_report
              ↓
       generate_domains
              ↓
        select_domain
              ↓
     HUMAN-IN-THE-LOOP
              ↓
 research_selected_domain
              ↓
       analyze_domain
              ↓
        generate_pdf
              ↓
             END
```

The conditional edge after `analyze_research` prevents later nodes from
generating reports or career domains when the available company evidence
is too weak.

------------------------------------------------------------------------

## Anti-Hallucination Strategy

### 1. Company Identity Verification

Before general research begins, the agent performs a dedicated search to
establish the most likely identity of the company.

It attempts to verify:

-   Company name
-   Location
-   Industry
-   Official website
-   Identity confidence

The verification prompt explicitly prevents the model from inferring an
industry merely from the company name.

``` text
User Company Name
       ↓
Identity Search
       ↓
Gemini Verification
       ↓
Verified Company Identity
```

### 2. Search Result Relevance Filtering

Search engines may return different companies with similar names,
unrelated organizations, generic topics with similar keywords, or pages
that cannot confidently be connected to the company.

The agent filters retrieved results against the verified company
identity before treating them as company evidence.

``` text
Tavily / Exa Results
        ↓
Verified Company Identity
        ↓
Relevance Filter
        ↓
Accepted Company Sources
```

A result is not accepted merely because its wording resembles the
company name.

### 3. Evidence-Grounded Analysis

Accepted company sources receive IDs such as:

``` text
S1
S2
S3
```

Company-specific factual claims are required to be supported by those
source IDs.

Example:

``` text
The company provides enterprise communication services. [S2]
```

Domain-specific evidence uses IDs such as `D1`, `D2`, and `D3`.

The analysis is instructed not to infer technologies from an industry,
products from a company name, AI/ML usage without evidence, engineering
practices without evidence, or company-specific projects/interview
topics without supporting information.

### 4. Evidence Confidence

Evidence is classified as:

  -----------------------------------------------------------------------
  Confidence                          Meaning
  ----------------------------------- -----------------------------------
  `HIGH`                              Multiple relevant sources with
                                      strong agreement and authoritative
                                      evidence

  `MEDIUM`                            Useful evidence exists, but
                                      authoritative evidence is limited

  `LOW`                               Limited or mostly third-party
                                      evidence is available

  `INSUFFICIENT`                      Evidence is too weak to reliably
                                      describe the company
  -----------------------------------------------------------------------

Source quality, relevance, and agreement matter more than the raw number
of results.

If company-level confidence is `INSUFFICIENT`, a conditional LangGraph
edge terminates the workflow instead of forcing later nodes to invent
missing information.

See `docs/HALLUCINATION_REDUCTION_STRATEGY.md` for the detailed design.

------------------------------------------------------------------------

## Report Structure

### Part A --- Company Research

``` text
1. Company Overview
2. Products & Services
3. Technologies & Business Domains
4. Recent Developments
5. Roles & Hiring Areas
```

Part A intentionally avoids candidate-specific skills, interview
questions, project recommendations, and preparation advice.

### Part B --- Selected Domain

After the user selects a career domain, domain analysis covers:

``` text
1. Domain Relevance to the Company
2. Relevant Technologies & Tools
3. Skills to Prepare
4. Important Concepts to Study
5. Relevant Project Areas
6. Likely Technical Interview Topics
7. Company-Specific Preparation Advice
```

Company-specific claims remain evidence-grounded. General study
recommendations may be given, but must not be presented as facts about
the company.

------------------------------------------------------------------------

## Human-in-the-Loop

After company research, the agent identifies broad career domains
supported by the evidence. The workflow pauses using LangGraph's
`interrupt()`.

The CLI displays the domains and waits for the student to choose one.
Execution resumes with:

``` python
Command(resume=selected_domain)
```

Checkpointing is provided by LangGraph's `MemorySaver`.

------------------------------------------------------------------------

## Technology Stack

  Technology      Purpose
  --------------- ---------------------------------------------------------
  Python          Main programming language
  LangGraph       Workflow, state, routing, HITL and checkpointing
  Gemini          Verification, filtering, analysis and report generation
  Tavily          Web research
  Exa             Additional web research source
  ReportLab       PDF generation
  python-dotenv   Environment variable management

------------------------------------------------------------------------

## Gemini Model Fallback

Current model priority:

``` python
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash"
]
```

The application attempts fallback models for supported API errors.

Gemini output is normalized because LangChain responses can arrive as
strings, message objects, structured content lists, or dictionary text
blocks.

------------------------------------------------------------------------

## Project Structure

``` text
KnowYourCompany/
│
├── agent/
│   ├── graph.py
│   └── state.py
│
├── app/
│   └── main.py
│
├── tools/
│   ├── web_search.py
│   ├── exa_search.py
│   └── pdf_generator.py
│
├── docs/
│   └── HALLUCINATION_REDUCTION_STRATEGY.md
│
├── outputs/
│   └── generated PDF reports
│
├── .env
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

`outputs/`, `.env`, virtual environments, IDE settings, and Python cache
files are excluded from Git.

------------------------------------------------------------------------

## Installation

### 1. Clone the repository

``` bash
git clone <your-repository-url>
cd KnowYourCompany
```

### 2. Create a virtual environment

Windows:

``` bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

Current direct dependencies:

``` text
langgraph
langchain-google-genai
python-dotenv
tavily-python
exa-py
reportlab
```

------------------------------------------------------------------------

## Environment Variables

Create a `.env` file in the project root:

``` env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
EXA_API_KEY=your_exa_api_key
```

Never commit the real `.env` file or API keys.

A safe `.env.example` can contain:

``` env
GOOGLE_API_KEY=
TAVILY_API_KEY=
EXA_API_KEY=
```

------------------------------------------------------------------------

## Running the CLI

From the project root:

``` bash
python -m app.main
```

Example:

``` text
Enter company name: Tech Mahindra

Verifying company identity...
Company identity verified.

Researching Tech Mahindra...
Analyzing research...
Company evidence confidence: HIGH

Generating structured report...
Identifying relevant job domains...

DOMAIN SELECTION
1. ...
2. ...
3. ...

Enter the domain number:
```

After domain selection, the graph resumes, performs domain-specific
research and analysis, and generates the PDF.

------------------------------------------------------------------------

## PDF Output

Generated reports are stored in:

``` text
outputs/
```

Example:

``` text
outputs/tech-mahindra-placement-report.pdf
```

The ReportLab generator supports a cover page, report sections,
selected-domain content, headings, bullets, numbered lists, basic
Markdown formatting, links, page numbers, and footer styling.

Generated reports are excluded from Git through `.gitignore`.

------------------------------------------------------------------------

## LangGraph State

``` python
class ResearchState(TypedDict):
    company_name: str
    company_identity: str

    search_results: list
    company_evidence_confidence: str

    analysis: str
    report: str

    available_domains: list
    selected_domain: str

    domain_search_results: list
    domain_evidence_confidence: str

    domain_analysis: str
```

------------------------------------------------------------------------

## Reliability Considerations

External APIs can fail even when application logic is correct.

Examples encountered during development include:

``` text
httpx.ConnectError: getaddrinfo failed
```

for DNS/network connectivity problems, and:

``` text
429 RESOURCE_EXHAUSTED
```

when Gemini API quota or rate limits are exceeded.

The application includes Gemini model fallback logic. More robust
retry/backoff and provider-level fault tolerance are possible future
improvements.

------------------------------------------------------------------------

## Performance Considerations

The workflow makes multiple external search and LLM calls. Optimization
directions include:

-   Batch-filtering retrieved results instead of filtering once per
    search query
-   Reducing overlapping search queries
-   Running Tavily and Exa in parallel where appropriate
-   Avoiding unnecessary repeated LLM analysis
-   Deduplicating retrieved URLs
-   Caching verified company research where appropriate
-   Adding safe retry/backoff for transient API failures

Reliability and evidence quality are prioritized over maximum speed.

------------------------------------------------------------------------

## Current Limitations

-   Public information for small/private companies may be sparse.
-   Search providers can still return irrelevant results.
-   Evidence confidence is LLM-assisted rather than mathematically
    calibrated.
-   External API quotas and network failures can interrupt execution.
-   The current interface is CLI-based.
-   `MemorySaver` is in-process checkpointing rather than persistent
    production storage.
-   Domain-specific evidence may be unavailable even when general
    company information is strong.
-   Search snippets may omit information available on the underlying
    page.
-   Generated preparation advice should still be reviewed before relying
    on it for an interview.

------------------------------------------------------------------------

## Planned Improvements

-   Additional network/API retry hardening
-   Search-result URL deduplication
-   Reduced search and Gemini API calls
-   Provider-specific failure isolation
-   Stronger structured-output validation
-   Persistent checkpoint storage
-   Better citation preservation in the final PDF
-   Improved insufficient-domain handling
-   Unified final report refinement
-   Web frontend

Planned frontend architecture:

``` text
Next.js + React + Tailwind CSS
              ↓
           FastAPI
              ↓
          LangGraph
              ↓
   Tavily / Exa / Gemini
```

The CLI version is being stabilized before frontend development.

------------------------------------------------------------------------

## Development Philosophy

KnowYourCompany is designed around **controlled research rather than
unrestricted generation**.

``` text
Retrieval
    ↓
Entity Verification
    ↓
Relevance Filtering
    ↓
Evidence Evaluation
    ↓
Grounded Reasoning
    ↓
Report Generation
```

This is especially important for small or ambiguous companies, where
search engines may return similarly named organizations or semantically
related but unrelated topics.

------------------------------------------------------------------------

## Project Status

**Current stage:** CLI prototype / development milestone

-   [x] LangGraph workflow
-   [x] Company identity verification
-   [x] Tavily research
-   [x] Exa research
-   [x] Parallel multi-provider company search
-   [x] Search-result relevance filtering
-   [x] Evidence-grounded company analysis
-   [x] Evidence confidence classification
-   [x] Conditional routing for insufficient company evidence
-   [x] Structured Part A report
-   [x] Career-domain generation
-   [x] Human-in-the-Loop domain selection
-   [x] Domain-specific research
-   [x] Evidence-grounded domain analysis
-   [x] Gemini model fallback
-   [x] PDF generation
-   [x] CLI application separation
-   [ ] Additional network/API retry hardening
-   [ ] Search and LLM-call optimization
-   [ ] Final unified report refinement
-   [ ] Web frontend

------------------------------------------------------------------------

## Disclaimer

KnowYourCompany uses information retrieved from public web sources and
AI-assisted analysis.

Company information, hiring processes, technologies, roles, and
interview expectations can change. Generated reports should be treated
as research and preparation aids rather than official statements from a
company.

Always verify critical placement information using official company
career pages, placement-cell communications, and official hiring
announcements.

------------------------------------------------------------------------

## License

No license has been specified yet. Add an appropriate license before
distribution or accepting external contributions.

------------------------------------------------------------------------

## Author

Built as an AI-agent project for learning and campus-placement research.
