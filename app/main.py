from langgraph.types import Command

from agent.graph import graph


# ============================================================
# COMPANY INPUT
# ============================================================

company_name = input(
    "\nEnter company name: "
).strip()


if not company_name:

    raise ValueError(
        "Company name cannot be empty."
    )


# ============================================================
# INITIAL STATE
# ============================================================

initial_state = {
    "company_name": company_name,
    "company_identity": "",

    "search_results": [],
    "company_evidence_confidence": "",

    "analysis": "",
    "report": "",

    "available_domains": [],
    "selected_domain": "",

    "domain_search_results": [],
    "domain_evidence_confidence": "",

    "domain_analysis": ""
}


# ============================================================
# CONFIG
# ============================================================

thread_id = (
    "company-research-"
    + company_name
    .lower()
    .replace(" ", "-")
)


config = {

    "configurable": {

        "thread_id":
            thread_id
    }
}


# ============================================================
# RUN GRAPH
# ============================================================

result = graph.invoke(
    initial_state,
    config=config
)


# ============================================================
# HUMAN-IN-THE-LOOP
# ============================================================

if "__interrupt__" in result:

    interrupt_data = result[
        "__interrupt__"
    ][0]

    print(
        "\n=============================="
    )

    print(
        "DOMAIN SELECTION"
    )

    print(
        "=============================="
    )

    domains = interrupt_data.value[
        "available_domains"
    ]


    for i, domain in enumerate(
        domains,
        start=1
    ):

        print(
            f"{i}. {domain}"
        )


    choice = int(
        input(
            "\nEnter the domain number: "
        )
    )


    if choice < 1 or choice > len(domains):

        raise ValueError(
            "Invalid domain selection."
        )


    selected_domain = domains[
        choice - 1
    ]


    print(
        f"\nSelected domain: "
        f"{selected_domain}"
    )


    result = graph.invoke(

        Command(
            resume=selected_domain
        ),

        config=config
    )


print(
    "\nGraph completed."
)