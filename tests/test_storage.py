from types import SimpleNamespace
from unittest.mock import Mock
from backend import supabase_client as storage


def test_public_bucket_is_rejected(monkeypatch):
    client = SimpleNamespace(storage=Mock())
    client.storage.list_buckets.return_value = [SimpleNamespace(name="placement-reports", public=True)]
    monkeypatch.setattr(storage, "get_supabase_client", lambda: client)
    assert storage.ensure_bucket_exists("placement-reports") is False


def test_signed_links_have_short_lifetime_and_download_intent(monkeypatch):
    bucket = Mock()
    bucket.create_signed_url.return_value = {"signedURL": "https://storage.example/signed"}
    client = SimpleNamespace(storage=Mock())
    client.storage.from_.return_value = bucket
    monkeypatch.setattr(storage, "get_supabase_client", lambda: client)
    assert storage.get_report_signed_url("reports/abc.pdf", download=True) == "https://storage.example/signed"
    bucket.create_signed_url.assert_called_once_with(path="reports/abc.pdf", expires_in=300, options={"download": True})
