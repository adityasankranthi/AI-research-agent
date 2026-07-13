import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import litellm

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: Optional[str]) -> Optional[dict[str, Any]]:
    """Recover a JSON object from assistant text when the model didn't make a real
    tool call -- e.g. it printed `{"query": "...", "rationale": "..."}` as prose
    instead of using the function-calling interface. Common with smaller local models.

    Tries the whole message first, then the first `{...}` block found inside it (to
    handle prose wrapping or a fenced ```json``` block). Returns None if nothing
    parses to a JSON object.
    """
    if not text:
        return None
    text = text.strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass

    return None


@dataclass
class LLMClient:
    """One client for every model provider, local or hosted.

    Built on litellm, whose `model` string carries the provider
    (`ollama/qwen2.5:7b`, `openai/gpt-4o-mini`, `anthropic/claude-...`,
    `openrouter/anthropic/claude-haiku-4-5`) -- so nothing else in this project ever
    branches on "which provider am I talking to."
    """

    model: str
    api_base: Optional[str] = None
    timeout: float = 60.0
    # Explicit and modest on purpose: some hosted gateways pre-check whether the
    # account can afford `max_tokens` output tokens at the model's worst case before
    # running the request at all, and reject outright if not -- even when actual
    # expected usage is far lower. Leaving this unset lets it default to the model's
    # absolute ceiling, which is what triggers that rejection.
    max_tokens: int = 2048

    total_cost: float = field(default=0.0, init=False)
    n_calls: int = field(default=0, init=False)

    def _track_cost(self, response: Any) -> None:
        try:
            cost = litellm.completion_cost(response) or 0.0
        except Exception:
            cost = 0.0
        self.total_cost += cost
        self.n_calls += 1

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Free-text completion -- used for summarization, where there's no fixed
        output shape to extract."""
        response = litellm.completion(
            model=self.model,
            messages=messages,
            api_base=self.api_base,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
        )
        self._track_cost(response)
        return response.choices[0].message.content or ""

    def chat_with_tool(
        self, messages: list[dict[str, str]], tool: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Structured-output completion: offer `tool` (a single OpenAI-style function
        schema) and return its arguments as a dict.

        Tries a native tool call first; if the model doesn't make one -- common with
        smaller local models that ignore the `tools` parameter and just print JSON as
        prose -- falls back to scanning the plain-text response for a JSON object.
        This single strategy (tool-calling with a text-extraction fallback) covers
        every provider without any JSON-mode/tool-calling switch to configure.
        """
        response = litellm.completion(
            model=self.model,
            messages=messages,
            tools=[tool],
            api_base=self.api_base,
            timeout=self.timeout,
            max_tokens=self.max_tokens,
            # litellm's completion() otherwise imports its MCP-handler code path
            # whenever `tools` is set, which pulls in its proxy-server dependency
            # tree (fastapi, orjson, ...) for a feature this project doesn't use.
            _skip_mcp_handler=True,
        )
        self._track_cost(response)

        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        if tool_calls:
            try:
                return json.loads(tool_calls[0].function.arguments)
            except (json.JSONDecodeError, TypeError):
                pass

        return extract_json_object(message.content)
