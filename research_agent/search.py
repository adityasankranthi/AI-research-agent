import time
from typing import Optional, Protocol

from duckduckgo_search import DDGS
from tavily import TavilyClient

from research_agent.state import Source


class SearchBackend(Protocol):
    """Anything that can turn a query into a list of sources. Adding a new backend
    (SearXNG, Perplexity, ...) is just a class satisfying this same shape -- the
    agent core never touches search-provider specifics.
    """

    def search(self, query: str, max_results: int) -> list[Source]: ...


class DuckDuckGoBackend:
    """No API key required -- the default backend.

    Free and scraping-based (no official API), so it can occasionally hit a rate
    limit and silently return zero results instead of raising an error. One retry
    after a short pause recovers from a brief burst; a sustained block needs a
    different backend (see TavilyBackend below).
    """

    def search(
        self, query: str, max_results: int = 3, max_retries: int = 1, retry_delay: float = 2.0
    ) -> list[Source]:
        sources = self._search_once(query, max_results)
        attempts = 0
        while not sources and attempts < max_retries:
            time.sleep(retry_delay)
            sources = self._search_once(query, max_results)
            attempts += 1
        return sources

    def _search_once(self, query: str, max_results: int) -> list[Source]:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        sources = []
        for r in results:
            url = r.get("href")
            title = r.get("title")
            content = r.get("body")
            if not all([url, title, content]):
                continue
            sources.append(Source(title=title, url=url, content=content))
        return sources


class TavilyBackend:
    """Needs a TAVILY_API_KEY (free tier available at tavily.com). A real search API
    rather than DuckDuckGoBackend's scraping approach -- not subject to the same
    unpredictable rate limiting, at the cost of requiring a key."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._client = TavilyClient(api_key=api_key) if api_key else TavilyClient()

    def search(self, query: str, max_results: int = 3) -> list[Source]:
        response = self._client.search(query, max_results=max_results)
        sources = []
        for r in response.get("results", []):
            url = r.get("url")
            title = r.get("title")
            content = r.get("content")
            if not all([url, title, content]):
                continue
            sources.append(Source(title=title, url=url, content=content))
        return sources


def get_search_backend(name: str) -> SearchBackend:
    if name == "tavily":
        return TavilyBackend()
    if name == "duckduckgo":
        return DuckDuckGoBackend()
    raise ValueError(f"Unknown search backend: {name!r} (expected 'duckduckgo' or 'tavily')")


def dedupe_sources(sources: list[Source]) -> list[Source]:
    """Keep the first occurrence of each URL, preserving order."""
    seen: set[str] = set()
    unique: list[Source] = []
    for source in sources:
        if source.url not in seen:
            seen.add(source.url)
            unique.append(source)
    return unique


def format_for_context(sources: list[Source]) -> str:
    """Render sources as blocks the summarizer LLM reads as its context."""
    blocks = [
        f"Source: {s.title}\nURL: {s.url}\nContent: {s.content}" for s in sources
    ]
    return "\n\n".join(blocks)


def format_citations(sources: list[Source]) -> str:
    """Render deduplicated sources as a markdown bullet list for the final report."""
    return "\n".join(f"* {s.title} : {s.url}" for s in dedupe_sources(sources))
