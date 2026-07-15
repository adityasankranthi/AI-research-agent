"""Adapter that runs this agent over DeepResearch Bench's prompts and writes the
JSONL shape its scoring scripts expect (https://github.com/Ayanami0730/deep_research_bench).

This does NOT vendor or reimplement DeepResearch Bench -- clone that repo
separately, point --query-file at its data/prompt_data/query.jsonl, point
--output at data/test_data/raw_data/<model_name>.jsonl inside that checkout,
then run its own `run_benchmark.sh` (after adding your model name to
TARGET_MODELS) to get RACE + FACT scores. See docs/deepresearch-bench.md.

Submitted articles run with citation-grounding annotation disabled (the
"### Unverified claims" footer is meta-commentary a strict RACE reader could
penalize under readability) -- grounding is instead computed here purely as a
per-task diagnostic ratio logged to the console.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from research_agent.agent import run
from research_agent.config import Config
from research_agent.factory import build_components
from research_agent.grounding import check_grounding

load_dotenv()

app = typer.Typer(add_completion=False)
console = Console()


def _load_queries(
    query_file: Path, language: str, ids: Optional[str]
) -> list[dict[str, Any]]:
    queries = [
        json.loads(line) for line in query_file.read_text().splitlines() if line.strip()
    ]
    if language:
        queries = [q for q in queries if q.get("language") == language]
    if ids:
        wanted = {int(i.strip()) for i in ids.split(",") if i.strip()}
        queries = [q for q in queries if q["id"] in wanted]
    return queries


def _run_one(query: dict[str, Any], config: Config) -> tuple[dict[str, Any], Optional[str], Optional[str]]:
    """Runs one benchmark query end to end. Returns (query, article, error) --
    exactly one of article/error is set. Builds a fresh LLMClient/tools per task,
    same rationale as eval/run_eval.py's _run_case: LLMClient mutates
    total_cost/n_calls on every call, so per-task instances avoid a shared-mutable-
    state race across threads."""
    llm, tools = build_components(config)
    try:
        state = run(topic=query["prompt"], llm=llm, tools=tools, config=config)
    except Exception as e:
        return query, None, str(e)

    grounding_results = check_grounding(state.running_summary, state.sources)
    n_grounded = sum(1 for r in grounding_results if r.grounded)
    console.print(
        f"[cyan]done:[/cyan] id={query['id']} "
        f"(loops={state.loop_count}, sources={len(state.sources)}, "
        f"grounded={n_grounded}/{len(grounding_results)}, "
        f"${llm.total_cost:.4f})"
    )
    return query, state.running_summary, None


@app.command()
def main(
    query_file: Path = typer.Option(
        ..., "--query-file", help="Path to <deep_research_bench checkout>/data/prompt_data/query.jsonl"
    ),
    output: Path = typer.Option(
        ..., "--output", help="Path to write, e.g. <checkout>/data/test_data/raw_data/<model_name>.jsonl"
    ),
    model: str = typer.Option("openrouter/anthropic/claude-haiku-4-5", "--model"),
    api_base: Optional[str] = typer.Option(None, "--api-base"),
    search_backend: str = typer.Option(
        "tavily",
        "--search-backend",
        help="Strongly recommend tavily at 100-task scale -- duckduckgo rate-limits.",
    ),
    loops: int = typer.Option(
        6,
        "--loops",
        help=(
            "A cap, not a target -- Config.allow_early_stop (on by default) lets reflect() "
            "end the loop before this once it judges a task's summary sufficiently "
            "answered. Raising this well above 4 (e.g. to 10-15, as a safety cap while "
            "relying on early-stop to decide the real length) was tried against a stronger "
            "model on a 3-task sample and did not beat this default -- see "
            "docs/deepresearch-bench.md for that comparison. If you raise this, also raise "
            "--max-output-tokens (see below), or reports get compressed rather than deeper."
        ),
    ),
    max_search_results: int = typer.Option(5, "--max-search-results"),
    max_output_tokens: int = typer.Option(
        6144,
        "--max-output-tokens",
        help=(
            "This cap applies to every LLM response including the final summary, so "
            "raising --loops/--max-search-results without also raising this just "
            "compresses more gathered material into the same fixed-length report instead "
            "of producing a deeper one."
        ),
    ),
    fetch_full_page: bool = typer.Option(
        True, "--fetch-full-page/--no-fetch-full-page", help="Fetch full page text for new sources."
    ),
    max_plan_items: int = typer.Option(8, "--max-plan-items"),
    queries_per_loop: int = typer.Option(2, "--queries-per-loop"),
    min_evidence_per_item: int = typer.Option(2, "--min-evidence-per-item"),
    broad_min_loops: int = typer.Option(2, "--broad-min-loops"),
    broad_min_evidence_sources: int = typer.Option(5, "--broad-min-evidence-sources"),
    broad_min_source_domains: int = typer.Option(3, "--broad-min-source-domains"),
    final_revision: bool = typer.Option(
        True,
        "--final-revision/--no-final-revision",
        help="Allow one evidence-constrained reviewer-directed rewrite.",
    ),
    concurrency: int = typer.Option(3, "--concurrency"),
    language: str = typer.Option(
        "en",
        "--language",
        help="'en' or 'zh' to filter, or '' for both. Agent prompts are English-only -- 'en' strongly recommended.",
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Run only the first N matching queries -- use for a cheap smoke test."
    ),
    ids: Optional[str] = typer.Option(
        None, "--ids", help="Comma-separated task ids, e.g. for retrying specific failures."
    ),
) -> None:
    queries = _load_queries(query_file, language, ids)
    if limit:
        queries = queries[:limit]
    if not queries:
        console.print("[red]No queries matched the given filters.[/red]")
        raise typer.Exit(code=1)

    config = Config.from_env(
        model=model,
        api_base=api_base,
        search_backend=search_backend,
        max_loops=loops,
        max_search_results=max_search_results,
        max_output_tokens=max_output_tokens,
        fetch_full_page=fetch_full_page,
        enable_citation_grounding_check=False,
        research_mode="deep",
        max_plan_items=max_plan_items,
        deep_queries_per_loop=queries_per_loop,
        min_evidence_per_plan_item=min_evidence_per_item,
        broad_question_min_loops=broad_min_loops,
        broad_question_min_evidence_sources=broad_min_evidence_sources,
        broad_question_min_source_domains=broad_min_source_domains,
        enable_final_revision=final_revision,
    )

    start = time.monotonic()
    articles: dict[int, str] = {}
    failures: list[tuple[int, str]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(_run_one, q, config) for q in queries]
        for future in as_completed(futures):
            query, article, error = future.result()
            if error:
                failures.append((query["id"], error))
                console.print(f"[red]failed:[/red] id={query['id']}: {error}")
            else:
                articles[query["id"]] = article
    elapsed = time.monotonic() - start

    with output.open("w", encoding="utf-8") as f:
        for q in queries:
            if q["id"] in articles:
                f.write(
                    json.dumps(
                        {"id": q["id"], "prompt": q["prompt"], "article": articles[q["id"]]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    console.print(
        f"[bold]{len(articles)}/{len(queries)} tasks succeeded[/bold] "
        f"({len(failures)} failed) in {elapsed:.1f}s wall-clock, concurrency={concurrency}"
    )
    if failures:
        console.print(f"[red]Failed ids:[/red] {[i for i, _ in failures]}")


if __name__ == "__main__":
    app()
