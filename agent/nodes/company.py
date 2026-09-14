import json
from datetime import datetime, timezone
from urllib.parse import urlsplit
from agent.schemas import Identity, Brief, validate_citations, brief_markdown
from agent.services.gemini import invoke_gemini
from agent.services.search import parallel_search, search_queries, normalize_url
from agent.services.evidence import filter_relevant_results
from agent.services.evidence_budget import select_evidence

def verify_company(state):
    results = select_evidence(parallel_search(
        f'{state["company_name"]} {state.get("company_hint", "")} official company website location industry'
    ), prefix="I")
    if not results:
        identity = Identity(name=state["company_name"], location="Not verified", industry="Not verified",
                            website="", confidence="INSUFFICIENT", reason="No usable public evidence was returned.")
    else:
        identity = invoke_gemini(
            "Identify the requested company using only supplied evidence. If ambiguous or unverified, use LOW "
            "or INSUFFICIENT confidence. Website must be an official URL supported by evidence. Never guess.\n"
            + json.dumps({"company": state["company_name"], "hint": state.get("company_hint", ""), "sources": results}, ensure_ascii=False),
            Identity,
        )
        website = normalize_url(identity.website)
        hosts = {(urlsplit(r["url"]).hostname or "").removeprefix("www.") for r in results}
        if not website or (urlsplit(website).hostname or "").removeprefix("www.") not in hosts:
            identity.website = ""
            identity.confidence = "LOW"
            identity.reason = "The official website could not be confirmed from the retrieved sources."
        else:
            identity.website = website
    return {"identity": identity.model_dump(), "company_identity": identity.model_dump_json()}

def research_company(state):
    company = state["identity"]["name"]
    website = state["identity"].get("website", "")
    queries = [
        f"{company} {website} company overview",
        f"{company} products services technologies",
        f"{company} business areas industries",
        f"{company} recent news developments",
        f"{company} technology careers initiatives",
    ]
    evidence = select_evidence(search_queries(queries), website)
    return {"search_results": filter_relevant_results(evidence, state["company_identity"])}

def analyze_research(state):
    sources = state.get("search_results", [])
    if not sources:
        brief = Brief(confidence="INSUFFICIENT", summary="There is not enough verified evidence to create a company brief.", sections=[], domains=[])
    else:
        brief = invoke_gemini(
            "Create a concise company brief for an interview candidate. Sections: Company overview; Products and services; "
            "Technologies and business areas; Recent developments; Roles and hiring areas. Also select broad career domains "
            "with an evidence-based reason, not vacancies. Every company-specific factual claim and domain needs supplied "
            "source IDs. Never infer technology from industry. Label missing or conflicting evidence as limitations. "
            "Summary describes evidence coverage only. No preparation advice in this company brief. "
            "Use INSUFFICIENT if the evidence does not support a reliable brief.\n"
            + json.dumps({"identity": state["identity"], "sources": sources}, ensure_ascii=False), Brief, validator=lambda brief: validate_citations(brief, sources))
    data = validate_citations(brief, sources)
    if data["confidence"] != "INSUFFICIENT" and not data["domains"]:
        data["confidence"] = "INSUFFICIENT"
        data["summary"] = "The evidence does not support any preparation domains. Try a more specific company."
    return {"company_brief": data, "analysis": brief_markdown(data), "report": brief_markdown(data),
            "company_evidence_confidence": data["confidence"], "available_domains": [d["name"] for d in data["domains"]],
            "researched_at": datetime.now(timezone.utc).isoformat()}

# Compatibility exports; formatting and domain extraction no longer need extra AI calls.
def generate_report(state):
    return {"report": brief_markdown(state["company_brief"])}

def generate_domains(state):
    return {"available_domains": [d["name"] for d in state["company_brief"]["domains"]]}
