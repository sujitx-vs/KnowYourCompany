from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from agent.schemas import Brief, validate_citations
from agent.services.gemini import invoke_gemini, ResponseFailure
from agent.services.runtime import context, RunContext
from tests.fixtures.research import fake_model


def data():
    return fake_model("company").model_dump()


SOURCES = [{"id": f"S{i}"} for i in range(1, 18)]


def stub(monkeypatch, outputs):
    import langchain_google_genai
    calls = []
    class Model:
        def __init__(self, **kwargs):
            pass
        def with_structured_output(self, *args, **kwargs):
            return self
        def invoke(self, messages):
            calls.append(messages)
            value = outputs.pop(0)
            if isinstance(value, Exception):
                raise value
            parsed, reason = value
            return {"parsed": parsed, "raw": SimpleNamespace(content=json.dumps(parsed),
                    response_metadata={"finish_reason": reason}, usage_metadata={"output_tokens": 100}),
                    "parsing_error": None}
    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", Model)
    return calls


def invoke():
    return invoke_gemini("original evidence", Brief, validator=lambda b: validate_citations(b, SOURCES))


def test_13_citations_and_deduplication(monkeypatch):
    value = data()
    value["sections"][0]["claims"][0]["source_ids"] = [f"S{i}" for i in range(1, 14)] * 2
    calls = stub(monkeypatch, [(value, "STOP")])
    assert len(invoke().sections[0].claims[0].source_ids) == 13
    assert len(calls) == 1


@pytest.mark.parametrize("problem", ["too_many", "unknown", "uncited", "kind", "source_ids", "domains"])
def test_validation_repair(monkeypatch, problem):
    invalid = data()
    claim = invalid["sections"][0]["claims"][0]
    if problem == "too_many": claim["source_ids"] = [f"S{i}" for i in range(1, 17)]
    elif problem == "unknown": claim["source_ids"] = ["S999"]
    elif problem == "uncited": claim["source_ids"] = []
    elif problem == "domains": invalid.pop("domains")
    else: claim.pop(problem)
    calls = stub(monkeypatch, [(invalid, "STOP"), (data(), "STOP")])
    assert invoke().confidence == "HIGH"
    assert len(calls) == 2
    assert "original evidence" in str(calls[1])
    assert "validation_errors" in str(calls[1])


def test_truncation_shares_recovery_allowance(monkeypatch):
    calls = stub(monkeypatch, [(None, "MAX_TOKENS"), (data(), "STOP")])
    invoke()
    assert "shorter COMPLETE" in str(calls[1])
    invalid = data()
    invalid.pop("domains")
    calls = stub(monkeypatch, [(invalid, "STOP"), (None, "MAX_TOKENS")])
    with pytest.raises(ResponseFailure, match="response_truncated"): invoke()
    assert len(calls) == 2


def test_failed_repair_preserves_checkpoint(monkeypatch):
    from agent.graph import durable_node
    from agent.nodes.company import analyze_research
    invalid = data()
    invalid["sections"][0]["claims"][0]["source_ids"] = ["S999"]
    stub(monkeypatch, [(invalid, "STOP"), (invalid, "STOP")])
    state = {"identity": {"name": "Fixture"}, "search_results": SOURCES,
             "completed_nodes": ["verify_company", "research_company"]}
    before, saved, events = deepcopy(state), [], []
    token = context.set(RunContext(checkpoint=saved.append, emit=lambda **e: events.append(e)))
    try:
        with pytest.raises(ResponseFailure): durable_node("analyze_research", analyze_research)(state)
    finally: context.reset(token)
    assert state == before and saved == []
    assert any(e.get("stage") == "brief_correction" for e in events)


def test_domain_empty_field_required(monkeypatch):
    from agent.nodes.domain import analyze_domain
    value = data()
    value["domains"] = []
    invalid = deepcopy(value)
    invalid.pop("domains")
    calls = stub(monkeypatch, [(invalid, "STOP"), (value, "STOP")])
    result = analyze_domain({"identity": {}, "selected_domain": "Engineering", "domain_search_results": SOURCES})
    assert result["domain_brief"]["domains"] == []
    assert "empty array" in str(calls[0])


def test_diagnostics_exclude_response(monkeypatch, caplog):
    invalid = data()
    invalid["sections"][0]["claims"][0]["text"] = "PRIVATE_SENTINEL"
    invalid.pop("domains")
    stub(monkeypatch, [(invalid, "STOP"), (data(), "STOP")])
    with caplog.at_level("INFO", logger="agent.services.gemini"):
        invoke()
    assert "PRIVATE_SENTINEL" not in caplog.text
    assert "domains" in caplog.text and "recovery=succeeded" in caplog.text


def test_provider_rate_limit_distinct(monkeypatch):
    calls = stub(monkeypatch, [RuntimeError("429 private"), RuntimeError("429 private")])
    with pytest.raises(ResponseFailure, match="provider_rate_limit"): invoke()
    assert len(calls) == 2


def test_over_limit_repair_is_bounded(monkeypatch):
    invalid = data()
    invalid["sections"][0]["claims"][0]["source_ids"] = [f"S{i}" for i in range(1, 17)]
    calls = stub(monkeypatch, [(invalid, "STOP"), (invalid, "STOP")])
    with pytest.raises(ResponseFailure, match="response_validation"): invoke()
    assert len(calls) == 2


def test_recovery_respects_deadline(monkeypatch):
    import time
    invalid = data()
    invalid.pop("domains")
    calls = stub(monkeypatch, [(invalid, "STOP"), (data(), "STOP")])
    ctx = RunContext()
    def emit(**event):
        if event.get("stage") == "brief_correction":
            ctx.deadline = time.monotonic() - 1
    ctx.emit = emit
    token = context.set(ctx)
    try:
        with pytest.raises(TimeoutError): invoke()
    finally: context.reset(token)
    assert len(calls) == 1


def test_unknown_finish_reason_does_not_assume_truncation(monkeypatch):
    calls = stub(monkeypatch, [(None, "unknown"), (data(), "STOP")])
    invoke()
    assert "shorter COMPLETE" not in str(calls[1])
