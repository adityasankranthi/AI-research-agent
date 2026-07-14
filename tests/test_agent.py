import pytest

from research_agent.agent import enrich_with_fetch, generate_query, reflect, run, summarize
from research_agent.config import Config
from research_agent.fetch import FetchResult
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


class _FakeSearchTool:
    def __init__(self, sources_per_call):
        self._sources_per_call = list(sources_per_call)
        self.queries_seen: list[str] = []

    def run(self, query):
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
    search_tool = _FakeSearchTool(sources_per_call=[[source_a], [source_b]])
    tools = {"web_search": search_tool}
    config = Config(max_loops=2)

    state = run(topic="test topic", llm=llm, tools=tools, config=config)

    assert llm.tool_calls_seen == ["generate_search_query", "propose_followup_query"]
    assert search_tool.queries_seen == ["initial query", "followup query"]
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
    tools = {"web_search": _FakeSearchTool(sources_per_call=[[], []])}
    config = Config(max_loops=2)
    seen: list[tuple[int, str]] = []

    run(
        topic="t",
        llm=llm,
        tools=tools,
        config=config,
        on_iteration=lambda i, state: seen.append((i, state.search_query)),
    )

    # loop 0's callback must see the query that was just searched ("initial query"),
    # not the follow-up query reflect() computes afterward for loop 1.
    assert seen == [(0, "initial query"), (1, "followup query")]


def test_run_calls_on_query_immediately_for_initial_and_followup_queries():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {"knowledge_gap": "gap", "follow_up_query": "followup query"},
        ],
        chat_responses=["summary after loop 1", "summary after loop 2"],
    )
    tools = {"web_search": _FakeSearchTool(sources_per_call=[[], []])}
    config = Config(max_loops=2)
    seen: list[str] = []

    run(topic="t", llm=llm, tools=tools, config=config, on_query=seen.append)

    assert seen == ["initial query", "followup query"]


def test_run_does_not_call_on_query_after_early_stop():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {
                "knowledge_gap": "none",
                "follow_up_query": "would-be next query",
                "research_complete": True,
            },
        ],
        chat_responses=["summary after loop 1"],
    )
    tools = {"web_search": _FakeSearchTool(sources_per_call=[[], []])}
    config = Config(max_loops=3, allow_early_stop=True)
    seen: list[str] = []

    run(topic="t", llm=llm, tools=tools, config=config, on_query=seen.append)

    assert seen == ["initial query"]


def test_run_single_loop_never_calls_reflect():
    llm = _FakeLLM(
        tool_responses=[{"query": "only query", "rationale": "r"}],
        chat_responses=["only summary"],
    )
    tools = {"web_search": _FakeSearchTool(sources_per_call=[[]])}
    config = Config(max_loops=1)

    run(topic="t", llm=llm, tools=tools, config=config)

    assert llm.tool_calls_seen == ["generate_search_query"]


def test_run_stops_early_when_reflect_reports_research_complete():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {
                "knowledge_gap": "none",
                "follow_up_query": "would-be next query",
                "research_complete": True,
            },
        ],
        chat_responses=["summary after loop 1"],
    )
    source_a = Source(title="A", url="http://a.com", content="a")
    search_tool = _FakeSearchTool(sources_per_call=[[source_a], [Source(title="B", url="http://b.com", content="b")]])
    tools = {"web_search": search_tool}
    config = Config(max_loops=3, allow_early_stop=True)

    state = run(topic="test topic", llm=llm, tools=tools, config=config)

    # Only loop 1's search happened; reflect() reported research_complete after it,
    # so loop 2 (and its search) never ran.
    assert search_tool.queries_seen == ["initial query"]
    assert state.loop_count == 1
    assert "summary after loop 1" in state.running_summary


