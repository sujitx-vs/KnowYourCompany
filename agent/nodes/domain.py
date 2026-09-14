import json
from agent.schemas import Brief, validate_citations, brief_markdown
from agent.services.gemini import invoke_gemini
from agent.services.search import search_queries
from agent.services.evidence import filter_relevant_results
from agent.services.evidence_budget import select_evidence

def select_domain(state):
    from langgraph.types import interrupt
    domain = interrupt({"available_domains": state["available_domains"]})
    if domain not in state["available_domains"]:
        raise ValueError("Select an offered domain")
    return {"selected_domain": domain}

def research_selected_domain(state):
    company, domain = state["identity"]["name"], state["selected_domain"]
    queries = [f"{company} {domain} {topic}" for topic in ("", "technologies", "solutions", "initiatives", "careers skills")]
    results = select_evidence(search_queries(queries), state["identity"].get("website", ""), "D")
    return {"domain_search_results": filter_relevant_results(results, state["company_identity"])}

def analyze_domain(state):
    sources = state.get("domain_search_results", [])
    if not sources:
        brief = Brief(confidence="INSUFFICIENT", summary="No verified company-specific evidence connects this domain to the company.", sections=[], domains=[])
    else:
        brief = invoke_gemini(
            "Build an interview preparation brief for the selected domain. Sections: Domain relevance; Technologies and tools; "
            "Preparation priorities; Concepts to study; Project ideas; Interview preparation. "
            "Company-specific facts require supplied source IDs. Study advice must have kind recommendation, never claim it "
            "is an actual company interview question or requirement. Missing evidence has kind limitation. "
            "Never infer company tools from general industry practice. Summary describes evidence coverage only. "
            "Include the required domains field as an empty array: domains: []. If company evidence is too weak use INSUFFICIENT.\n"
            + json.dumps({"identity": state["identity"], "domain": state["selected_domain"], "sources": sources}, ensure_ascii=False),
            Brief, validator=lambda brief: validate_citations(brief, sources, domain=True))
    data = validate_citations(brief, sources, domain=True)
    return {"domain_brief": data, "domain_analysis": brief_markdown(data), "domain_evidence_confidence": data["confidence"]}
