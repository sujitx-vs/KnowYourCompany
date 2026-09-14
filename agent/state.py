from typing import TypedDict

class ResearchState(TypedDict, total=False):
    company_name: str
    company_hint: str
    company_identity: str
    identity: dict
    identity_confirmed: bool
    search_results: list
    company_evidence_confidence: str
    analysis: str
    report: str
    company_brief: dict
    available_domains: list
    selected_domain: str
    domain_search_results: list
    domain_evidence_confidence: str
    domain_analysis: str
    domain_brief: dict
    pdf_path: str
    pdf_url: str
    completed_nodes: list
    researched_at: str
    cached_at: str
