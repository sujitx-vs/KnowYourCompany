# KnowYourCompany

KnowYourCompany is an AI-powered company research and campus-placement preparation agent built with **LangGraph, Gemini, Tavily, Exa, FastAPI, Next.js, and ReportLab**.

It researches a company from multiple web sources, verifies company identity, filters unrelated evidence, analyzes evidence quality, generates a placement-focused company report, pauses for **Human-in-the-Loop (HITL)** domain selection, performs domain-specific research, and produces a downloadable PDF report through a web interface.

## Key Features

- Multi-source research using Tavily and Exa
- Parallel search-provider execution
- Company identity verification
- URL deduplication before LLM processing
- Batched relevance filtering to reduce Gemini calls
- Evidence-grounded analysis using source IDs
- Confidence levels: `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`
- Combined confidence + analysis calls to reduce LLM usage
- Conditional LangGraph routing when evidence is insufficient
- Human-in-the-Loop domain selection
- Domain-specific follow-up research
- Gemini model fallback
- LangGraph checkpointing with `MemorySaver`
- FastAPI backend
- Next.js + React + Tailwind frontend
- PDF generation with ReportLab
- PDF preview, open-in-new-tab, and download support
- Lightweight in-run caching for stable state

## Architecture

```text
Next.js + React + Tailwind
          ↓
        FastAPI
          ↓
       LangGraph
          ↓
   Tavily + Exa + Gemini
          ↓
      ReportLab PDF
```

## LangGraph Workflow

```text
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
  ├── INSUFFICIENT → END
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

## Anti-Hallucination Strategy

### 1. Company Identity Verification
The agent first verifies the most likely company identity using retrieved evidence instead of inferring from the company name.

### 2. Relevance Filtering
Retrieved results are checked against the verified identity. Results about similar names, unrelated organizations, or generic topics are rejected.

### 3. Evidence Grounding
Accepted company sources are assigned IDs such as `S1`, `S2`, and `S3`. Domain evidence uses IDs such as `D1`, `D2`, and `D3`. Company-specific claims are expected to remain grounded in these sources.

### 4. Evidence Confidence
Evidence is classified as:

| Confidence | Meaning |
|---|---|
| `HIGH` | Multiple relevant sources with strong agreement and authoritative evidence |
| `MEDIUM` | Useful evidence exists, but authoritative support is limited |
| `LOW` | Limited or mostly third-party evidence |
| `INSUFFICIENT` | Evidence is too weak to describe the company reliably |

If company-level evidence is `INSUFFICIENT`, the graph stops early.

## Performance Optimizations

- Search results from multiple queries are collected before relevance filtering.
- URLs are deduplicated before being sent to Gemini.
- Company relevance filtering uses one batched Gemini call instead of one call per query.
- Domain relevance filtering uses the same batched approach.
- Evidence confidence and analysis are combined into one Gemini call where appropriate.
- Deterministic tasks such as evidence formatting, confidence parsing, numbered-list parsing, empty-result checks, and cache checks are handled in Python.
- Stable state such as `company_identity`, `search_results`, and `available_domains` can be reused during the same LangGraph thread.

## Project Structure

```text
KnowYourCompany/
│
├── agent/
│   ├── graph.py
│   ├── state.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── domain.py
│   │   └── report.py
│   ├── edges/
│   │   ├── __init__.py
│   │   └── routing.py
│   └── services/
│       ├── __init__.py
│       ├── gemini.py
│       ├── search.py
│       ├── evidence.py
│       └── parsing.py
│
├── app/
│   └── main.py
├── backend/
│   ├── __init__.py
│   └── main.py
├── frontend/
│   ├── app/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   └── ...
├── tools/
│   ├── web_search.py
│   ├── exa_search.py
│   └── pdf_generator.py
├── docs/
│   └── HALLUCINATION_REDUCTION_STRATEGY.md
├── tests/
├── outputs/
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend and agent implementation |
| LangGraph | Workflow, state, routing, HITL, checkpointing |
| Gemini | Identity verification, relevance judgment, analysis, report generation |
| Tavily | Web research |
| Exa | Additional web research |
| FastAPI | Backend API |
| Uvicorn | ASGI server |
| Next.js | Frontend framework |
| React | UI |
| Tailwind CSS | Styling |
| ReportLab | PDF generation |
| python-dotenv | Environment variable loading |

## Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
EXA_API_KEY=your_exa_api_key
```

Do not commit real API keys.

## Installation

### Clone

```bash
git clone https://github.com/sujitx-vs/KnowYourCompany.git
cd KnowYourCompany
```

### Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install backend dependencies

```bash
pip install -r requirements.txt
```

### Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Application

Backend:

```bash
uvicorn backend.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Local URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
API Docs: http://127.0.0.1:8000/docs
```

## API Endpoints

### `GET /`
Health check.

### `POST /research`
Starts company research.

Example:

```json
{
  "company_name": "TCS"
}
```

### `POST /select-domain`
Resumes the paused LangGraph thread after domain selection.

### `GET /view-pdf`
Serves a generated PDF for browser preview.

### `GET /download-pdf`
Serves a generated PDF as a download.

## Report Structure

### Part A — Company Research
1. Company Overview
2. Products & Services
3. Technologies & Business Domains
4. Recent Developments
5. Roles & Hiring Areas

### Part B — Selected Domain
1. Domain Relevance to the Company
2. Relevant Technologies & Tools
3. Skills to Prepare
4. Important Concepts to Study
5. Relevant Project Areas
6. Likely Technical Interview Topics
7. Company-Specific Preparation Advice

## PDF Output

Generated reports are stored under:

```text
outputs/
```

The web interface supports:

- inline PDF preview
- open in a new browser tab
- direct download

## LangGraph State

```python
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
    pdf_path: str
```

## Gemini Model Fallback

```python
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash"
]
```

## Current Limitations

- External API availability and quotas affect execution.
- `MemorySaver` is in-process and not persistent across backend restarts.
- Public information for small/private companies may be sparse.
- Evidence confidence is LLM-assisted rather than mathematically calibrated.
- Search snippets may omit information available on the source page.
- Local PDF storage is suitable for development but not ideal for production.
- Frontend API URLs and backend CORS settings currently target local development and should become environment-based for deployment.

## Deployment Status

The application is complete for local development.

Before production deployment, the main areas to address are:

- hosted FastAPI backend
- persistent LangGraph checkpoints
- persistent PDF/object storage
- environment-based frontend API URL
- production CORS settings

## Disclaimer

KnowYourCompany uses public web search results and AI-generated analysis. Information may be incomplete, outdated, or affected by external APIs. Always verify important placement, hiring, eligibility, compensation, and interview information using official company or campus-placement sources.

## Author

**Sujith V S**

GitHub: https://github.com/sujitx-vs
