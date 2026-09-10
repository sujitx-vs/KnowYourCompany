import os
import re
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from agent.graph import graph
from backend.supabase_client import (
    is_supabase_configured,
    get_report_signed_url
)
from langgraph.types import Command

load_dotenv()

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="KnowYourCompany API",
    description=(
        "Backend API for the KnowYourCompany "
        "placement research agent."
    ),
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://know-your-company-pi.vercel.app",
]

frontend_env = os.getenv("FRONTEND_URL", "").strip()
if frontend_env:
    for origin in frontend_env.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class ResearchRequest(BaseModel):
    company_name: str


class DomainSelectionRequest(BaseModel):
    thread_id: str
    selected_domain: str


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def health_check():

    return {
        "status": "running",
        "message": "KnowYourCompany API is running.",
        "supabase_configured": is_supabase_configured()
    }


# ============================================================
# VIEW PDF IN BROWSER
# ============================================================

@app.get("/view-pdf")
def view_pdf(path: str):
    # 1. If path is already an external signed URL, redirect directly
    if path.startswith("http://") or path.startswith("https://"):
        return RedirectResponse(url=path)

    # 2. If Supabase is configured and path is a storage object path
    if is_supabase_configured() and not os.path.exists(path):
        try:
            signed_url = get_report_signed_url(path, expires_in=3600)
            return RedirectResponse(url=signed_url)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found in cloud storage: {e}"
            )

    # 3. Local file fallback
    if os.path.exists(path):
        return FileResponse(
            path=path,
            media_type="application/pdf"
        )

    raise HTTPException(
        status_code=404,
        detail="PDF report file could not be found."
    )


# ============================================================
# DOWNLOAD PDF
# ============================================================

@app.get("/download-pdf")
def download_pdf(path: str):
    # 1. If path is already an external signed URL, redirect directly
    if path.startswith("http://") or path.startswith("https://"):
        return RedirectResponse(url=path)

    # 2. If Supabase is configured and path is a storage object path
    if is_supabase_configured() and not os.path.exists(path):
        try:
            signed_url = get_report_signed_url(path, expires_in=3600)
            return RedirectResponse(url=signed_url)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found in cloud storage: {e}"
            )

    # 3. Local file fallback
    if os.path.exists(path):
        return FileResponse(
            path=path,
            media_type="application/pdf",
            filename="placement_report.pdf"
        )

    raise HTTPException(
        status_code=404,
        detail="PDF report file could not be found."
    )


# ============================================================
# START COMPANY RESEARCH
# ============================================================

@app.post("/research")
def start_research(
    request: ResearchRequest
):

    company_name = request.company_name.strip()

    if not company_name:

        return {
            "status": "error",
            "message": "Company name cannot be empty."
        }


    # --------------------------------------------------------
    # INITIAL LANGGRAPH STATE
    # --------------------------------------------------------

    initial_state = {
        "company_name": company_name,
        "company_identity": "",

        "search_results": [],
        "company_evidence_confidence": "",

        "analysis": "",
        "report": "",

        "available_domains": [],
        "selected_domain": "",

        "domain_search_results": [],
        "domain_evidence_confidence": "",

        "domain_analysis": "",

        "pdf_path": "",
        "pdf_url": ""
    }


    # --------------------------------------------------------
    # UNIQUE THREAD CONFIGURATION
    # --------------------------------------------------------

    safe_name = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        company_name.lower()
    ).strip("-")

    session_id = uuid.uuid4().hex[:8]

    thread_id = f"company-research-{safe_name}-{session_id}"


    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }


    # --------------------------------------------------------
    # RUN LANGGRAPH
    # --------------------------------------------------------

    result = graph.invoke(
        initial_state,
        config=config
    )


    # --------------------------------------------------------
    # CHECK FOR HUMAN-IN-THE-LOOP INTERRUPT
    # --------------------------------------------------------

    if "__interrupt__" in result:

        interrupt_data = result[
            "__interrupt__"
        ][0]

        domains = interrupt_data.value[
            "available_domains"
        ]

        return {
            "status": "awaiting_domain_selection",
            "thread_id": thread_id,
            "company_name": company_name,
            "available_domains": domains
        }


    # --------------------------------------------------------
    # GRAPH COMPLETED WITHOUT INTERRUPT
    # --------------------------------------------------------

    return {
        "status": "completed",
        "thread_id": thread_id,
        "company_name": company_name,
        "result": result
    }


# ============================================================
# RESUME AFTER DOMAIN SELECTION
# ============================================================

@app.post("/select-domain")
def select_domain(
    request: DomainSelectionRequest
):

    thread_id = request.thread_id.strip()
    selected_domain = request.selected_domain.strip()

    if not thread_id:

        return {
            "status": "error",
            "message": "Thread ID cannot be empty."
        }


    if not selected_domain:

        return {
            "status": "error",
            "message": "Selected domain cannot be empty."
        }


    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }


    result = graph.invoke(
        Command(
            resume=selected_domain
        ),
        config=config
    )


    pdf_path = result.get(
        "pdf_path",
        ""
    )

    pdf_url = result.get(
        "pdf_url",
        ""
    )

    # If Supabase is configured and pdf_url was not populated, generate signed URL
    if is_supabase_configured() and pdf_path and not pdf_url:
        try:
            pdf_url = get_report_signed_url(pdf_path, expires_in=3600)
        except Exception as e:
            print(f"[Supabase] Could not generate signed URL: {e}")


    return {
        "status": "completed",
        "thread_id": thread_id,
        "selected_domain": selected_domain,
        "pdf_path": pdf_path,
        "pdf_url": pdf_url,
        "result": result
    }