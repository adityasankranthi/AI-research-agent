from typing import Optional

from research_agent.config import Config
from research_agent.llm import LLMClient
from research_agent.search import get_search_backend
from research_agent.tools import Tool, build_tools


def build_components(
    config: Config,
    llm_api_key: Optional[str] = None,
    search_api_key: Optional[str] = None,
) -> tuple[LLMClient, dict[str, Tool]]:
    """The one place an `LLMClient` and the agent's `Tool`s get constructed from a
    `Config` -- shared by the CLI and the eval runner so that wiring only lives in
    one place instead of being copy-pasted between the two entry points.

    `llm_api_key`/`search_api_key` are deliberately separate parameters rather than
    `Config` fields -- see api/stream.py for the caller that needs a request-scoped
    key that never touches process env vars or `Config.from_env()`'s env-var
    resolution (which would otherwise leak a stray server-side key into every
    concurrent caller). The CLI and eval runner never pass these, so they keep
    resolving keys the existing way (via litellm/TavilyClient reading env vars).
    """
    llm = LLMClient(
        model=config.model,
        api_base=config.api_base,
        api_key=llm_api_key,
        timeout=config.llm_timeout_seconds,
        max_tokens=config.max_output_tokens,
    )
    backend = get_search_backend(config.search_backend, api_key=search_api_key)
    tools = build_tools(backend, config)
    return llm, tools
