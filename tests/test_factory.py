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
    _, backend = build_components(config)
    assert isinstance(backend, DuckDuckGoBackend)


def test_build_components_wires_tavily_backend(monkeypatch):
    monkeypatch.setattr(
        "research_agent.search.TavilyClient", lambda api_key=None: object()
    )
    config = Config(search_backend="tavily")
    _, backend = build_components(config)
    assert isinstance(backend, TavilyBackend)
