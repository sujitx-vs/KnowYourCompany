import time
from pathlib import Path
from backend.worker import Worker


def create(client, auth):
    response = client.post("/runs", headers=auth, json={"company_name": "Northstar Systems"})
    assert response.status_code == 202, response.text
    return response.json()["id"]


def test_auth_and_validation(client, auth):
    assert client.get("/runs").status_code == 401
    assert client.post("/runs", headers=auth, json={"company_name": "  "}).status_code == 422
    assert client.post("/runs", headers=auth, json={"company_name": "x" * 181}).status_code == 422
    assert client.get("/ready").json()["status"] == "ready"


def test_idempotency_and_ownership(client, auth):
    first = create(client, auth)
    assert create(client, auth) == first
    assert client.post("/runs", headers=auth, json={"company_name": "Different"}).status_code == 409
    other = {"Authorization": "Bearer " + "b" * 43}
    for path in [f"/runs/{first}", f"/runs/{first}/events", f"/reports/{first}/download"]:
        assert client.get(path, headers=other).status_code == 404
    assert client.post(f"/runs/{first}/cancel", headers=other).status_code == 404
    assert client.get("/runs", headers=other).json() == []


def test_retired_paths_and_cors(client):
    assert client.get("/view-pdf?path=.env").status_code == 410
    assert client.get("/download-pdf?path=https://evil.example").status_code == 410
    response = client.options("/runs", headers={"Origin": "https://unrelated.vercel.app", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in response.headers


def test_full_workflow(client, db, auth, providers, monkeypatch, tmp_path):
    monkeypatch.setenv("REPORT_DIR", str(tmp_path))
    monkeypatch.setattr("backend.supabase_client.is_supabase_configured", lambda: False)
    run_id = create(client, auth)
    worker = Worker(db)
    assert worker.tick()
    run = client.get(f"/runs/{run_id}", headers=auth).json()
    assert run["status"] == "awaiting_domain_selection"
    assert run["company_brief"]["sections"] and run["sources"]
    assert "owner" not in run and "state" not in run and "pdf_path" not in run
    assert client.post(f"/runs/{run_id}/domain", headers=auth, json={"selected_domain": "Invented"}).status_code == 422
    assert client.post(f"/runs/{run_id}/domain", headers=auth, json={"selected_domain": "Software Engineering"}).status_code == 202
    assert client.post(f"/runs/{run_id}/domain", headers=auth, json={"selected_domain": "Cloud Operations"}).status_code == 409
    assert worker.tick()
    partial = client.get(f"/runs/{run_id}", headers=auth).json()
    assert partial["domain_brief"] and partial["export_status"] == "queued"
    assert worker.tick()
    assert client.get(f"/runs/{run_id}", headers=auth).json()["status"] == "completed"
    pdf = client.get(f"/reports/{run_id}/download", headers=auth)
    assert pdf.content.startswith(b"%PDF") and "attachment" in pdf.headers["content-disposition"]
    assert client.post(f"/runs/{run_id}/feedback", headers=auth, json={"rating": 5, "comment": "Useful"}).status_code == 200
    assert client.get("/usage", headers=auth).json()["completed"] == 1


def test_pdf_traversal_guard(client, db, auth, tmp_path):
    run_id = create(client, auth)
    secret = tmp_path / "outside.txt"
    secret.write_text("private")
    db.mutate(run_id, lambda r: r.update(export_status="ready", state={"pdf_path": str(secret)}))
    assert client.get(f"/reports/{run_id}/view", headers=auth).status_code == 404


def test_cancel_before_claim(client, db, auth):
    run_id = create(client, auth)
    assert client.post(f"/runs/{run_id}/cancel", headers=auth).json()["status"] == "cancelled"
    assert not Worker(db).tick()


def test_allowance(client, db, auth, monkeypatch):
    monkeypatch.setenv("DAILY_RUN_LIMIT", "1")
    run_id = create(client, auth)
    client.post(f"/runs/{run_id}/cancel", headers=auth)
    response = client.post("/runs", headers={**auth, "Idempotency-Key": "another-key"}, json={"company_name": "Another"})
    assert response.status_code == 429


def test_insufficient_not_success(client, db, auth, providers, monkeypatch):
    monkeypatch.setattr("agent.nodes.company.parallel_search", lambda _: [])
    run_id = create(client, auth)
    Worker(db).tick()
    assert client.get(f"/runs/{run_id}", headers=auth).json()["status"] == "insufficient_evidence"


def test_confirmation_gate(client, db, auth, providers, monkeypatch):
    from tests.fixtures.research import fake_model
    from agent.schemas import Identity
    def uncertain(prompt, schema, **kwargs):
        result = fake_model(prompt, schema)
        if schema is Identity:
            result.confidence = "MEDIUM"
        return result
    monkeypatch.setattr("agent.nodes.company.invoke_gemini", uncertain)
    run_id = create(client, auth)
    Worker(db).tick()
    assert client.get(f"/runs/{run_id}", headers=auth).json()["status"] == "needs_company_confirmation"
    assert client.post(f"/runs/{run_id}/confirm", headers=auth).status_code == 200
    Worker(db).tick()
    assert db.get(run_id)["status"] == "awaiting_domain_selection"


def test_event_replay(client, db, auth):
    run_id = create(client, auth)
    client.post(f"/runs/{run_id}/cancel", headers=auth)
    response = client.get(f"/runs/{run_id}/events?after=1", headers=auth)
    assert "id: 1\n" not in response.text
    assert "id: 2\n" in response.text and "event: snapshot" in response.text


def test_export_retry_keeps_research(client, db, auth, providers, monkeypatch):
    run_id = create(client, auth)
    worker = Worker(db)
    worker.tick()
    client.post(f"/runs/{run_id}/domain", headers=auth, json={"selected_domain": "Software Engineering"})
    worker.tick()
    def fail(_):
        raise RuntimeError("private-provider-secret")
    monkeypatch.setattr("agent.nodes.report.generate_pdf", fail)
    worker.tick()
    failed = client.get(f"/runs/{run_id}", headers=auth).json()
    assert failed["status"] == "export_failed" and failed["domain_brief"]
    assert "private-provider-secret" not in str(failed)
    assert client.post(f"/runs/{run_id}/retry", headers=auth).status_code == 202
    assert db.get(run_id)["phase"] == "export"


def test_operator_boundary_and_unknown_costs(client, db, auth, monkeypatch):
    assert client.get("/admin/metrics", headers=auth).status_code == 401
    monkeypatch.setenv("ADMIN_API_KEY", "operator-secret-" + "x" * 32)
    run_id = create(client, auth)
    db.mutate(run_id, lambda r: r["metrics"].append({"metric": "llm_usage", "model": "test-model", "input_tokens": 100, "output_tokens": 20}))
    data = client.get("/admin/metrics", headers={"X-Admin-Key": "operator-secret-" + "x" * 32}).json()
    assert data["runs"] == 1 and data["estimated_provider_cost_usd"] is None
    assert "owner" not in data and "state" not in data
    monkeypatch.setenv("MODEL_PRICES_JSON", '{"test-model":{"input":1,"output":2}}')
    data = client.get("/admin/metrics", headers={"X-Admin-Key": "operator-secret-" + "x" * 32}).json()
    assert data["estimated_llm_cost_usd"] == 0.0001
