from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.memory import (
    MemorySaver
)

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
# CHECKPOINT MEMORY
# ============================================================

memory = MemorySaver()


# ============================================================
# COMPILE GRAPH
# ============================================================

graph = builder.compile(
    checkpointer=memory
)