import research_agent.tools as tools_module
from research_agent.config import Config
from research_agent.state import Source
from research_agent.tools import FetchTool, SearchTool, build_tools


class _FakeBackend:
    def __init__(self, sources):
        self._sources = sources
        self.calls: list[tuple[str, int]] = []

    def search(self, query, max_results):
        self.calls.append((query, max_results))
        return self._sources


def test_search_tool_delegates_to_backend_with_configured_max_results():
    source = Source(title="A", url="http://a.com", content="a")
    backend = _FakeBackend(sources=[source])
    tool = SearchTool(backend=backend, max_results=5)

    result = tool.run(query="test query")

    assert result == [source]
    assert backend.calls == [("test query", 5)]


def test_build_tools_registers_web_search_with_max_results_from_config():
    backend = _FakeBackend(sources=[])
    config = Config(max_search_results=7)

    tools = build_tools(backend, config)

    assert isinstance(tools["web_search"], SearchTool)
    assert tools["web_search"].max_results == 7
    assert tools["web_search"].backend is backend


def test_build_tools_omits_fetch_page_by_default():
    tools = build_tools(_FakeBackend(sources=[]), Config())
    assert "fetch_page" not in tools


def test_build_tools_registers_fetch_page_when_enabled_in_config():
    config = Config(fetch_full_page=True, fetch_timeout_seconds=5.0, fetch_max_chars=123)

    tools = build_tools(_FakeBackend(sources=[]), config)

    assert isinstance(tools["fetch_page"], FetchTool)
    assert tools["fetch_page"].timeout == 5.0
    assert tools["fetch_page"].max_chars == 123


def test_fetch_tool_delegates_to_fetch_page_with_configured_timeout_and_max_chars(monkeypatch):
    captured = {}

    def fake_fetch_page(url, timeout, max_chars):
        captured["url"] = url
        captured["timeout"] = timeout
        captured["max_chars"] = max_chars
        return "fake result"

    # tools.py imported fetch_page by name -- patch the reference it actually calls.
    monkeypatch.setattr(tools_module, "fetch_page", fake_fetch_page)

    tool = FetchTool(timeout=9.0, max_chars=99)
    result = tool.run(url="http://example.com")

    assert result == "fake result"
    assert captured == {"url": "http://example.com", "timeout": 9.0, "max_chars": 99}
