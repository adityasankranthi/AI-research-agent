# research-agent

A provider-agnostic iterative web-research agent. Give it a topic; it loops through
**generate a search query → search the web → summarize findings → reflect on gaps →
repeat** for a configurable number of iterations, then emits a cited markdown report.
Includes a quantitative evaluation harness so changes to prompts, models, or config can
be measured, not just eyeballed.

```
$ research-agent --topic "What is the Model Context Protocol (MCP)?" \
    --model openrouter/anthropic/claude-haiku-4-5 --search-backend tavily --loops 1

loop 1/1 searched: Model Context Protocol MCP what is  (sources so far: 3)

## Summary
The Model Context Protocol (MCP) is an open standard and open-source framework
introduced by Anthropic in November 2024 designed to standardize how artificial
intelligence systems, particularly large language models (LLMs), integrate with and
access external tools, systems, and data sources...

### Sources:
* Model Context Protocol - Wikipedia : https://en.wikipedia.org/wiki/Model_Context_Protocol
* What is Model Context Protocol (MCP)? : https://www.ibm.com/think/topics/model-context-protocol
* What is MCP? The Universal Connector for AI Explained : https://www.backslash.security/blog/...

2 LLM calls, $0.0040 total cost
```

## Goals

This project is built around a few deliberate engineering choices:

- **Full control over agent orchestration.** The research loop, its state, its retry
  behavior, and its structured-output parsing are all plain Python you can read start to
  finish — no orchestration framework hides the control flow.
- **Provider-agnostic by design.** One model string (`ollama/qwen2.5:7b`,
  `openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5`,
  `openrouter/anthropic/claude-haiku-4-5`, ...) carries the provider, so nothing else in
  the codebase branches on which one you're using. Local and hosted models are
  interchangeable at the CLI.
- **Swappable search backends** behind one protocol (`SearchBackend`) — DuckDuckGo (free,
  no key) and Tavily (a real search API, no scraping-related rate limits) ship today;
  adding another is a class, not a rewrite.
- **Defensive engineering, hardened by live testing.** Bounded retries with corrective
  feedback on malformed model output, a fail-loud path when a summary can't be produced
  instead of silently writing a broken report, and a skip path when a search returns no
  results instead of asking a model to summarize nothing.
- **Quantitative evaluation**, not vibes. A small dataset of stable, well-documented
  topics with checkable facts, scored automatically, so a prompt or config change has a
  number attached to it.

## Results

