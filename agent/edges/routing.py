from agent.state import ResearchState


# ============================================================
# ROUTE AFTER COMPANY ANALYSIS
# ============================================================

def route_after_company_analysis(
    state: ResearchState
):

    confidence = state[
        "company_evidence_confidence"
    ]

    if confidence == "INSUFFICIENT":
        return "stop"

    return "continue"