def test_run_ignores_research_complete_when_allow_early_stop_is_false():
    llm = _FakeLLM(
        tool_responses=[
            {"query": "initial query", "rationale": "r"},
            {
                "knowledge_gap": "none",
                "follow_up_query": "next query",
                "research_complete": True,
            },
        ],
        chat_responses=["summary after loop 1", "summary after loop 2"],
    )
    source_a = Source(title="A", url="http://a.com", content="a")
    source_b = Source(title="B", url="http://b.com", content="b")
    search_tool = _FakeSearchTool(sources_per_call=[[source_a], [source_b]])
    tools = {"web_search": search_tool}
    config = Config(max_loops=2, allow_early_stop=False)

    state = run(topic="test topic", llm=llm, tools=tools, config=config)

    assert search_tool.queries_seen == ["initial query", "next query"]
    assert state.loop_count == 2


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

    reflection = reflect(_NoToolLLM(), ResearchState(topic="fallback topic"))
    assert reflection.follow_up_query == "Tell me more about fallback topic"
    assert reflection.research_complete is False


def test_reflect_reports_research_complete_when_tool_says_so():
    llm = _FakeLLM(
        tool_responses=[
            {
                "knowledge_gap": "none",
                "follow_up_query": "irrelevant",
                "research_complete": True,
            }
        ]
    )
    reflection = reflect(llm, ResearchState(topic="t"))
    assert reflection.research_complete is True


def test_reflect_defaults_research_complete_to_false_when_omitted():
    llm = _FakeLLM(
        tool_responses=[{"knowledge_gap": "gap", "follow_up_query": "q"}]
    )
    reflection = reflect(llm, ResearchState(topic="t"))
    assert reflection.research_complete is False


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
    tools = {"web_search": _FakeSearchTool(sources_per_call=[[]])}
    config = Config(max_loops=1)

    state = run(topic="t", llm=llm, tools=tools, config=config)

    # summarize() was never called (chat_responses is empty and would IndexError
    # on pop() if it had been) -- the body stays empty; finalize() still wraps it.
    assert state.running_summary == "## Summary\n\n\n### Sources:\n"


class _FakeFetchTool:
    def __init__(self, results_by_url):
        self._results_by_url = results_by_url
        self.urls_seen: list[str] = []

    def run(self, url):
        self.urls_seen.append(url)
        return self._results_by_url[url]


def test_enrich_with_fetch_is_a_passthrough_when_no_fetch_tool_registered():
    sources = [Source(title="A", url="http://a.com", content="short")]
    assert enrich_with_fetch({}, sources, max_fetch=3) == sources


def test_enrich_with_fetch_replaces_content_when_fetched_text_is_longer():
    source = Source(title="A", url="http://a.com", content="short snippet")
    fetch_tool = _FakeFetchTool(
        {"http://a.com": FetchResult(url="http://a.com", text="much longer full page text", ok=True)}
    )

    enriched = enrich_with_fetch({"fetch_page": fetch_tool}, [source], max_fetch=3)

    assert enriched[0].content == "much longer full page text"
    assert enriched[0].title == "A"
    assert enriched[0].url == "http://a.com"


def test_enrich_with_fetch_keeps_original_when_fetch_fails():
    source = Source(title="A", url="http://a.com", content="short snippet")
    fetch_tool = _FakeFetchTool(
        {"http://a.com": FetchResult(url="http://a.com", text="", ok=False, error="boom")}
    )

    enriched = enrich_with_fetch({"fetch_page": fetch_tool}, [source], max_fetch=3)

    assert enriched[0] is source


def test_enrich_with_fetch_keeps_original_when_fetched_text_is_not_longer():
    source = Source(title="A", url="http://a.com", content="a fairly long snippet already")
    fetch_tool = _FakeFetchTool(
        {"http://a.com": FetchResult(url="http://a.com", text="short", ok=True)}
    )

    enriched = enrich_with_fetch({"fetch_page": fetch_tool}, [source], max_fetch=3)

    assert enriched[0] is source


def test_enrich_with_fetch_respects_max_fetch():
    sources = [
        Source(title="A", url="http://a.com", content="a"),
        Source(title="B", url="http://b.com", content="b"),
    ]
    fetch_tool = _FakeFetchTool(
        {"http://a.com": FetchResult(url="http://a.com", text="longer a text", ok=True)}
    )

    enriched = enrich_with_fetch({"fetch_page": fetch_tool}, sources, max_fetch=1)

    assert fetch_tool.urls_seen == ["http://a.com"]
    assert enriched[0].content == "longer a text"
    assert enriched[1] is sources[1]
