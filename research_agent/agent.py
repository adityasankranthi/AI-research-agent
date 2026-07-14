from dataclasses import dataclass
from typing import Any, Callable, Optional

from research_agent.config import Config
from research_agent.grounding import annotate_ungrounded, check_grounding
from research_agent.llm import LLMClient
from research_agent.prompts import (
    QUERY_WRITER_SYSTEM_PROMPT,
    REFLECTION_SYSTEM_PROMPT,
    REFLECTION_TOOL,
    SEARCH_QUERY_TOOL,
    SUMMARIZER_SYSTEM_PROMPT,
    current_date,
    reflection_user_message,
    summarizer_user_message,
)
from research_agent.search import format_citations, format_for_context
from research_agent.state import ResearchState, Source
from research_agent.tools import Tool


def _call_tool_with_retry(
    llm: LLMClient,
    messages: list[dict[str, str]],
    tool: dict[str, Any],
    required_field: str,
    max_retries: int,
) -> Optional[dict[str, Any]]:
    """Retry a structured-output call when the model's answer is missing the field
    we actually need -- bounded, so a consistently uncooperative model still falls
    through to the caller's static fallback rather than looping forever."""
    args = llm.chat_with_tool(messages, tool=tool)
    attempts = 0
    while (not args or not args.get(required_field)) and attempts < max_retries:
        messages = messages + [
            {
                "role": "user",
                "content": (
                    f"Your previous response didn't include a valid '{required_field}'. "
                    f"Call the {tool['function']['name']} tool with a '{required_field}' "
                    "value now."
                ),
            }
        ]
        args = llm.chat_with_tool(messages, tool=tool)
        attempts += 1
    return args


def generate_query(llm: LLMClient, state: ResearchState, max_retries: int = 0) -> str:
    messages = [
        {
            "role": "system",
            "content": QUERY_WRITER_SYSTEM_PROMPT.format(
                current_date=current_date(), research_topic=state.topic
            ),
        },
        {"role": "user", "content": "Generate a query for web search."},
    ]
    args = _call_tool_with_retry(llm, messages, SEARCH_QUERY_TOOL, "query", max_retries)
    if args and args.get("query"):
        return args["query"]
    return f"Tell me more about {state.topic}"


def web_research(tools: dict[str, Tool], query: str) -> list[Source]:
    return tools["web_search"].run(query=query)


def enrich_with_fetch(
    tools: dict[str, Tool], sources: list[Source], max_fetch: int
) -> list[Source]:
    """Replace up to `max_fetch` sources' short search-snippet content with the
    full page text, when a "fetch_page" tool is registered (Config.fetch_full_page).
    A no-op passthrough otherwise, so callers never need an `if` around this."""
    fetch_tool = tools.get("fetch_page")
    if fetch_tool is None:
        return sources

    enriched: list[Source] = []
    for i, source in enumerate(sources):
        if i >= max_fetch:
            enriched.append(source)
            continue
        result = fetch_tool.run(url=source.url)
        if result.ok and len(result.text) > len(source.content):
            enriched.append(Source(title=source.title, url=source.url, content=result.text))
        else:
            enriched.append(source)
    return enriched


def _looks_broken(content: str, system_prompt: str) -> bool:
    """Empty response, or the model echoed the instructions back instead of
    answering them -- both failure modes observed from real local models in
    practice. A real summary won't contain a long verbatim run of its own system
    prompt, so a substring match is a cheap, reliable enough signal."""
    if not content.strip():
        return True
    return system_prompt.strip()[:60] in content


def summarize(
    llm: LLMClient, state: ResearchState, new_sources: list[Source], max_retries: int = 0
) -> str:
    messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": summarizer_user_message(
                topic=state.topic,
                existing_summary=state.running_summary,
                new_context=format_for_context(new_sources),
            ),
        },
    ]
    content = llm.chat(messages)
    attempts = 0
    while _looks_broken(content, SUMMARIZER_SYSTEM_PROMPT) and attempts < max_retries:
        messages = messages + [
            {"role": "assistant", "content": content},
            {
                "role": "user",
                "content": (
                    "Your previous response was empty, or repeated these instructions "
                    "instead of answering them. Write only the summary text now -- no "
                    "preamble, no repeating the instructions."
                ),
            },
        ]
        content = llm.chat(messages)
        attempts += 1

    if _looks_broken(content, SUMMARIZER_SYSTEM_PROMPT):
        raise RuntimeError(
            "Summarizer returned an empty or malformed response after "
            f"{max_retries} retr{'y' if max_retries == 1 else 'ies'}. The model may not "
            "be well-suited for this task -- try a different --model."
        )

    return content


