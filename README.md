# KnowYourCompany

> **Live Demo**: [https://know-your-company-pi.vercel.app/](https://know-your-company-pi.vercel.app/)  
> **API Backend**: [https://knowyourcompany-api.onrender.com](https://knowyourcompany-api.onrender.com)  
> **API Docs**: [https://knowyourcompany-api.onrender.com/docs](https://knowyourcompany-api.onrender.com/docs)

KnowYourCompany is an AI-powered company research and campus-placement preparation agent built with **LangGraph, Gemini, Tavily, Exa, FastAPI, Next.js, Supabase, and ReportLab**.

It researches a company from multiple web sources, verifies company identity, filters unrelated evidence, analyzes evidence quality, generates a placement-focused company report, pauses for **Human-in-the-Loop (HITL)** domain selection, performs domain-specific research, and produces a private downloadable PDF report through a modern web interface.

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
- **Persistent LangGraph Checkpointing**: Powered by Supabase Postgres (`PostgresSaver`) to survive backend restarts, with graceful local `MemorySaver` fallback
- **Cloud PDF Storage**: Uploads reports to private Supabase Storage (`placement-reports`) with time-limited signed URLs
- **Unique Session & Report IDs**: Collision-free threads and PDF filenames
- **Environment-based Configuration**: Production CORS and dynamic `NEXT_PUBLIC_API_URL`
- FastAPI backend + Next.js (React 19 + Tailwind CSS) frontend
- PDF generation with ReportLab
- PDF preview, open-in-new-tab, and download support
- Lightweight in-run caching for stable state

## Architecture

```text
       ┌──────────────────────────────────────────────┐
       │             Frontend: Vercel                 │
       │    (Next.js 16 + React 19 + Tailwind CSS)     │
       └──────────────────────┬───────────────────────┘
                              │
                              │ NEXT_PUBLIC_API_URL
                              ▼
       ┌──────────────────────────────────────────────┐
       │      Backend: Render / Railway Web Service   │
       │            (FastAPI + Uvicorn)               │
       └──────┬───────────────┬────────────────┬──────┘
              │               │                │
              ▼               ▼                ▼
   ┌────────────────────┐  ┌─────────────┐  ┌─────────────────────────┐
   │ LangGraph Workflow │  │ Search APIs │  │    Supabase Cloud       │
   │  - Research nodes  │  │ - Tavily    │  │ - Storage (PDF bucket)  │
   │  - HITL interrupt  │  │ - Exa       │  │ - Postgres Checkpointer │
   │  - Gemini LLM      │  └─────────────┘  │   (Session persistence) │
   └────────────────────┘                   └─────────────────────────┘
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
        generate_pdf (Supabase upload & signed URL)
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

## Project Structure

```text
KnowYourCompany/
│
├── agent/
│   ├── graph.py                 # Graph definition with Postgres checkpointer & fallback
│   ├── state.py                 # TypedDict ResearchState (pdf_path, pdf_url)
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── company.py           # Verification, research, analysis, report, domains
│   │   ├── domain.py            # HITL interrupt, domain research, analysis
│   │   └── report.py            # Temporary PDF creation & Supabase upload
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
│   └── main.py                  # CLI runner
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI server with dynamic CORS & routes
│   └── supabase_client.py       # Backend-only Supabase storage & signed URL service
├── frontend/
│   ├── app/                     # Next.js 16 App Router UI
│   ├── .env.example             # Frontend environment template
│   ├── .env.local               # Local frontend configuration
│   └── package.json
├── tools/
│   ├── web_search.py            # Tavily client
│   ├── exa_search.py            # Exa client
│   └── pdf_generator.py         # ReportLab PDF generator (collision-safe filenames)
├── docs/
│   └── HALLUCINATION_REDUCTION_STRATEGY.md
├── .env.example                 # Root environment template
├── .gitignore
├── README.md
└── requirements.txt
```

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Backend and agent implementation |
| LangGraph | Workflow, state, routing, HITL, checkpointing |
| LangGraph Postgres | Persistent session checkpointer across restarts |
| Gemini | Identity verification, relevance judgment, analysis, report generation |
| Tavily | Web research |
| Exa | Additional web research |
| FastAPI | Backend REST API |
| Uvicorn | ASGI server |
| Next.js | Frontend framework |
| React | UI |
| Tailwind CSS | Styling |
| Supabase Storage | Private cloud PDF report storage |
| Supabase Postgres | Session and state checkpoint persistence |
| ReportLab | Placement PDF generation |

---

## Supabase Setup Guide

### 1. Create Storage Bucket
1. In your Supabase Dashboard, go to **Storage**.
2. Click **New bucket**.
3. Name: `placement-reports`
4. Make sure **Public bucket** is **OFF** (Private bucket).
5. Click **Save bucket**.

### 2. Obtain API Credentials
1. In **Project Settings** → **API**:
   - Copy **Project URL** (`SUPABASE_URL`)
   - Copy **anon public** (`SUPABASE_ANON_KEY`)
   - Copy **service_role secret** (`SUPABASE_SERVICE_ROLE_KEY`)
   *(The service-role key remains strictly on the backend and is never exposed to the frontend).*

### 3. Obtain Database Connection String
1. In **Project Settings** → **Database** → **Connection string**.
2. Select **URI** (Session or Transaction pooler).
3. Copy the URI and insert your project password:
   ```text
   postgresql://postgres.[project-ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require
   ```
4. Set this as `SUPABASE_DB_URL` in `.env`.
5. Note: Port 5432 (Session mode) is recommended with Supabase connection poolers. LangGraph automatically provisions all necessary tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) via `checkpointer.setup()` upon server start.

---

## Environment Variables

### Backend (`.env` in root)

```env
# LLM and Search APIs
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
EXA_API_KEY=your_exa_api_key

# Supabase Configuration (Backend only)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_STORAGE_BUCKET=placement-reports

# Supabase Postgres Checkpointer (Session persistence)
SUPABASE_DB_URL=postgresql://postgres.[project-ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require

# Frontend URL for CORS
FRONTEND_URL=http://localhost:3000
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## Local Installation & Development

### 1. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn backend.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Local endpoints:
- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`
- API Swagger Docs: `http://127.0.0.1:8000/docs`

---

## Cloud Deployment Guide

### Why Not Vercel for the Backend?
- **Execution Timeouts**: Vercel Serverless Functions have execution duration limits (10–15s on free tier, 60s max).
- **Agent Workload**: KnowYourCompany performs parallel searches across Tavily and Exa, followed by multiple Gemini reasoning passes and PDF compilation. Research tasks typically take 30 to 60 seconds.
- **Recommended Strategy**: Deploy the **Next.js frontend to Vercel** (for high-speed static/edge delivery) and the **FastAPI backend to Render, Railway, Fly.io, or Google Cloud Run** (for long-running ASGI execution).

### Step 1: Deploy Backend to Render (Recommended)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and click **New +** → **Web Service**.
3. Connect your repository.
4. Settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GOOGLE_API_KEY`
   - `TAVILY_API_KEY`
   - `EXA_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_STORAGE_BUCKET=placement-reports`
   - `SUPABASE_DB_URL`
   - `FRONTEND_URL` *(set to your Vercel frontend URL, e.g. `https://your-app.vercel.app`)*
6. Click **Deploy Web Service**. Render provides your live backend URL (e.g., `https://knowyourcompany-api.onrender.com`).

### Step 2: Deploy Frontend to Vercel
1. Sign in to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Select your repository.
3. In project configuration:
   - Set **Root Directory**: `frontend`
   - Framework Preset: `Next.js`
4. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL`: Your live backend URL from Render (e.g., `https://knowyourcompany-api.onrender.com`)
5. Click **Deploy**.

---

## API Endpoints

### `GET /`
Health check and Supabase status.

### `POST /research`
Starts company research. Returns unique `thread_id` and `available_domains` upon HITL pause.

### `POST /select-domain`
Resumes research with human-selected domain. Compiles report, uploads PDF to Supabase Storage, and returns `pdf_path` and `pdf_url` (signed URL).

### `GET /view-pdf?path=...`
Redirects to the Supabase signed URL (or streams local PDF during development).

### `GET /download-pdf?path=...`
Redirects to download signed URL (or serves local PDF with attachment header).

---

## Disclaimer

KnowYourCompany uses public web search results and AI-generated analysis. Information may be incomplete, outdated, or affected by external APIs. Always verify important placement, hiring, eligibility, compensation, and interview information using official company or campus-placement sources.

## Author

**Sujith V S**  
GitHub: [https://github.com/sujitx-vs](https://github.com/sujitx-vs)
