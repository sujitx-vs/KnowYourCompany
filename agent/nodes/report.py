import os

from agent.state import ResearchState

from tools.pdf_generator import (
    create_placement_pdf
)

from backend.supabase_client import (
    is_supabase_configured,
    upload_report_pdf,
    get_report_signed_url
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

    # 1. Generate the PDF temporarily
    local_pdf_path = create_placement_pdf(
        company_name=
            state["company_name"],

        report=
            state["report"],

        selected_domain=
            state["selected_domain"],

        domain_analysis=
            state["domain_analysis"]
    )

    # 2. If Supabase is configured, upload to private bucket and generate signed URL
    if is_supabase_configured():
        try:
            filename = os.path.basename(local_pdf_path)
            print(
                f"\nUploading {filename} to Supabase Storage..."
            )

            storage_path = upload_report_pdf(
                file_path=local_pdf_path,
                object_name=filename
            )

            signed_url = get_report_signed_url(
                storage_path=storage_path,
                expires_in=3600
            )

            # Clean up local temporary file after successful upload
            if os.path.exists(local_pdf_path):
                try:
                    os.remove(local_pdf_path)
                except Exception as cleanup_err:
                    print(f"Notice: Could not remove temporary PDF {local_pdf_path}: {cleanup_err}")

            print(
                f"\nPDF stored in Supabase: {storage_path}"
            )

            return {
                "pdf_path": storage_path,
                "pdf_url": signed_url
            }

        except Exception as err:
            print(
                f"\nError uploading to Supabase Storage: {err}. Falling back to local PDF path."
            )
            return {
                "pdf_path": local_pdf_path,
                "pdf_url": ""
            }

    # 3. Local-only fallback when Supabase is not configured
    print(
        f"\nPDF created locally: "
        f"{local_pdf_path}"
    )

    return {
        "pdf_path":
            local_pdf_path,
        "pdf_url":
            ""
    }