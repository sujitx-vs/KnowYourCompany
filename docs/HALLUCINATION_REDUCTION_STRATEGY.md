# KnowYourCompany --- Hallucination Reduction Strategy

## Overview

KnowYourCompany is a company-research and campus-placement preparation
agent built with LangGraph, Gemini, Tavily, and Exa. During testing, an
important reliability problem appeared: irrelevant web results could be
treated as company evidence and produce confident but incorrect report
content.

The project now uses four defensive layers:

1.  **Company identity verification**
2.  **Search-result relevance filtering**
3.  **Evidence-grounded analysis**
4.  **Evidence confidence and insufficient-evidence handling**

The objective is not to claim that hallucination can be completely
eliminated. The objective is to reduce unsupported claims and make the
system explicitly admit when reliable evidence is unavailable.

------------------------------------------------------------------------

## Why Prompting Alone Is Not Enough

A prompt such as `Do not hallucinate` cannot solve a retrieval problem.
If irrelevant evidence enters the model context, the model may summarize
it as if it belongs to the requested company.

The protected flow is:

``` text
User company
    |
    v
Verify company identity
    |
    v
Search Tavily + Exa
    |
    v
Filter irrelevant results
    |
    v
Assess evidence confidence
    |
    v
Evidence-grounded analysis
    |
    v
Report / safe insufficient-evidence response
```

------------------------------------------------------------------------

# Step 1 --- Company Identity Verification

## Problem

A company name may be ambiguous, similar to an unrelated term, shared by
multiple organizations, or poorly represented on the web. Broad searches
performed before establishing identity can therefore retrieve evidence
about the wrong entity.

## Solution

A `verify_company` LangGraph node runs before normal company research.

Its only responsibility is to establish the most likely identity of the
requested company from retrieved evidence.

It attempts to determine:

-   Company name
-   Location
-   Industry
-   Official website
-   Identity confidence

The prompt explicitly prohibits guessing and prohibits inferring an
industry from the wording of the company name.

## State

The verified identity is stored as:

``` python
company_identity: str
```

Later retrieval and filtering stages can therefore compare search
results against a known identity rather than only the raw company-name
query.

## Benefit

This protects against the first major failure mode:

``` text
Ambiguous name -> wrong entity -> wrong research -> wrong report
```

------------------------------------------------------------------------

# Step 2 --- Search-Result Relevance Filtering

## Problem

Even after identity verification, Tavily and Exa may retrieve unrelated
results because of keyword or semantic similarity.

## Solution

Filtering happens **after retrieval but before analysis**.

``` text
Query
  |
  v
parallel_search()
  |
  +-- Tavily
  +-- Exa
  |
  v
Normalize + merge
  |
  v
filter_relevant_results()
  |
  v
Accepted company-specific sources
```

Each candidate result is explicitly numbered:

``` text
RESULT 1
TITLE: ...
URL: ...
CONTENT: ...

RESULT 2
TITLE: ...
URL: ...
CONTENT: ...
```

The filtering model returns only the indexes of results that clearly
relate to the verified company.

## Rejection Rules

Results are rejected when they:

-   refer to another company,
-   refer to an organization with a similar name,
-   discuss an unrelated topic with similar keywords,
-   contain generic information without a clear company connection,
-   cannot reasonably be connected to the verified entity.

A result is not accepted merely because it contains similar words.

## Company Research

The company-research path follows:

``` python
results = parallel_search(query)

filtered_results = filter_relevant_results(
    results,
    state["company_identity"]
)

all_results.extend(filtered_results)
```

## Selected-Domain Research

The relevance filter is also applied to selected-domain search results.
This is essential because filtering only Part A research would still
allow unrelated evidence to contaminate Part B.

------------------------------------------------------------------------

# Step 3 --- Evidence-Grounded Analysis

## Problem

Even when all retrieved pages concern the correct company, a language
model can still infer details that the pages never actually state.

## Solution

Every accepted source receives an explicit source ID before analysis.

Company research uses:

``` text
S1, S2, S3, ...
```

Domain research uses:

``` text
D1, D2, D3, ...
```

Example:

``` text
SOURCE ID: S2
TITLE: ...
URL: ...
CONTENT: ...
```

The company-analysis prompt requires company-specific factual claims to
be supported by source IDs.

Example:

``` text
The company provides cloud communication services. [S2]
```

Multiple supporting sources can be represented as:

``` text
The company operates across cloud and cybersecurity services. [S1][S4]
```

## Grounding Rules

The model is instructed not to:

-   infer technologies because they are common in the industry,
-   infer products from the company name,
-   infer technologies from job-domain terminology,
-   combine unrelated facts into unsupported new claims,
-   use unsupported general knowledge as company fact,
-   invent missing details.

When the evidence cannot support a claim, the preferred response is:

``` text
Insufficient verified evidence.
```

## Company Facts vs Student Recommendations

This distinction is especially important in Part B.

``` text
COMPANY FACT
    |
    +-- must have company-specific evidence

STUDENT RECOMMENDATION
    |
    +-- may use general career knowledge,
        but must be clearly presented as a recommendation
```

For example, saying that a company uses PyTorch requires evidence.
Saying that learning Python can be useful preparation for an AI/ML role
can be presented as general preparation advice, but must not be
represented as proof that the company uses Python.

------------------------------------------------------------------------

