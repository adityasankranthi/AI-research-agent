import pytest

from research_agent.agent import generate_query, reflect, run, summarize
from research_agent.config import Config
from research_agent.prompts import SUMMARIZER_SYSTEM_PROMPT
from research_agent.state import ResearchState, Source


class _FakeLLM:
    def __init__(self, tool_responses=(), chat_responses=()):
        self._tool_responses = list(tool_responses)
        self._chat_responses = list(chat_responses)
        self.tool_calls_seen: list[str] = []

    def chat_with_tool(self, messages, tool):
        self.tool_calls_seen.append(tool["function"]["name"])
        return self._tool_responses.pop(0)

    def chat(self, messages):
        return self._chat_responses.pop(0)


class _FakeBackend:
    def __init__(self, sources_per_call):
        self._sources_per_call = list(sources_per_call)
        self.queries_seen: list[str] = []

    def search(self, query, max_results):
        self.queries_seen.append(query)
        return self._sources_per_call.pop(0)


def test_run_generates_query_once_then_reflects_between_loops_not_after_the_last():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {"knowledge_gap": "gap", "follow_up_query": "followup query"},
        ],
        chat_responses=["summary after loop 1", "summary after loop 2"],
    )
    source_a = Source(title="A", url="http://a.com", content="a")
    source_b = Source(title="B", url="http://b.com", content="b")
    backend = _FakeBackend(sources_per_call=[[source_a], [source_b]])
    config = Config(max_loops=2)

    state = run(topic="test topic", llm=llm, backend=backend, config=config)

    assert llm.tool_calls_seen == ["generate_search_query", "propose_followup_query"]
    assert backend.queries_seen == ["initial query", "followup query"]
    assert state.loop_count == 2
    assert state.sources == [source_a, source_b]
    assert "## Summary" in state.running_summary
    assert "summary after loop 2" in state.running_summary
    assert "### Sources:" in state.running_summary
    assert "http://a.com" in state.running_summary


def test_run_calls_on_iteration_with_query_used_for_that_loop_before_it_is_replaced():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {"knowledge_gap": "gap", "follow_up_query": "followup query"},
        ],
        chat_responses=["summary after loop 1", "summary after loop 2"],
    )
    backend = _FakeBackend(sources_per_call=[[], []])
    config = Config(max_loops=2)
    seen: list[tuple[int, str]] = []

    run(
        topic="t",
        llm=llm,
        backend=backend,
        config=config,
        on_iteration=lambda i, state: seen.append((i, state.search_query)),
    )

    # loop 0's callback must see the query that was just searched ("initial query"),
    # not the follow-up query reflect() computes afterward for loop 1.
    assert seen == [(0, "initial query"), (1, "followup query")]


def test_run_single_loop_never_calls_reflect():
    llm = _FakeLLM(
        tool_responses=[{"query": "only query", "rationale": "r"}],
        chat_responses=["only summary"],
    )
    backend = _FakeBackend(sources_per_call=[[]])
    config = Config(max_loops=1)

    run(topic="t", llm=llm, backend=backend, config=config)

    assert llm.tool_calls_seen == ["generate_search_query"]


def test_generate_query_falls_back_when_tool_returns_nothing():
    class _NoToolLLM:
        def chat_with_tool(self, messages, tool):
            return None

    query = generate_query(_NoToolLLM(), ResearchState(topic="fallback topic"))
    assert query == "Tell me more about fallback topic"


def test_reflect_falls_back_when_tool_returns_nothing():
    class _NoToolLLM:
        def chat_with_tool(self, messages, tool):
            return None

    query = reflect(_NoToolLLM(), ResearchState(topic="fallback topic"))
    assert query == "Tell me more about fallback topic"


def test_generate_query_retries_once_then_succeeds():
    llm = _FakeLLM(
        tool_responses=[
            {"rationale": "missing the query field"},
            {"query": "recovered query", "rationale": "r"},
        ]
    )
    query = generate_query(llm, ResearchState(topic="t"), max_retries=1)
    assert query == "recovered query"
    assert len(llm.tool_calls_seen) == 2


def test_generate_query_falls_back_after_exhausting_retries():
    llm = _FakeLLM(tool_responses=[{"rationale": "bad"}, {"rationale": "still bad"}])
    query = generate_query(llm, ResearchState(topic="fallback topic"), max_retries=1)
    assert query == "Tell me more about fallback topic"
    assert len(llm.tool_calls_seen) == 2  # initial attempt + one retry, no more


def test_summarize_retries_once_on_empty_content_then_succeeds():
    llm = _FakeLLM(chat_responses=["", "a real summary"])
    source = Source(title="A", url="http://a.com", content="a")
    summary = summarize(llm, ResearchState(topic="t"), [source], max_retries=1)
    assert summary == "a real summary"


def test_summarize_raises_after_exhausting_retries_on_persistent_empty_content():
    llm = _FakeLLM(chat_responses=["", ""])
    source = Source(title="A", url="http://a.com", content="a")
    with pytest.raises(RuntimeError):
        summarize(llm, ResearchState(topic="t"), [source], max_retries=1)


def test_summarize_detects_and_retries_on_prompt_echo():
    # A real failure mode observed from a real local model: it repeated the system
    # prompt's instructions back verbatim instead of writing a summary.
    llm = _FakeLLM(chat_responses=[SUMMARIZER_SYSTEM_PROMPT, "a real summary"])
    source = Source(title="A", url="http://a.com", content="a")
    summary = summarize(llm, ResearchState(topic="t"), [source], max_retries=1)
    assert summary == "a real summary"


def test_run_skips_summarize_when_a_loop_finds_no_new_sources():
    llm = _FakeLLM(tool_responses=[{"query": "q", "rationale": "r"}], chat_responses=[])
    backend = _FakeBackend(sources_per_call=[[]])
    config = Config(max_loops=1)

    state = run(topic="t", llm=llm, backend=backend, config=config)

    # summarize() was never called (chat_responses is empty and would IndexError
    # on pop() if it had been) -- the body stays empty; finalize() still wraps it.
    assert state.running_summary == "## Summary\n\n\n### Sources:\n"
