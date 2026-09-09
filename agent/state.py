from typing import TypedDict


class ResearchState(TypedDict):

    # Company
    company_name: str
    company_identity: str

    # Company research
    search_results: list
    company_evidence_confidence: str

    analysis: str
    report: str

    # Domain selection
    available_domains: list
    selected_domain: str

    # Domain research
    domain_search_results: list
    domain_evidence_confidence: str

    domain_analysis: str

    # Output
    pdf_path: str