import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from eval.dataset import DATASET, EvalCase
from eval.judge import Judge, KeywordRecallJudge, LLMJudge
from research_agent.agent import run
from research_agent.config import Config
from research_agent.factory import build_components
from research_agent.llm import LLMClient

load_dotenv()

app = typer.Typer(add_completion=False)
console = Console()


@dataclass
class CaseReport:
    topic: str
    n_facts: int
    n_covered: int
    loop_count: int
    n_sources: int

    @property
    def score(self) -> float:
        return self.n_covered / self.n_facts if self.n_facts else 0.0


def _build_judge(judge_kind: str, judge_model: str) -> Judge:
    if judge_kind == "keyword":
        return KeywordRecallJudge()
    return LLMJudge(LLMClient(model=judge_model, max_tokens=512))


def _run_case(
    index: int, case: EvalCase, config: Config, judge_kind: str, judge_model: str
) -> tuple[int, CaseReport]:
    """Runs one dataset case end to end. Builds its own LLMClient and judge rather
    than sharing one across threads -- LLMClient mutates total_cost/n_calls on every
    call, and per-task instances avoid that shared-mutable-state race entirely
    instead of adding lock complexity. Both are plain dataclasses, cheap to build."""
    llm, tools = build_components(config)
    state = run(topic=case.topic, llm=llm, tools=tools, config=config)

    fact_judge = _build_judge(judge_kind, judge_model)
    fact_results = fact_judge.score_facts(state.running_summary, case.key_facts)

    report = CaseReport(
        topic=case.topic,
        n_facts=len(case.key_facts),
        n_covered=sum(1 for f in fact_results if f.covered),
        loop_count=state.loop_count,
        n_sources=len(state.sources),
    )
    return index, report


@app.command()
def main(
    model: str = typer.Option("ollama/qwen2.5:7b", "--model", help="Model under test."),
    api_base: Optional[str] = typer.Option(None, "--api-base"),
    search_backend: str = typer.Option("duckduckgo", "--search-backend"),
    loops: int = typer.Option(
        2,
        "--loops",
        help="Research loops per case -- kept low; this runs the full agent once per topic.",
    ),
    judge: str = typer.Option(
        "llm", "--judge", help="'llm' (uses --judge-model) or 'keyword' (free, no LLM call)."
    ),
    judge_model: str = typer.Option(
        "openrouter/anthropic/claude-haiku-4-5",
        "--judge-model",
        help=(
            "Only used when --judge llm. Deliberately independent of --model, so the "
            "judge isn't grading its own work."
        ),
    ),
    concurrency: int = typer.Option(
        3,
        "--concurrency",
        help=(
            "How many dataset topics to research in parallel -- each is an independent, "
            "blocking I/O workload (LLM + search calls), a textbook case for concurrency. "
            "Note: with --search-backend duckduckgo, higher concurrency increases the "
            "chance of hitting that backend's rate limit; --search-backend tavily doesn't "
            "have this issue."
        ),
    ),
) -> None:
    config = Config.from_env(
        model=model, api_base=api_base, search_backend=search_backend, max_loops=loops
    )

    start = time.monotonic()
    reports: list[Optional[CaseReport]] = [None] * len(DATASET)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_run_case, i, case, config, judge, judge_model)
            for i, case in enumerate(DATASET)
        ]
        for future in as_completed(futures):
            index, report = future.result()
            reports[index] = report
            console.print(f"[cyan]done:[/cyan] {report.topic}")
    elapsed = time.monotonic() - start

    table = Table(title=f"Eval results -- model={config.model}, judge={judge}")
    table.add_column("Topic")
    table.add_column("Facts covered")
    table.add_column("Loops")
    table.add_column("Sources")
    for r in reports:
        assert r is not None
        table.add_row(r.topic, f"{r.n_covered}/{r.n_facts}", str(r.loop_count), str(r.n_sources))
    console.print(table)

    avg_score = statistics.mean(r.score for r in reports) if reports else 0.0
    avg_loops = statistics.mean(r.loop_count for r in reports) if reports else 0.0
    avg_sources = statistics.mean(r.n_sources for r in reports) if reports else 0.0
    console.print(
        f"[bold]avg fact coverage: {avg_score:.0%}[/bold]  "
        f"avg loops: {avg_loops:.1f}  avg sources: {avg_sources:.1f}  "
        f"[dim]({elapsed:.1f}s wall-clock, concurrency={concurrency})[/dim]"
    )


if __name__ == "__main__":
    app()
