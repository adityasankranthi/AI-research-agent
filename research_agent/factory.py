from research_agent.config import Config
from research_agent.llm import LLMClient
from research_agent.search import SearchBackend, get_search_backend


def build_components(config: Config) -> tuple[LLMClient, SearchBackend]:
    """The one place an `LLMClient` and a `SearchBackend` get constructed from a
    `Config` -- shared by the CLI and the eval runner so that wiring only lives in
    one place instead of being copy-pasted between the two entry points."""
    llm = LLMClient(
        model=config.model,
        api_base=config.api_base,
        timeout=config.llm_timeout_seconds,
        max_tokens=config.max_output_tokens,
    )
    backend = get_search_backend(config.search_backend)
    return llm, backend
