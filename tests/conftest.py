import pytest
from backend.store import Store
from backend.main import create_app
from fastapi.testclient import TestClient
from tests.fixtures.research import fake_model, fake_search


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("RESEARCH_CACHE_ENABLED", "true")
    monkeypatch.setenv("SEARCH_CACHE_ENABLED", "false")
    return Store(str(tmp_path / "runs.sqlite3"))


@pytest.fixture
def client(db):
    with TestClient(create_app(db, start_worker=False)) as client:
        yield client


@pytest.fixture
def auth():
    return {"Authorization": "Bearer " + "a" * 43, "Idempotency-Key": "test-request-001"}


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr("agent.services.search.search_web", fake_search)
    monkeypatch.setattr("agent.services.search.search_exa", fake_search)
    monkeypatch.setattr("agent.nodes.company.invoke_gemini", fake_model)
    monkeypatch.setattr("agent.nodes.domain.invoke_gemini", fake_model)
    monkeypatch.setattr("agent.services.evidence.invoke_gemini", fake_model)
