import pytest
from backend.config import validate_configuration


def test_invalid_numeric_settings_fail_early(monkeypatch):
    monkeypatch.setenv("SEARCH_QUERY_CONCURRENCY", "100")
    with pytest.raises(RuntimeError, match="SEARCH_QUERY_CONCURRENCY"):
        validate_configuration()


def test_invalid_price_settings_fail_early(monkeypatch):
    monkeypatch.setenv("MODEL_PRICES_JSON", '{"test":{"input":-1,"output":2}}')
    with pytest.raises(RuntimeError, match="MODEL_PRICES_JSON"):
        validate_configuration()


def test_production_requires_https_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for key in ("GOOGLE_API_KEY", "TAVILY_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.setenv(key, "configured-for-test")
    monkeypatch.setenv("FRONTEND_URL", "http://unsafe.example")
    with pytest.raises(RuntimeError, match="HTTPS"):
        validate_configuration()
