from typing import Literal, Optional

from pydantic import BaseModel, Field, SecretStr, model_validator

# Bounds requests can push the agent to: a public demo shares one server, so these
# caps exist to bound worst-case cost/latency per request regardless of what a
# visitor's own key can afford -- not a product decision about "ideal" defaults.
MAX_LOOPS = 5
MAX_SEARCH_RESULTS = 6


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    model: str
    api_base: Optional[str] = None
    search_backend: Literal["duckduckgo", "tavily"] = "tavily"
    max_search_results: int = Field(3, ge=1, le=MAX_SEARCH_RESULTS)
    fetch_full_page: bool = False
    loops: int = Field(2, ge=1, le=MAX_LOOPS)
    # SecretStr keeps a raw key out of any accidental repr()/str()/log of the
    # request object -- .get_secret_value() is required to read the real value.
    llm_api_key: SecretStr
    tavily_api_key: Optional[SecretStr] = None

    @model_validator(mode="after")
    def _tavily_key_required_when_selected(self) -> "ResearchRequest":
        if self.search_backend == "tavily" and not self.tavily_api_key:
            raise ValueError("tavily_api_key is required when search_backend='tavily'")
        return self
