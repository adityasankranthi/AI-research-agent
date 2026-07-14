import asyncio
import json
import queue
import threading
from typing import Any, AsyncIterator, Optional

from research_agent.agent import run
from research_agent.config import Config
from research_agent.factory import build_components
from research_agent.llm import LLMClient
from research_agent.state import ResearchState

from api.schemas import ResearchRequest

# Sentinel distinguishing "stream is done" from any legitimate queued payload.
_DONE = object()

# Bounds concurrent in-flight research runs on this process -- a coarse but simple
# safeguard against one burst of visitors starving everyone else's requests. Not
# distributed-safe (each process gets its own semaphore); fine for a single-instance
# demo deployment.
MAX_CONCURRENT_RESEARCH = 8
_concurrency_limiter = asyncio.Semaphore(MAX_CONCURRENT_RESEARCH)


def _redact(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run_research(
    req: ResearchRequest,
    llm_key: str,
    tavily_key: Optional[str],
    q: "queue.Queue[Any]",
) -> None:
    """Runs on a background thread -- agent.run() is a blocking call, so this keeps
    the async event loop free to serve other requests while this one researches."""
    sources_seen = 0
    llm_holder: dict[str, LLMClient] = {}

    def on_query(query: str) -> None:
        q.put(("searching", {"query": query}))

    def on_iteration(i: int, state: ResearchState) -> None:
        nonlocal sources_seen
        new_sources = state.sources[sources_seen:]
        sources_seen = len(state.sources)
        llm = llm_holder["llm"]
        q.put((
            "iteration",
            {
                "loop": i + 1,
                "loops_total": req.loops,
                "search_query": state.search_query,
                "new_sources": [{"title": s.title, "url": s.url} for s in new_sources],
                "sources_total": len(state.sources),
                "summary_preview": state.running_summary[:280],
                "cost_so_far": llm.total_cost,
                "calls_so_far": llm.n_calls,
            },
        ))

    try:
        config = Config(
            model=req.model,
            api_base=req.api_base,
            search_backend=req.search_backend,
            max_loops=req.loops,
            max_search_results=req.max_search_results,
            fetch_full_page=req.fetch_full_page,
        )
        llm, tools = build_components(config, llm_api_key=llm_key, search_api_key=tavily_key)
        llm_holder["llm"] = llm

        state = run(
            topic=req.topic,
            llm=llm,
            tools=tools,
            config=config,
            on_iteration=on_iteration,
            on_query=on_query,
        )
        q.put((
            "done",
            {
                "topic": state.topic,
                "report_markdown": state.running_summary,
                "sources": [{"title": s.title, "url": s.url} for s in state.sources],
                "loop_count": state.loop_count,
                "llm_cost": llm_holder["llm"].total_cost,
                "llm_calls": llm_holder["llm"].n_calls,
            },
        ))
    except Exception as exc:
        q.put(("error", {"message": _redact(str(exc), [llm_key, tavily_key or ""])}))
    finally:
        q.put(_DONE)


async def event_stream(req: ResearchRequest) -> AsyncIterator[str]:
    if _concurrency_limiter.locked():
        yield _sse(
            "error",
            {"message": "Server is busy handling other research requests. Please try again shortly."},
        )
        return

    async with _concurrency_limiter:
        q: "queue.Queue[Any]" = queue.Queue()
        llm_key = req.llm_api_key.get_secret_value()
        tavily_key = req.tavily_api_key.get_secret_value() if req.tavily_api_key else None

        thread = threading.Thread(
            target=_run_research, args=(req, llm_key, tavily_key, q), daemon=True
        )
        thread.start()

        while True:
            item = await asyncio.to_thread(q.get)
            if item is _DONE:
                return
            event, data = item
            yield _sse(event, data)
