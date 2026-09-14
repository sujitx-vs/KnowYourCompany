import os
from pathlib import Path
from tools.pdf_generator import create_dossier_pdf
from agent.services.runtime import remaining

def generate_pdf(state):
    from backend.supabase_client import is_supabase_configured, upload_report_pdf
    path = create_dossier_pdf(state, report_id=state.get("export_id"))
    remaining()
    if is_supabase_configured():
        storage_path = upload_report_pdf(path, Path(path).name)
        Path(path).unlink(missing_ok=True)
        return {"pdf_path": storage_path, "pdf_url": ""}
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("Production report storage is not configured")
    return {"pdf_path": path, "pdf_url": ""}
