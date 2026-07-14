from research_agent.config import Config
from research_agent.llm import LLMClient
from research_agent.search import get_search_backend
from research_agent.tools import Tool, build_tools


def build_components(config: Config) -> tuple[LLMClient, dict[str, Tool]]:
    """The one place an `LLMClient` and the agent's `Tool`s get constructed from a
    `Config` -- shared by the CLI and the eval runner so that wiring only lives in
    one place instead of being copy-pasted between the two entry points."""
    llm = LLMClient(
        model=config.model,
        api_base=config.api_base,
        timeout=config.llm_timeout_seconds,
        max_tokens=config.max_output_tokens,
    )
    backend = get_search_backend(config.search_backend)
    tools = build_tools(backend, config)
    return llm, tools
