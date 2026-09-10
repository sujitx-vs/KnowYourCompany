from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.graph import graph
from langgraph.types import Command


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
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
        "message": "KnowYourCompany API is running."
    }


# ============================================================
# VIEW PDF IN BROWSER
# ============================================================

@app.get("/view-pdf")
def view_pdf(path: str):

    return FileResponse(
        path=path,
        media_type="application/pdf"
    )


# ============================================================
# DOWNLOAD PDF
# ============================================================

@app.get("/download-pdf")
def download_pdf(path: str):

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename="placement_report.pdf"
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

        "pdf_path": ""
    }


    # --------------------------------------------------------
    # THREAD CONFIGURATION
    # --------------------------------------------------------

    thread_id = (
        "company-research-"
        + company_name
        .lower()
        .replace(" ", "-")
    )


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


    return {
        "status": "completed",
        "thread_id": thread_id,
        "selected_domain": selected_domain,
        "pdf_path": pdf_path,
        "result": result
    }