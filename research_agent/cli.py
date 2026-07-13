import json
from pathlib import Path
from typing import Any, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from research_agent.agent import run
from research_agent.config import Config
from research_agent.factory import build_components
from research_agent.state import ResearchState

load_dotenv()  # picks up provider API keys (OPENROUTER_API_KEY, TAVILY_API_KEY, etc.) from ./.env

app = typer.Typer(add_completion=False)
console = Console()


def _trajectory(state: ResearchState, cost: float, n_calls: int) -> dict[str, Any]:
    return {
        "topic": state.topic,
        "loop_count": state.loop_count,
        "sources": [{"title": s.title, "url": s.url} for s in state.sources],
        "running_summary": state.running_summary,
        "llm_cost": cost,
        "llm_calls": n_calls,
    }


@app.command()
def main(
    topic: str = typer.Option(..., "--topic", help="Research topic to investigate."),
    loops: int = typer.Option(3, "--loops", help="Number of search/summarize/reflect iterations."),
    model: str = typer.Option(
        "ollama/qwen2.5:7b",
        "--model",
        help="litellm model string, e.g. ollama/qwen2.5:7b, openai/gpt-4o-mini, anthropic/claude-haiku-4-5, openrouter/anthropic/claude-haiku-4-5.",
    ),
    api_base: Optional[str] = typer.Option(
        None,
        "--api-base",
        help="Base URL for a local model server (Ollama/LMStudio). Leave unset for hosted API providers.",
    ),
    search_backend: str = typer.Option(
        "duckduckgo",
        "--search-backend",
        help="'duckduckgo' (no key needed) or 'tavily' (needs TAVILY_API_KEY).",
    ),
    max_search_results: int = typer.Option(3, "--max-search-results"),
    output: Optional[Path] = typer.Option(None, "--output", help="Write the final markdown report here."),
    trajectory: Optional[Path] = typer.Option(
        None, "--trajectory", help="Write the full run (state + cost) as JSON here."
    ),
) -> None:
    config = Config.from_env(
        model=model,
        api_base=api_base,
        search_backend=search_backend,
        max_loops=loops,
        max_search_results=max_search_results,
    )
    llm, backend = build_components(config)

    console.print(Panel(topic, title="Researching", style="bold"))

    def on_iteration(i: int, state: ResearchState) -> None:
        console.print(
            f"[cyan]loop {i + 1}/{config.max_loops}[/cyan] "
            f"searched: [italic]{state.search_query}[/italic]  "
            f"(sources so far: {len(state.sources)})"
        )

    state = run(topic=topic, llm=llm, backend=backend, config=config, on_iteration=on_iteration)

    console.print(Panel(state.running_summary, title="Final Report"))
    console.print(f"[dim]{llm.n_calls} LLM calls, ${llm.total_cost:.4f} total cost[/dim]")

    if output:
        output.write_text(state.running_summary)
        console.print(f"[green]report written to {output}[/green]")

    if trajectory:
        trajectory.write_text(
            json.dumps(_trajectory(state, llm.total_cost, llm.n_calls), indent=2)
        )
        console.print(f"[green]trajectory written to {trajectory}[/green]")


if __name__ == "__main__":
    app()
