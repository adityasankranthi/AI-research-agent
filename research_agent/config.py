import os
from dataclasses import dataclass, fields
from typing import Optional

# Default local model sized for a 16GB-unified-memory machine: a ~7B quantized model
# runs comfortably alongside a browser/IDE, unlike a 13B+ model.
DEFAULT_MODEL = "ollama/qwen2.5:7b"
DEFAULT_API_BASE = "http://localhost:11434"

ENV_PREFIX = "RESEARCH_AGENT_"


def _coerce(raw: str, annotation: object) -> object:
    if annotation is bool:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if annotation is int:
        return int(raw)
    if annotation is float:
        return float(raw)
    return raw


@dataclass
class Config:
    """Runtime knobs for the agent. Resolution order: explicit arg > env var > default.

    A plain dataclass with an env-var-aware constructor is all the indirection this
    project needs -- there's exactly one caller (the CLI and the eval runner), so a
    validation framework would be pure overhead.
    """

    model: str = DEFAULT_MODEL
    api_base: Optional[str] = None
    search_backend: str = "duckduckgo"
    max_loops: int = 3
    max_search_results: int = 3
    fetch_full_page: bool = False
    # A cold or "thinking" local model can take 60-90s+ for a modest response, so a
    # short timeout fires on calls that are genuinely still working, not just hung.
    # Generous on purpose; hosted API providers return well before this.
    llm_timeout_seconds: float = 180.0
    # One retry with corrective feedback before falling back (query/reflection) or
    # raising (summarizer) -- bounded so a consistently uncooperative model fails fast
    # instead of looping.
    max_structured_output_retries: int = 1
    # Some hosted gateways reject a request outright if the account can't afford
    # `max_tokens` at the model's absolute ceiling, even though actual usage is far
    # lower -- an explicit, modest cap avoids that regardless of provider.
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        # Only Ollama needs a local base URL by default -- hosted providers (and
        # self-hosted OpenAI-compatible servers, via an explicit --api-base) resolve
        # their own endpoint from the model string itself.
        if self.api_base is None and self.model.startswith("ollama/"):
            self.api_base = DEFAULT_API_BASE

    @classmethod
    def from_env(cls, **overrides: object) -> "Config":
        values: dict[str, object] = {}
        for f in fields(cls):
            raw = os.environ.get(f"{ENV_PREFIX}{f.name.upper()}")
            if raw is not None:
                values[f.name] = _coerce(raw, f.type)
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)
