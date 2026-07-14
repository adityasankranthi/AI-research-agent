"""A minimal capability abstraction for the agent loop: a `Tool` is anything with a
`ToolSpec` (name/description/JSON-Schema parameters) and a `run(**kwargs)` method,
following the same structural-`Protocol` style as `SearchBackend` in search.py.

This is unrelated to the lowercase "tool" dicts in prompts.py/judge.py
(SEARCH_QUERY_TOOL, REFLECTION_TOOL, FACT_CHECK_TOOL) -- those are OpenAI-style
function-calling schemas passed straight to LLMClient.chat_with_tool for
structured-output extraction (query generation, reflection, fact-checking), and
nothing here changes them. The `Tool` registry below exists only to standardize
what a capability the agent loop invokes directly (search, page fetch) looks
like -- the loop still hardcodes *when* to call which tool, so no orchestration
framework is hiding the control flow.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from research_agent.config import Config
from research_agent.fetch import FetchResult, fetch_page
from research_agent.search import SearchBackend
from research_agent.state import Source


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(Protocol):
    spec: ToolSpec

    def run(self, **kwargs: Any) -> Any: ...


def _search_tool_spec() -> ToolSpec:
    return ToolSpec(
        name="web_search",
        description="Search the web and return sources (title/url/content snippet).",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )


@dataclass
class SearchTool:
    backend: SearchBackend
    max_results: int = 3
    spec: ToolSpec = field(default_factory=_search_tool_spec)

    def run(self, query: str) -> list[Source]:
        return self.backend.search(query, max_results=self.max_results)


def _fetch_tool_spec() -> ToolSpec:
    return ToolSpec(
        name="fetch_page",
        description="Fetch a URL and return its extracted visible text.",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    )


@dataclass
class FetchTool:
    timeout: float = 15.0
    max_chars: int = 4000
    spec: ToolSpec = field(default_factory=_fetch_tool_spec)

    def run(self, url: str) -> FetchResult:
        return fetch_page(url, timeout=self.timeout, max_chars=self.max_chars)


def build_tools(backend: SearchBackend, config: Config) -> dict[str, Tool]:
    tools: dict[str, Tool] = {
        "web_search": SearchTool(backend=backend, max_results=config.max_search_results)
    }
    if config.fetch_full_page:
        tools["fetch_page"] = FetchTool(
            timeout=config.fetch_timeout_seconds, max_chars=config.fetch_max_chars
        )
    return tools
