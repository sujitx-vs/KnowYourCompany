from agent.state import ResearchState

from tools.pdf_generator import (
    create_placement_pdf
)


# ============================================================
# GENERATE PDF
# ============================================================

def generate_pdf(
    state: ResearchState
):

    print(
        "\nGenerating PDF report..."
    )

    pdf_path = create_placement_pdf(
        company_name=
            state["company_name"],

        report=
            state["report"],

        selected_domain=
            state["selected_domain"],

        domain_analysis=
            state["domain_analysis"]
    )

    print(
        f"\nPDF created: "
        f"{pdf_path}"
    )

    return {
        "pdf_path":
            pdf_path
    }