import os
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ============================================================
# SUPABASE CONFIGURATION (BACKEND ONLY)
# ============================================================
# NOTE: SUPABASE_SERVICE_ROLE_KEY has administrative privileges.
# It MUST NEVER be exposed to the frontend or browser.
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "placement-reports").strip()

_supabase_client: Optional[Client] = None


def is_supabase_configured() -> bool:
    """
    Check if Supabase credentials are configured in backend environment.
    """
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_client() -> Optional[Client]:
    """
    Get or initialize the backend Supabase client using the service role key.
    Returns None if Supabase credentials are not configured.
    """
    global _supabase_client

    if not is_supabase_configured():
        return None

    if _supabase_client is None:
        _supabase_client = create_client(
            SUPABASE_URL,
            SUPABASE_SERVICE_ROLE_KEY
        )

    return _supabase_client


def ensure_bucket_exists(bucket_name: str = SUPABASE_STORAGE_BUCKET) -> bool:
    """
    Ensure the target storage bucket exists. If not, attempts to create it as a private bucket.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        buckets = client.storage.list_buckets()
        existing = [b.name for b in buckets] if buckets else []
        for bucket in buckets or []:
            if bucket.name == bucket_name and getattr(bucket, "public", False):
                raise ValueError("The report bucket must be private")
        if bucket_name not in existing:
            # Create private bucket (public=False)
            client.storage.create_bucket(
                bucket_name,
                options={"public": False}
            )
        return True
    except Exception as e:
        print(f"[Supabase] Storage setup failed ({type(e).__name__}). Check that the report bucket is private and the backend has access.")
        return False


def upload_report_pdf(file_path: str, object_name: str) -> str:
    """
    Upload a local PDF file to Supabase Storage in the private placement-reports bucket.
    
    Args:
        file_path: Path to the local temporary PDF file.
        object_name: Filename to store inside the 'reports' folder in the bucket.
        
    Returns:
        The storage object path (e.g. 'reports/tcs-abc123-placement-report.pdf').
    """
    client = get_supabase_client()
    if not client:
        raise ValueError("Supabase is not configured on the backend.")

    storage_path = f"reports/{object_name}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Upload or overwrite to ensure idempotency
    client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": "application/pdf",
            "upsert": "true"
        }
    )

    return storage_path


def get_report_signed_url(storage_path: str, expires_in: int = 300, download: bool = False) -> str:
    """
    Generate a secure time-limited signed URL for viewing or downloading a private PDF report.
    
    Args:
        storage_path: Storage object path (e.g. 'reports/...').
        expires_in: Time-to-live in seconds (default 3600s = 1 hour).
        
    Returns:
        The complete signed URL string.
    """
    client = get_supabase_client()
    if not client:
        raise ValueError("Supabase is not configured on the backend.")

    res = client.storage.from_(SUPABASE_STORAGE_BUCKET).create_signed_url(
        path=storage_path,
        expires_in=expires_in,
        options={"download": True} if download else {}
    )

    if isinstance(res, dict):
        signed_url = res.get("signedURL") or res.get("signedUrl")
    else:
        signed_url = getattr(res, "signedURL", None) or getattr(res, "signedUrl", None)

    if not signed_url:
        raise ValueError(f"Failed to generate signed URL for path: {storage_path}")

    return signed_url


def download_report_pdf(storage_path: str) -> bytes:
    """
    Download the raw PDF bytes from Supabase storage.
    """
    client = get_supabase_client()
    if not client:
        raise ValueError("Supabase is not configured on the backend.")

    return client.storage.from_(SUPABASE_STORAGE_BUCKET).download(storage_path)
