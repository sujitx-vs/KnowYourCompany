from typing import TypedDict

class ResearchState(TypedDict):
    company_name: str

    company_identity: str

    search_results: list
    analysis: str
    report: str

    available_domains: list
    selected_domain: str

    domain_search_results: list
    domain_analysis: str

    company_evidence_confidence: str
    domain_evidence_confidence: str