@dataclass
class Reflection:
    follow_up_query: str
    research_complete: bool = False


def reflect(llm: LLMClient, state: ResearchState, max_retries: int = 0) -> Reflection:
    messages = [
        {
            "role": "system",
            "content": REFLECTION_SYSTEM_PROMPT.format(research_topic=state.topic),
        },
        {"role": "user", "content": reflection_user_message(state.running_summary)},
    ]
    args = _call_tool_with_retry(llm, messages, REFLECTION_TOOL, "follow_up_query", max_retries)
    if args and args.get("follow_up_query"):
        return Reflection(
            follow_up_query=args["follow_up_query"],
            research_complete=bool(args.get("research_complete", False)),
        )
    return Reflection(follow_up_query=f"Tell me more about {state.topic}")


def finalize(state: ResearchState, enable_grounding_check: bool = True) -> ResearchState:
    summary = state.running_summary
    if enable_grounding_check:
        summary = annotate_ungrounded(summary, check_grounding(summary, state.sources))
    state.running_summary = (
        f"## Summary\n{summary}\n\n### Sources:\n{format_citations(state.sources)}"
    )
    return state


def run(
    topic: str,
    llm: LLMClient,
    tools: dict[str, Tool],
    config: Config,
    on_iteration: Optional[Callable[[int, ResearchState], None]] = None,
    on_query: Optional[Callable[[str], None]] = None,
) -> ResearchState:
    """The agent's control flow: an explicit loop, not a graph or state-machine
    framework.

    `generate_query` runs exactly once, up front. Every loop iteration after that
    runs `web_research` against whatever `state.search_query` currently holds, then
    summarizes, then (except on the final iteration, where the result would never be
    used) reflects to produce the *next* iteration's search query -- skipping that
    last reflection avoids paying for a call whose output is guaranteed to be
    discarded. If reflect() judges the summary already sufficiently addresses the
    topic (`Reflection.research_complete`) and `config.allow_early_stop` is set, the
    loop ends there instead of running to `max_loops` -- always after that loop's
    summarize()/on_iteration() have already run, so it never skips summarizing a
    completed loop's sources; `state.loop_count` simply reads lower than
    `config.max_loops` when this fires.

    `on_iteration`, if given, is called after each loop's summary is ready and
    before that loop's reflection -- a plain callback for whoever's driving the loop
    (the CLI uses it to print per-iteration progress) to observe what's happening
    without any framework-level visualization tooling.

    `on_query`, if given, is called with the query as soon as it's decided --
    right after the initial `generate_query()`, and again after each `reflect()`
    picks the next loop's query -- so a caller wanting to show "Searching: ..."
    isn't stuck waiting out an entire search+summarize round-trip for the first
    signal `on_iteration` would otherwise give it.

    Robustness: structured-output calls (query/reflection) and the summarizer retry
    up to `config.max_structured_output_retries` times against malformed model
    output before falling back (query/reflection) or raising (summarizer -- see
    `summarize`'s docstring for why an empty summary fails loudly instead of writing
    a broken report). A loop that finds no new sources skips summarization entirely
    rather than asking the model to summarize an empty context, which risks it
    inventing content to fill the gap.
    """
    retries = config.max_structured_output_retries
    state = ResearchState(topic=topic)
    state.search_query = generate_query(llm, state, max_retries=retries)
    if on_query:
        on_query(state.search_query)

    for i in range(config.max_loops):
        new_sources = web_research(tools, state.search_query)
        new_sources = enrich_with_fetch(tools, new_sources, config.max_fetch_per_loop)
        state.add_sources(new_sources)

        if new_sources:
            state.running_summary = summarize(llm, state, new_sources, max_retries=retries)

        state.loop_count += 1

        if on_iteration:
            on_iteration(i, state)

        if i < config.max_loops - 1:
            reflection = reflect(llm, state, max_retries=retries)
            if config.allow_early_stop and reflection.research_complete:
                break
            state.search_query = reflection.follow_up_query
            if on_query:
                on_query(state.search_query)

    return finalize(state, enable_grounding_check=config.enable_citation_grounding_check)
