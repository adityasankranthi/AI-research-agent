from research_agent.config import Config
from research_agent.factory import build_components
from research_agent.llm import LLMClient
from research_agent.search import DuckDuckGoBackend, TavilyBackend


def test_build_components_wires_llm_from_config():
    config = Config(model="openai/gpt-4o-mini", max_output_tokens=1024)
    llm, _ = build_components(config)

    assert isinstance(llm, LLMClient)
    assert llm.model == "openai/gpt-4o-mini"
    assert llm.max_tokens == 1024


def test_build_components_wires_search_backend_from_config():
    config = Config(search_backend="duckduckgo")
    _, tools = build_components(config)
    assert isinstance(tools["web_search"].backend, DuckDuckGoBackend)


def test_build_components_wires_tavily_backend(monkeypatch):
    monkeypatch.setattr(
        "research_agent.search.TavilyClient", lambda api_key=None: object()
    )
    config = Config(search_backend="tavily")
    _, tools = build_components(config)
    assert isinstance(tools["web_search"].backend, TavilyBackend)


def test_build_components_threads_llm_api_key():
    config = Config(model="openai/gpt-4o-mini")
    llm, _ = build_components(config, llm_api_key="sk-test")
    assert llm.api_key == "sk-test"


def test_build_components_threads_search_api_key(monkeypatch):
    captured = {}

    def fake_tavily_client(api_key=None):
        captured["api_key"] = api_key
        return object()

    monkeypatch.setattr("research_agent.search.TavilyClient", fake_tavily_client)
    config = Config(search_backend="tavily")
    build_components(config, search_api_key="tvly-test")

    assert captured["api_key"] == "tvly-test"
