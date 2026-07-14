from research_agent.state import ResearchState, Source

from api.main import create_app
from api.schemas import ResearchRequest


def _parse_sse(body: str) -> list[tuple[str, str]]:
    """Split a raw SSE stream body into (event, data) pairs."""
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = next(l.removeprefix("event: ") for l in lines if l.startswith("event: "))
        data = next(l.removeprefix("data: ") for l in lines if l.startswith("data: "))
        events.append((event, data))
    return events


def _fake_run_success(topic, llm, tools, config, on_iteration=None, on_query=None):
    if on_query:
        on_query("initial query")
    state = ResearchState(topic=topic, running_summary="## Summary\nhello\n")
    state.add_sources([Source(title="A", url="http://a.com", content="c")])
    state.loop_count = 1
    llm.total_cost = 0.01
    llm.n_calls = 2
    if on_iteration:
        on_iteration(0, state)
    return state


def test_research_endpoint_streams_searching_iteration_and_done_events(monkeypatch):
    monkeypatch.setattr("api.stream.run", _fake_run_success)

    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/research",
        json={
            "topic": "What is MCP?",
            "model": "test/model",
            "search_backend": "tavily",
            "tavily_api_key": "tvly-secret",
            "llm_api_key": "sk-secret",
        },
    )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    event_names = [e for e, _ in events]
    assert event_names == ["searching", "iteration", "done"]

    import json

    searching_data = json.loads(events[0][1])
    assert searching_data == {"query": "initial query"}

    done_data = json.loads(events[2][1])
    assert done_data["report_markdown"] == "## Summary\nhello\n"
    assert done_data["sources"] == [{"title": "A", "url": "http://a.com"}]
    assert done_data["llm_cost"] == 0.01

    assert "sk-secret" not in response.text
    assert "tvly-secret" not in response.text


def test_research_endpoint_sends_redacted_error_event_on_failure(monkeypatch):
    def _fake_run_raises(topic, llm, tools, config, on_iteration=None, on_query=None):
        raise RuntimeError("boom with key sk-secret embedded")

    monkeypatch.setattr("api.stream.run", _fake_run_raises)

    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/research",
        json={
            "topic": "What is MCP?",
            "model": "test/model",
            "search_backend": "duckduckgo",
            "llm_api_key": "sk-secret",
        },
    )

    events = _parse_sse(response.text)
    assert events[0][0] == "error"
    assert "sk-secret" not in events[0][1]
    assert "[REDACTED]" in events[0][1]


def test_research_endpoint_rejects_oversized_loops():
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/research",
        json={
            "topic": "What is MCP?",
            "model": "test/model",
            "search_backend": "duckduckgo",
            "llm_api_key": "sk-secret",
            "loops": 999,
        },
    )

    assert response.status_code == 422


def test_research_endpoint_requires_tavily_key_when_tavily_selected():
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.post(
        "/api/research",
        json={
            "topic": "What is MCP?",
            "model": "test/model",
            "search_backend": "tavily",
            "llm_api_key": "sk-secret",
        },
    )

    assert response.status_code == 422


def test_research_request_repr_never_contains_raw_keys():
    req = ResearchRequest(
        topic="What is MCP?",
        model="test/model",
        search_backend="tavily",
        llm_api_key="sk-super-secret",
        tavily_api_key="tvly-super-secret",
    )

    assert "sk-super-secret" not in repr(req)
    assert "tvly-super-secret" not in repr(req)
    assert "sk-super-secret" not in str(req)
