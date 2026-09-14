"""Clearly fictional evidence used only in offline tests and local UI verification."""
from agent.schemas import Identity, Relevance, Brief


def fake_search(query):
    return [{"title": "Northstar Systems - Products and careers", "url": "https://example.com/company",
             "content": "Northstar Systems is a fictional software business in Bengaluru. It develops cloud operations software. Its engineering team builds Python services and maintains reliability tooling.", "source": "tavily"},
            {"title": "Northstar Systems engineering guide", "url": "https://example.com/engineering",
             "content": "Northstar Systems uses Python for service development. Engineers work on automated tests and monitoring. This fictional fixture is for interface verification only.", "source": "exa"}]


def fake_model(prompt, schema=None):
    import json
    if schema is Identity:
        return Identity(name="Northstar Systems", location="Bengaluru, India", industry="Software and cloud operations",
                        website="https://example.com/company", confidence="HIGH", reason="Matched to supplied test evidence.")
    if schema is Relevance:
        return Relevance(relevant_indexes=[0, 1])
    domain = "selected domain" in prompt
    prefix = "D" if domain else "S"
    sections = [{"title": "How this career area connects" if domain else "What the company does", "claims": [
        {"text": "Northstar Systems develops software for cloud operations, with an engineering focus on reliable services.", "kind": "fact", "source_ids": [prefix + "1"]},
        {"text": "The supplied engineering guide describes Python service development and monitoring work.", "kind": "fact", "source_ids": [prefix + "2"]},
    ]}, {"title": "Preparation priorities" if domain else "Technology and engineering", "claims": [
        {"text": "Build a small Python service with automated tests, request logging and a health endpoint. Be ready to explain your design choices and how you would investigate a failed request." if domain else "The engineering guide describes automated tests and monitoring alongside Python service development.", "kind": "recommendation" if domain else "fact", "source_ids": [] if domain else [prefix + "2"]},
        {"text": "Current vacancies and interview formats are not established by these sources. Check the company's official hiring information before relying on specific requirements.", "kind": "limitation", "source_ids": []},
    ]}]
    return Brief(confidence="HIGH", summary="Two supplied example sources support this fictional demonstration brief. This is test data, not real company research.", sections=sections,
                 domains=[] if domain else [{"name": "Software Engineering", "reason": "The engineering evidence describes Python services and automated testing.", "source_ids": ["S2"]},
                                            {"name": "Cloud Operations", "reason": "The product evidence connects the company to cloud reliability tooling.", "source_ids": ["S1"]}])
