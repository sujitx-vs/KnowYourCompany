"""Small phase graphs with durable node checkpoints owned by the run queue.

No database connections or schema migrations occur at module import. Each completed
node is saved by the worker before the next node; crashed work is resumed from there.
"""
import time
from langgraph.graph import StateGraph, START, END
from agent.state import ResearchState
from agent.services.runtime import context, emit, remaining
from agent.nodes.company import verify_company, research_company, analyze_research
from agent.nodes.domain import research_selected_domain, analyze_domain

STAGES = {
    "verify_company": ("identity", "Finding the right company and its official website."),
    "research_company": ("company_search", "Checking products, business areas and recent developments."),
    "analyze_research": ("company_brief", "Connecting the evidence into your company brief."),
    "research_selected_domain": ("domain_search", "Checking how this career area connects to the company."),
    "analyze_domain": ("domain_brief", "Building your preparation priorities from the evidence."),
}

def durable_node(name, function):
    def run(state):
        if name in state.get("completed_nodes", []):
            return {}
        remaining()
        stage, message = STAGES[name]
        emit(stage=stage, message=message)
        start = time.monotonic()
        update = function(state)
        remaining()
        update["completed_nodes"] = [*state.get("completed_nodes", []), name]
        ctx = context.get()
        if ctx:
            ctx.checkpoint({**state, **update})
        emit("metric", metric="node_seconds", node=name, value=round(time.monotonic() - start, 3))
        return update
    return run

def build_graph(phase):
    builder = StateGraph(ResearchState)
    nodes = ([("verify_company", verify_company), ("research_company", research_company), ("analyze_research", analyze_research)]
             if phase == "company" else [("research_selected_domain", research_selected_domain), ("analyze_domain", analyze_domain)])
    for name, fn in nodes:
        builder.add_node(name, durable_node(name, fn))
    builder.add_edge(START, nodes[0][0])
    for index, (name, _) in enumerate(nodes):
        following = nodes[index + 1][0] if index + 1 < len(nodes) else END
        if name == "verify_company":
            builder.add_conditional_edges(name, lambda s: "continue" if s.get("identity_confirmed") or s["identity"]["confidence"] == "HIGH" else "pause",
                                          {"continue": following, "pause": END})
        else:
            builder.add_edge(name, following)
    return builder.compile()
