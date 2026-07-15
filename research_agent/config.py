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
    # When set, up to `max_fetch_per_loop` new sources per loop have their full page
    # text fetched (via the "fetch_page" tool) and substituted for the search
    # backend's short snippet -- see research_agent/fetch.py.
    fetch_full_page: bool = False
    fetch_timeout_seconds: float = 15.0
    # Conservative on purpose: a fetched page's extracted text is added to the
    # summarizer's context on top of the running summary, which matters for
    # small-context local models.
    fetch_max_chars: int = 4000
    # Independent of max_search_results -- raising search breadth shouldn't
    # silently multiply how many pages get fetched (and how long that takes).
    max_fetch_per_loop: int = 3
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
    # Appends an "### Unverified claims" footer listing sentences whose inline
    # citation doesn't match a gathered source -- see research_agent/grounding.py.
    enable_citation_grounding_check: bool = True
    # Lets reflect() end the loop before max_loops when it judges the summary
    # already sufficiently addresses the topic. A killswitch for cases needing a
    # reproducible, fixed loop count (e.g. comparing runs in the eval harness).
    allow_early_stop: bool = True
    # "iterative" preserves the cheap summarize/reflect loop. "deep" first builds
    # a coverage plan, retains atomic evidence, and writes the report once at the end.
    research_mode: str = "iterative"
    min_evidence_per_plan_item: int = 2
    max_plan_items: int = 8
    deep_queries_per_loop: int = 2
    enable_final_revision: bool = True
    enforce_citation_compliance: bool = True

    def __post_init__(self) -> None:
        if self.research_mode not in {"iterative", "deep"}:
            raise ValueError("research_mode must be 'iterative' or 'deep'")
        if self.min_evidence_per_plan_item < 1:
            raise ValueError("min_evidence_per_plan_item must be at least 1")
        if self.max_plan_items < 1:
            raise ValueError("max_plan_items must be at least 1")
        if self.deep_queries_per_loop < 1:
            raise ValueError("deep_queries_per_loop must be at least 1")
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