# Step 4 --- Confidence and Insufficient-Evidence Handling

## Problem

For small or private companies, the correct retrieval pipeline may leave
only a few weak sources. A system should not manufacture detail merely
because the user requested a full report.

## Solution

The reusable `assess_evidence_confidence()` function evaluates the
filtered evidence before analysis.

It returns exactly one of:

-   `HIGH`
-   `MEDIUM`
-   `LOW`
-   `INSUFFICIENT`

## HIGH

Used when multiple relevant sources agree and authoritative sources such
as official company pages, reports, careers pages, or press releases are
available.

## MEDIUM

Used when relevant evidence exists and multiple sources support
important facts, but authoritative evidence is limited.

## LOW

Used when only a small amount of relevant information exists, evidence
is mostly third-party, or important details remain uncertain.

## INSUFFICIENT

Used when evidence is too weak to reliably describe the company or
selected domain.

## Important Principle

Confidence is based on **quality, relevance, authority, and agreement**,
not merely source count.

``` text
10 weak sources != HIGH confidence
```

## Company-Level Handling

Before company analysis:

``` python
confidence = assess_evidence_confidence(
    results=state["search_results"],
    company_identity=state["company_identity"],
    context="General company research"
)
```

The result is stored in:

``` python
company_evidence_confidence: str
```

If it is `INSUFFICIENT`, the system returns a safe explanation instead
of asking Gemini to construct a normal company analysis.

## Domain-Level Handling

The same process is applied before selected-domain analysis:

``` python
confidence = assess_evidence_confidence(
    results=state["domain_search_results"],
    company_identity=state["company_identity"],
    context=f"Selected domain: {state['selected_domain']}"
)
```

The result is stored in:

``` python
domain_evidence_confidence: str
```

If evidence is insufficient, the system explicitly states that verified
company-specific domain information is unavailable.

------------------------------------------------------------------------

# What Each Layer Protects Against

  Layer                   Main failure prevented
  ----------------------- ----------------------------------------------
  Identity verification   Researching the wrong company
  Relevance filtering     Unrelated pages entering the model context
  Evidence grounding      Unsupported company-specific claims
  Confidence handling     Fabricating detail when evidence is too weak

The layers complement one another. No single layer should be treated as
a complete hallucination solution.

------------------------------------------------------------------------

# Current Reliability Architecture

``` text
USER COMPANY
     |
     v
+----------------------+
| 1. VERIFY IDENTITY   |
+----------------------+
     |
     v
company_identity
     |
     v
+----------------------+
| SEARCH TAVILY + EXA  |
+----------------------+
     |
     v
+----------------------+
| 2. FILTER RESULTS    |
+----------------------+
     |
     v
accepted sources
     |
     v
+----------------------+
| 4. CHECK CONFIDENCE  |
+----------------------+
     |
     +----------+----------------+
     |                           |
INSUFFICIENT               HIGH/MEDIUM/LOW
     |                           |
     v                           v
safe fallback          +----------------------+
                       | 3. GROUNDED ANALYSIS |
                       +----------------------+
                                  |
                                  v
                         source-backed claims
```

Although evidence grounding is called Step 3 and confidence handling
Step 4 in the development strategy, the confidence function is
intentionally executed before the analysis call so that an insufficient
evidence set can be stopped early.

------------------------------------------------------------------------

# Important Limitation

This architecture **reduces hallucination risk but does not guarantee
factual correctness**.

Gemini is still involved in entity interpretation, relevance
classification, confidence assessment, and synthesis.

Possible future hardening includes:

-   deterministic official-domain validation,
-   source deduplication,
-   structured citation objects,
-   claim-level verification,
-   identity confirmation when confidence is low,
-   conditional graph routing when evidence is insufficient.

------------------------------------------------------------------------

# Remaining Graph Improvement

At present, an `INSUFFICIENT` company analysis can still flow into
`generate_report` and `generate_domains`.

A safer future graph is:

``` text
analyze_research
       |
       v
check company_evidence_confidence
       |
       +-- HIGH/MEDIUM/LOW --> generate_report --> generate_domains
       |
       +-- INSUFFICIENT -----> safe output --> END
```

This can be implemented with a LangGraph conditional edge.

------------------------------------------------------------------------

# Testing Strategy

## Test 1 --- Well-Known Company

Use a company with an established official website, many reliable
sources, clear products, and substantial public information.

Expected behavior:

-   strong identity verification,
-   many relevant results survive filtering,
-   evidence confidence is normally HIGH or MEDIUM,
-   analysis claims remain source-grounded.

## Test 2 --- Small or Ambiguous Company

Use a company with limited public information or an ambiguous name.

Expected behavior:

-   semantic false matches are removed,
-   unsupported technologies do not appear,
-   confidence may be LOW or INSUFFICIENT,
-   the system prefers an explicit limitation over invented detail.

The previously observed animal-behavior / mice-related false matches are
useful regression cases: unrelated content such as laboratory mice,
grimace prediction, animal behavior, or "MiceGPT" should not survive
unless credible evidence explicitly connects it to the verified company.

------------------------------------------------------------------------

# Final Design Principle

> A smaller amount of verified information is better than a detailed
> report containing unsupported information.

For a campus-placement research assistant, reporting that reliable
public evidence is unavailable is a valid result. It is preferable to
producing confident but incorrect preparation material.
