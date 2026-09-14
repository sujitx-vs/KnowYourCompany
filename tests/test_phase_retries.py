from copy import deepcopy
from tests.test_api import create
from backend.worker import Worker


def fail(db, run_id, phase):
    db.mutate(run_id, lambda r: r.update(status="export_failed" if phase == "export" else "failed",
                                         phase=phase, lease_until=0))


def test_independent_phase_budgets(client, db, auth):
    run_id = create(client, auth)
    for phase in ("company", "domain", "export"):
        for remaining in (2, 1, 0):
            fail(db, run_id, phase)
            response = client.post(f"/runs/{run_id}/retry", headers=auth)
            assert response.status_code == 202
            assert response.json()["retries_remaining"] == remaining
        fail(db, run_id, phase)
        snapshot = client.get(f"/runs/{run_id}", headers=auth).json()
        assert snapshot["retry_allowed"] is False
        response = client.post(f"/runs/{run_id}/retry", headers=auth)
        assert response.status_code == 429
        assert response.headers["X-Failure-Category"] == "manual_retries_exhausted"
        assert "Retry-After" not in response.headers
        assert "Waiting does not reset" in response.json()["detail"]
    assert db.get(run_id)["retries"] == 9


def test_legacy_budget_not_migrated_or_reset(client, db, auth):
    run_id = create(client, auth)
    def legacy(r):
        r.pop("phase_retries")
        r.update(retries=2, status="failed", state={"completed_nodes": ["verify_company"], "private": "saved"})
    db.mutate(run_id, legacy)
    state = deepcopy(db.get(run_id)["state"])
    response = client.post(f"/runs/{run_id}/retry", headers=auth)
    assert response.json()["retry_scope"] == "legacy_shared"
    fail(db, run_id, "domain")
    before = db.get(run_id)
    assert client.post(f"/runs/{run_id}/retry", headers=auth).status_code == 429
    after = db.get(run_id)
    assert after == before and after["state"] == state
    assert "phase_retries" not in after and after["retries"] == 3


def test_automatic_budget_persists_and_manual_retry_is_separate(client, db, auth, monkeypatch):
    from tests.test_response_recovery import stub, data
    from agent.services.gemini import invoke_gemini
    from agent.schemas import Brief
    from types import SimpleNamespace
    run_id = create(client, auth)
    # Start at a checkpointed domain synthesis; deliberately fail both responses.
    db.mutate(run_id, lambda r: r.update(phase="domain", state={"completed_nodes": ["research_selected_domain"]}))
    invalid = data()
    invalid.pop("domains")
    calls = stub(monkeypatch, [(invalid, "STOP")] * 4)
    monkeypatch.setattr("backend.worker.build_graph", lambda _: SimpleNamespace(invoke=lambda state: invoke_gemini("fixture", Brief)))
    worker = Worker(db)
    worker.tick()
    assert len(calls) == 2
    assert db.get(run_id)["phase_retries"]["domain"] == 0
    db.mutate(run_id, lambda r: r.update(status="queued"))  # Restart without a manual retry.
    worker.tick()
    assert len(calls) == 2
    assert db.get(run_id)["failure_category"] == "automatic_attempts_exhausted"
    assert client.post(f"/runs/{run_id}/retry", headers=auth).status_code == 202
    worker.tick()
    assert len(calls) == 4
    assert db.get(run_id)["state"]["completed_nodes"] == ["research_selected_domain"]