Baseline run against `openrouter/anthropic/claude-haiku-4-5` + Tavily search, 2 research
loops per topic, scored with the free keyword-recall judge (see [Evaluation](#evaluation)
for what that does and doesn't tell you):

| Topic | Facts covered | Loops | Sources |
|---|---|---|---|
| What is the Model Context Protocol (MCP)? | 3/3 | 2 | 6 |
| What is Retrieval-Augmented Generation (RAG)? | 2/3 | 2 | 6 |
| What is the Transformer architecture in machine learning? | 3/3 | 2 | 6 |
| What is Kubernetes? | 2/3 | 2 | 6 |
| What is the HTTP/3 protocol? | 3/3 | 2 | 6 |
| What is Rust's ownership model in programming? | 1/3 | 2 | 6 |

**avg fact coverage: 78%** · avg loops: 2.0 · avg sources: 6.0

**Concurrency:** the eval harness researches all 6 topics in parallel
(`ThreadPoolExecutor`, since each topic is an independent, blocking I/O workload).
Measured on the same dataset/model/backend:

| Concurrency | Wall-clock | 
|---|---|
| 1 (sequential) | 113.3s |
| 3 (default) | 38.4s |

A ~2.95x speedup — close to the theoretical ceiling for 6 equal-length independent tasks
split across 3 workers. Fact-coverage scores vary slightly run-to-run (72% vs. 78% across
these two runs) since model generation isn't deterministic; the wall-clock comparison
used the same everything else.

Full test suite: **100 tests passing**, all mocked at the network boundary
(`litellm.completion`, `DDGS`, `TavilyClient`, `httpx.get`) — no test makes a real network
call, so the suite runs in ~2 seconds and is safe to run constantly.

### DeepResearch Bench

Full run against all 50 English [DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench)
tasks (`openrouter/anthropic/claude-haiku-4-5` + Tavily search, 4 research loops per
topic — see [`docs/deepresearch-bench.md`](docs/deepresearch-bench.md) for the full
methodology and a tuning experiment that didn't pay off):

| RACE dimension | Score |
|---|---|
| Comprehensiveness | 0.34 |
| Insight | 0.34 |
| Instruction Following | 0.37 |
| Readability | 0.38 |
| **Overall** | **0.36** |

| FACT metric | Value |
|---|---|
| Avg. citations per report | 17.98 |
| Avg. valid citations per report | 16.38 |
| **Citation accuracy** | **91.1%** |

**vs. the [public leaderboard](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)**
(same GPT-5.5/GPT-5.4-mini judges as the entries below, so the scoring itself is
apples-to-apples; the coverage isn't -- this run is 50 English tasks with a small, cheap
model, not the full 100-task bilingual set most entries report):

| | RACE overall | Rank | Citation accuracy | Effective citations |
|---|---|---|---|---|
| sonar-reasoning | 37.75 | 41 | 52.6% | 13.4 |
| claude-3-7-sonnet-with-search | 36.63 | 42 | 87.3% | 24.5 |
| sonar-pro | 36.19 | 43 | 79.7% | 16.8 |
| **research-agent (this project)** | **35.50** | **44 / 46** | **91.1%** | **16.4** |
| gemini-2.5-pro-preview-05-06 | 31.90 | 45 | — | — |
| gpt-4o-search-preview | 30.74 | 46 | 86.6% | 5.1 |

Two honest takeaways: RACE overall lands in the bottom quartile -- unsurprising for a
report-comprehensiveness metric judged against PhD-level reference articles, running on
a small, cheap model with no dedicated planning step. But citation accuracy (91.1%) is
the **highest of any entry that reports FACT at all**, beating every frontier-model
deep-research product on the board -- a direct result of the inline-citation +
grounding-check work below. The tradeoff is visible in "effective citations": models like
`gemini-2.5-pro-deepresearch` cite ~10x more sources per report (165 vs. our 16), just
less accurately (78.3%) -- this agent is precise rather than voluminous.

## How these results were achieved

Four architecture changes, each validated against this benchmark rather than assumed:

- **A formal `Tool` abstraction** (`research_agent/tools.py`) standardizing what a
  capability the agent loop can call looks like (name, schema, `run()`), without turning
  the loop itself into a framework -- it still hardcodes *when* to call which tool.
- **A real page-fetch tool** (`research_agent/fetch.py`) replacing a config flag that had
  quietly done nothing since it was added -- sources now carry full page text instead of
  a short search snippet when enabled.
- **Inline citations + a citation-grounding check** (`research_agent/grounding.py`): the
  summarizer now cites claims inline as `[Title](URL)` instead of only listing sources in
  a trailing bibliography. This wasn't a cosmetic change -- DeepResearch Bench's own FACT
  pipeline only extracts citations that appear next to the claim in the body text; without
  this, FACT would have scored this agent's reports at 0% citation accuracy regardless of
  everything else.
- **Dynamic early-stop reflection**: the reflect step can now end the research loop before
  `--loops` is reached once it judges a topic sufficiently covered. The first version of
  this never actually fired in live testing -- the prompt's own wording ("identify a
  knowledge gap") biased the model toward always finding one. Rewriting it to judge
  sufficiency *first* fixed this: confirmed live at 1/5 loops on a trivial factual
  question and the full 4/4 on a genuinely broad one.

One tuning path was tried and explicitly **didn't** make it into the defaults: raising
`--loops` and `--max-search-results` for the benchmark run initially made reports *worse*
(RACE overall 0.25 vs. 0.38 baseline) because `max_output_tokens` is a fixed ceiling on
every LLM call -- more gathered material just got compressed into the same report length
instead of a deeper one. Raising the output budget alongside it recovered most of the
loss but still didn't clearly beat the simple baseline at the sample size tested. Full
writeup, including the exact before/after numbers, in
[`docs/deepresearch-bench.md`](docs/deepresearch-bench.md).

## Requirements

- Python ≥ 3.10
- [uv](https://github.com/astral-sh/uv) for dependency management
- A local model server (e.g. [Ollama](https://ollama.com)) and/or an API key for a hosted
  provider (OpenAI, Anthropic, OpenRouter, ...)
- Optionally, a free [Tavily](https://tavily.com) API key for the more reliable search
  backend

## Install

```bash
git clone <this-repo-url>
cd research-agent
uv sync --extra dev
cp .env.example .env   # fill in whichever provider/search keys you plan to use
```

## Usage

### Research a topic

```bash
# Local model via Ollama (default) -- no API key needed
uv run research-agent --topic "your research topic" --model ollama/qwen2.5:7b

# Hosted model, real search backend
uv run research-agent --topic "your research topic" \
  --model openrouter/anthropic/claude-haiku-4-5 --search-backend tavily
```

| Flag | Default | Description |
|---|---|---|
| `--topic` | *(required)* | Research topic to investigate |
| `--loops` | `3` | Number of search/summarize/reflect iterations |
| `--model` | `ollama/qwen2.5:7b` | Any [litellm](https://docs.litellm.ai/docs/providers) model string |
| `--api-base` | *(unset)* | Base URL for a local model server; leave unset for hosted providers |
| `--search-backend` | `duckduckgo` | `duckduckgo` (no key) or `tavily` (needs `TAVILY_API_KEY`) |
| `--max-search-results` | `3` | Results fetched per search |
| `--output` | *(unset)* | Write the final markdown report to this path |
| `--trajectory` | *(unset)* | Write the full run (state + cost) as JSON to this path |

Every `Config` field is also settable via a `RESEARCH_AGENT_<FIELD_NAME>` environment
variable (e.g. `RESEARCH_AGENT_MAX_LOOPS=5`), read from `.env` automatically.

### Evaluation

```bash
# Free, no extra LLM calls -- keyword-overlap heuristic
uv run research-agent-eval --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily --judge keyword

# More rigorous -- a second model grades the summaries
uv run research-agent-eval --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily --judge llm --judge-model anthropic/claude-sonnet-5
```

`--judge keyword` scores fact coverage by checking whether enough of a fact's
significant keywords appear in the summary — free, instant, but can't tell a real
paraphrase from coincidental word overlap. `--judge llm` asks a second model (by design,
a different one than `--model`, so it isn't grading its own work) whether each fact is
actually supported.

| Flag | Default | Description |
|---|---|---|
| `--model` | `ollama/qwen2.5:7b` | Model under test |
| `--search-backend` | `duckduckgo` | Search backend to use |
| `--loops` | `2` | Research loops per topic |
| `--judge` | `llm` | `llm` or `keyword` |
| `--judge-model` | `openrouter/anthropic/claude-haiku-4-5` | Model used when `--judge llm` |
| `--concurrency` | `3` | Topics researched in parallel |

### DeepResearch Bench

Beyond this repo's own small eval dataset, the agent can also be scored against
[DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench) -- 100
PhD-level research tasks judged on report comprehensiveness, insight, and citation
trustworthiness. `research-agent-bench` generates the article JSONL that benchmark's
scoring scripts expect; see [`docs/deepresearch-bench.md`](docs/deepresearch-bench.md)
for the full two-repo workflow.

### Tests

```bash
uv run pytest -v
```

## Project structure

```
research_agent/
├── state.py       # ResearchState, Source -- the data the loop reads and writes
├── config.py       # Config -- every runtime knob, env-var resolution
├── llm.py           # LLMClient -- one interface to every model provider
├── search.py         # SearchBackend protocol + DuckDuckGo/Tavily implementations
├── prompts.py         # System prompts + tool schemas for each LLM call
├── agent.py            # The research loop itself
├── factory.py           # Shared component wiring for the CLI and eval runner
└── cli.py                 # research-agent entry point

eval/
├── dataset.py       # Topics with checkable key facts
├── judge.py           # KeywordRecallJudge / LLMJudge
└── run_eval.py          # research-agent-eval entry point

tests/                       # One test file per module above, all network-mocked
```

## License

MIT — see [LICENSE](LICENSE).
