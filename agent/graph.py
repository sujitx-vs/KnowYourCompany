import os
from dotenv import load_dotenv

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.memory import (
    MemorySaver
)

load_dotenv()

from agent.state import ResearchState

from agent.nodes.company import (
    verify_company,
    research_company,
    analyze_research,
    generate_report,
    generate_domains
)

from agent.nodes.domain import (
    select_domain,
    research_selected_domain,
    analyze_domain
)

from agent.nodes.report import (
    generate_pdf
)

from agent.edges.routing import (
    route_after_company_analysis
)


# ============================================================
# BUILD GRAPH
# ============================================================

builder = StateGraph(
    ResearchState
)


# ============================================================
# NODES
# ============================================================

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


# ============================================================
# CONDITIONAL ROUTING
# ============================================================

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


# ============================================================
# REMAINING EDGES
# ============================================================

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
# CHECKPOINTER INITIALIZATION
# ============================================================

def get_checkpointer():
    """
    Initialize persistent PostgresSaver checkpointer using Supabase DB URL if provided.
    Falls back gracefully to in-memory MemorySaver for local development.
    """
    db_url = (
        os.getenv("SUPABASE_DB_URL", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )

    if db_url:
        try:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver

            pool = ConnectionPool(
                conninfo=db_url,
                max_size=10,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": None
                }
            )
            checkpointer = PostgresSaver(pool)
            checkpointer.supports_pipeline = False
            checkpointer.setup()
            print("[LangGraph] Persistent PostgresSaver checkpointer initialized with Supabase Postgres.")
            return checkpointer
        except Exception as e:
            print(f"[LangGraph] Warning: Could not connect to Supabase Postgres ({e}). Falling back to MemorySaver.")
            return MemorySaver()

    print("[LangGraph] SUPABASE_DB_URL not configured. Using MemorySaver for local development.")
    return MemorySaver()


checkpointer = get_checkpointer()


# ============================================================
# COMPILE GRAPH
# ============================================================

graph = builder.compile(
    checkpointer=checkpointer
)