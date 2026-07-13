import pytest

from research_agent.search import (
    DuckDuckGoBackend,
    TavilyBackend,
    dedupe_sources,
    format_citations,
    format_for_context,
    get_search_backend,
)
from research_agent.state import Source

A = Source(title="A", url="http://a.com", content="content a")
B = Source(title="B", url="http://b.com", content="content b")
A_DUPLICATE = Source(title="A again", url="http://a.com", content="different content")


def test_dedupe_sources_keeps_first_occurrence_by_url():
    assert dedupe_sources([A, B, A_DUPLICATE]) == [A, B]


def test_dedupe_sources_preserves_order():
    assert dedupe_sources([B, A]) == [B, A]


def test_format_for_context_includes_full_content():
    text = format_for_context([A])
    assert "Source: A" in text
    assert "URL: http://a.com" in text
    assert "content a" in text


def test_format_citations_is_deduped_bullet_list():
    assert format_citations([A, B, A_DUPLICATE]) == "* A : http://a.com\n* B : http://b.com"


class _FakeDDGS:
    def __init__(self, results):
        self._results = results

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results):
        return self._results


def test_duckduckgo_backend_filters_incomplete_results(monkeypatch):
    fake_results = [
        {"href": "http://a.com", "title": "A", "body": "content a"},
        {"href": "http://b.com", "title": None, "body": "content b"},  # missing title
        {"href": None, "title": "C", "body": "content c"},  # missing url
    ]
    monkeypatch.setattr("research_agent.search.DDGS", lambda: _FakeDDGS(fake_results))

    backend = DuckDuckGoBackend()
    sources = backend.search("test query", max_results=3)

    assert sources == [Source(title="A", url="http://a.com", content="content a")]


class _SequencedDDGS:
    """Returns each successive item of `results_sequence` on successive `text()`
    calls, repeating the last item once exhausted -- simulates DDGS recovering
    after a burst-rate-limited empty response."""

    def __init__(self, results_sequence, call_log):
        self._results_sequence = results_sequence
        self._call_log = call_log

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results):
        idx = min(len(self._call_log), len(self._results_sequence) - 1)
        self._call_log.append(query)
        return self._results_sequence[idx]


def test_duckduckgo_backend_retries_once_after_empty_results_then_succeeds(monkeypatch):
    call_log: list[str] = []
    results_sequence = [[], [{"href": "http://a.com", "title": "A", "body": "content a"}]]
    monkeypatch.setattr(
        "research_agent.search.DDGS", lambda: _SequencedDDGS(results_sequence, call_log)
    )
    monkeypatch.setattr("research_agent.search.time.sleep", lambda seconds: None)

    backend = DuckDuckGoBackend()
    sources = backend.search("query", max_results=3)

    assert len(call_log) == 2
    assert sources == [Source(title="A", url="http://a.com", content="content a")]


def test_duckduckgo_backend_gives_up_after_exhausting_retries(monkeypatch):
    call_log: list[str] = []
    monkeypatch.setattr(
        "research_agent.search.DDGS", lambda: _SequencedDDGS([[]], call_log)
    )
    monkeypatch.setattr("research_agent.search.time.sleep", lambda seconds: None)

    backend = DuckDuckGoBackend()
    sources = backend.search("query", max_results=3, max_retries=1)

    assert len(call_log) == 2  # initial attempt + one retry, no more
    assert sources == []


class _FakeTavilyClient:
    def __init__(self, results):
        self._results = results

    def search(self, query, max_results):
        return {"results": self._results}


def test_tavily_backend_parses_results_and_filters_incomplete(monkeypatch):
    fake_results = [
        {"url": "http://a.com", "title": "A", "content": "content a"},
        {"url": "http://b.com", "title": None, "content": "content b"},  # missing title
    ]
    monkeypatch.setattr(
        "research_agent.search.TavilyClient",
        lambda api_key=None: _FakeTavilyClient(fake_results),
    )

    backend = TavilyBackend(api_key="test-key")
    sources = backend.search("query", max_results=2)

    assert sources == [Source(title="A", url="http://a.com", content="content a")]


def test_get_search_backend_returns_duckduckgo_by_default():
    assert isinstance(get_search_backend("duckduckgo"), DuckDuckGoBackend)


def test_get_search_backend_returns_tavily(monkeypatch):
    monkeypatch.setattr(
        "research_agent.search.TavilyClient", lambda api_key=None: _FakeTavilyClient([])
    )
    assert isinstance(get_search_backend("tavily"), TavilyBackend)


def test_get_search_backend_raises_for_unknown_name():
    with pytest.raises(ValueError):
        get_search_backend("bing")
