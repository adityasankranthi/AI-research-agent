# Evidence-First AI Research Agent

[![CI](https://github.com/adityasankranthi/AI-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/adityasankranthi/AI-research-agent/actions/workflows/ci.yml)
![Paired RACE gain](https://img.shields.io/badge/paired_RACE_gain-%2B15.7%25-2ea44f)
![FACT citation accuracy](https://img.shields.io/badge/FACT_citation_accuracy-91.1%25-0969da)
[![Live DeepResearch Bench](https://img.shields.io/badge/DeepResearch_Bench-live_leaderboard-FFD21E)](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)

An AI web-research agent that plans what to investigate, searches for independent
support, preserves claims as atomic evidence, audits coverage, and writes a cited report
only when the evidence is ready.

This project was built from scratch in plain Python—without an agent orchestration
framework—and improved through measured experiments on
[DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench), a real external
benchmark of PhD-level research tasks.

The agent can:

- turn an open-ended question into a coverage plan;
- generate targeted search portfolios instead of one generic query;
- rank, fetch, deduplicate, and retain evidence from multiple sources;
- enforce minimum evidence breadth before broad research can stop;
- synthesize the report once, after research, to avoid summary-of-summary information loss;
- repair or remove citations that fail deterministic compliance checks; and
- run with hosted AI models or locally through Ollama.

## Results

The central result is an engineering result: **changing the agent architecture improved
quality more reliably than changing to a larger model.**

| Experiment | Evaluation scope | Measured result |
|---|---:|---:|
| Citation-precision baseline | 50 English benchmark tasks | **91.1% FACT citation accuracy** |
| Evidence-first architecture | Fixed 12-task paired set | **37.29 → 43.15 RACE** |
| Broad-question stopping rule | Official task-56 evaluation | **45.74 → 49.57 RACE** |
| Breadth-aware citation validation | Official task-56 FACT evaluation | **100% accuracy, 18 effective citations** |
| Automated regression suite | Mocked model, search, fetch, and API boundaries | **127 tests passing** |

On the fixed development set, planning, atomic evidence, and write-once synthesis raised
RACE by **5.86 points / 15.7%** with the same
`openrouter/anthropic/claude-haiku-4-5` model and Tavily search backend.

### How this compares with the live leaderboard

[Open the live DeepResearch Bench leaderboard →](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)

*Comparison checked 15 July 2026 against leaderboard data updated 28 June 2026.*

DeepResearch Bench now maintains a new GPT-5.5-evaluated leaderboard and a legacy
Gemini-2.5-evaluated leaderboard. This project's saved results were produced with the
legacy evaluator, so only the legacy score band is relevant—and a development subset
cannot be treated as an official full-benchmark rank.

| Comparison | RACE | What can be concluded |
|---|---:|---|
| Current legacy leaderboard top-10 cutoff | **56.23** | Full leaderboard result |
| Current legacy rank 26 | **49.71** | Full leaderboard result |
| **This agent: strongest task-56 run** | **49.57** | Numerically between legacy ranks 26 and 27; single-task score only |
| Current legacy rank 27 | **49.33** | Full leaderboard result |
| **This agent: paired development average** | **43.15** | 12-task engineering result; not rank-eligible |

The strongest task result is **6.66 RACE points below the current legacy top-10 cutoff**
and sits inside the score band of published deep-research systems. That is encouraging
evidence, not a claimed rank: an official position requires a full submission evaluated
under one consistent judge version.

Citation precision is the standout result at larger scale. In the public leaderboard
snapshot used during the experiment, this agent's **91.1% FACT citation accuracy** was
higher than every reported result; the next highest was 87.3%. Because our run contains
the 50 English tasks rather than the complete bilingual suite, this remains a precision
comparison—not an official leaderboard placement.

> **Scope, stated plainly:** 35.50 RACE / 91.1% FACT is a 50-English-task pre-planner
> baseline; 43.15 is a paired 12-task development result; and 49.57 RACE / 100% FACT is
> a single-task ablation. The raw artifacts are committed for inspection, but none is
> presented as a full leaderboard submission.

### A bigger model did not produce the improvement

Before redesigning the pipeline, a three-task ablation tested Claude Sonnet with much
larger retrieval limits. It did not beat the simpler Haiku configuration.

| Configuration | Model | Loop cap | Results/query | Output budget | RACE (0–1) |
|---|---|---:|---:|---:|---:|
| Default | Claude Haiku 4.5 | 4 | 5 | 2,048 | **0.38** |
| More model + more retrieval | Claude Sonnet 5 | 12 | 8 | 2,048 | 0.25 |
| More model + matched output budget | Claude Sonnet 5 | 12 | 8 | 6,144 | 0.37 |

The first Sonnet run gathered far more material but compressed it into the same
2,048-token report ceiling. Its reports became shorter—305–833 words versus 945–1,230
for the default—and RACE fell. Raising the report budget recovered the loss, but still
did not establish a win over Haiku.

This was only an n=3 ablation, so it does not prove that smaller models are generally
better. It proves something more useful for this project: **model scale cannot compensate
for a mismatched research and synthesis pipeline.** The repeatable 12-task improvement
came from architecture while the model stayed fixed.

## How we improved report quality

### 1. Planning and atomic evidence improved every RACE dimension

The same 12 prompts (DeepResearch Bench IDs 51–62), model, search backend, and official
judge were used before and after replacing the iterative summary-rewrite loop with the
evidence-first pipeline.

| RACE dimension | Iterative pipeline | Evidence-first pipeline | Gain |
|---|---:|---:|---:|
| Comprehensiveness | 36.86 | **41.76** | +4.90 |
| Insight | 36.27 | **42.54** | +6.27 |
| Instruction following | 39.02 | **44.23** | +5.20 |
| Readability | 38.40 | **45.47** | +7.07 |
| **Overall** | **37.29** | **43.15** | **+5.86** |

The agent now stores source-backed claims rather than repeatedly rewriting a running
summary. It audits the evidence and synthesizes once at the end. The largest gain was
readability—even though the final reports retained more evidence—because useful detail
was no longer degraded through repeated compression.

### 2. Minimum evidence breadth fixed premature stopping

Task 56 asks for a general method for solving asymmetric first-price auctions. The first
deep version considered one supported plan item sufficient and stopped after one loop.
The revised agent classified the question as broad and required at least two loops, five
retained evidence URLs, and three source domains before early stopping was allowed.

| Task-56 metric | Citation-compliant one-loop run | Breadth-aware run |
|---|---:|---:|
| Research loops | 1 | **2** |
| Gathered sources | 9 | **19** |
| Report words | 529 | **1,496** |
| Inline citations | 3 | **20** |
| Unique cited URLs | 3 | **10** |
| Cited domains | 2 | **10** |
| Agent cost | $0.0234 | $0.0804 |
| Official RACE | 45.74 | **49.57** |

The breadth-aware report also beat the original deep task-56 score of 47.53. Official
FACT extracted 21 citation instances across 11 URLs: all **18 evaluable citations were
supported**, while three were marked unknown and excluded by the benchmark. The result
was **100% citation accuracy and 18.0 effective citations**.

### 3. Citation precision was strong before report depth was strong

The original iterative AI agent completed all 50 English tasks with:

| Metric | Result |
|---|---:|
| RACE overall | 35.50 |
| Average citations per report | 17.98 |
| Effective citations per report | 16.38 |
| **FACT citation accuracy** | **91.1%** |

That result exposed the real bottleneck. The agent could cite accurately, but accurate
citations alone did not guarantee comprehensive, insightful research. The new planner,
evidence store, coverage audit, breadth rules, and final citation postcondition were
built to improve the missing depth without giving up precision.

Raw evidence is available in [`benchmark_results/`](benchmark_results/), including the
[12-task RACE output](benchmark_results/deep-dev-12-race.jsonl),
[task-56 combined metrics](benchmark_results/deep-dev-56-breadth-metrics.json), and
[official FACT output](benchmark_results/deep-dev-56-breadth-fact/fact_result.txt).

## What the experiments taught us

- **Store evidence, not evolving prose.** Atomic claims survive many search rounds;
  repeatedly rewriting a report discards detail and compounds summarization errors.
- **Coverage needs a mechanical definition.** Every plan item needs independent support
  before it can be considered researched.
- **Broad questions need global breadth constraints.** Plan-item completion can be
  fooled by an under-decomposed plan, so broad tasks also require multiple loops, URLs,
  and source domains.
- **Citation quality should be a postcondition.** The final report is checked for unknown
  URLs and evidenced plan items that were never cited. One bounded repair is allowed,
  followed by a deterministic fallback.
- **Retrieval, context, and output budgets must scale together.** More loops and sources
  hurt quality when the final report budget remained fixed.
- **Benchmark the system, not just the model.** Keeping the model fixed made it possible
  to attribute the 15.7% gain to agent design rather than model substitution.

The complete methodology, failed experiments, and reproducible commands are documented
in [`docs/deepresearch-bench.md`](docs/deepresearch-bench.md).

## Architecture

```mermaid
flowchart LR
    A["Research request"] --> B["Coverage plan + breadth classification"]
    B --> C["Targeted query portfolio"]
    C --> D["Search, rank, and fetch sources"]
    D --> E["Atomic evidence store"]
    E --> F{"Coverage and breadth satisfied?"}
    F -- "No" --> C
    F -- "Yes or loop cap" --> G["Evidence audit"]
    G --> H["Write report once"]
    H --> I["Bounded review and revision"]
    I --> J["Citation compliance postcondition"]
    J --> K["Final cited report"]
```

The project keeps two modes behind the same model and tool interfaces, making controlled
experiments possible:

| Mode | Design | Best use |
|---|---|---|
| `iterative` | Query → search → summarize → reflect | Fast, lower-cost research |
| `deep` | Plan → evidence → audit → write → citation check | Benchmark-quality reports |

## Try it yourself

Requires Python 3.10+ and [`uv`](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/adityasankranthi/AI-research-agent.git
cd AI-research-agent
uv sync --extra dev
cp .env.example .env
```

### Run the AI agent locally without API keys

With [Ollama](https://ollama.com/) installed and running, use a local model and
DuckDuckGo search:

```bash
ollama pull qwen2.5:7b

uv run research-agent \
  --topic "What are the strongest approaches to scalable ion-trap quantum computing?" \
  --model ollama/qwen2.5:7b \
  --research-mode deep
```

### Try the Web UI

The FastAPI + React interface runs the same agent and streams planning, search, and
report progress with Server-Sent Events.

```bash
# Terminal 1 — API
uv run uvicorn api.main:app --reload --port 8000

# Terminal 2 — UI
cd web
npm install
npm run dev
```

Open `http://localhost:5173`, open **Settings**, and provide the model-provider and
search keys required by your selected configuration. Keys remain in browser local
storage and are passed through only for the active request; the server does not persist
them.

| Ask a question | Watch the research | Inspect the cited report |
|---|---|---|
| ![Idle screen](docs/images/idle.png) | ![Live research progress](docs/images/researching.png) | ![Final cited report](docs/images/result.png) |

<details>
<summary><strong>Hosted-model example and CLI options</strong></summary>

```bash
uv run research-agent \
  --topic "Compare the evidence for the leading approaches to this problem" \
  --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily \
  --research-mode deep \
  --fetch-full-page \
  --output report.md \
  --trajectory trajectory.json
```

| Flag | Default | Description |
|---|---|---|
| `--topic` | required | Research request |
| `--research-mode` | `iterative` | `iterative` or `deep` |
| `--model` | `ollama/qwen2.5:7b` | Any LiteLLM-compatible model string |
| `--search-backend` | `duckduckgo` | `duckduckgo` or `tavily` |
| `--loops` | `3` | Research-loop safety cap |
| `--max-search-results` | `3` | Search results retained per query |
| `--fetch-full-page` | off | Replace snippets with fetched page text |
| `--output` | unset | Write the final Markdown report |
| `--trajectory` | unset | Write state, evidence, sources, calls, and cost |

Every `Config` field is also available as a
`RESEARCH_AGENT_<FIELD_NAME>` environment variable. Broad-task thresholds default to
two loops, five evidence URLs, and three source domains.

</details>

<details>
<summary><strong>Production build and Docker</strong></summary>

```bash
cd web && npm ci && npm run build
cd ..
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Or run the multi-stage container:

```bash
docker build -t research-agent .
docker run -p 8000:8000 research-agent
```

</details>

## Evaluation and reproducibility

<details>
<summary><strong>Tests, internal evaluation, and DeepResearch Bench workflow</strong></summary>

### Fast regression suite

```bash
uv run pytest -q
```

**127 tests pass** with model, search, fetch, and API boundaries mocked. The suite takes
about two seconds and makes no live network calls.

### Internal evaluation

```bash
uv run research-agent-eval \
  --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily \
  --judge keyword
```

The six-topic internal set is a cheap regression signal. Use `--judge llm` with a
separate judge model for semantic grading.

### DeepResearch Bench

The adapter writes the JSONL format expected by the upstream benchmark:

```bash
uv run research-agent-bench \
  --query-file /path/to/deep_research_bench/data/prompt_data/query.jsonl \
  --output /path/to/deep_research_bench/data/test_data/raw_data/research-agent.jsonl \
  --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily \
  --ids 51,52,53,54,55,56,57,58,59,60,61,62 \
  --concurrency 3
```

Scoring remains in the benchmark's own repository so RACE and FACT are neither
reimplemented nor approximated here. See the
[benchmark guide](docs/deepresearch-bench.md) for the complete two-repository workflow.

</details>

## Project structure

```text
research_agent/
├── agent.py                 # Mode dispatch and iterative research loop
├── deep_research.py         # Coverage-driven evidence-first pipeline
├── deep_prompts.py          # Planner, query, evidence, audit, and review schemas
├── citation_compliance.py   # Final citation postcondition and repair
├── source_quality.py        # Deterministic authority and relevance ranking
├── state.py                 # Plans, evidence, sources, and research state
├── llm.py                   # Provider-independent AI model client
├── search.py                # DuckDuckGo and Tavily backends
├── fetch.py                 # Full-page extraction
├── grounding.py             # Gathered-source citation checks
├── config.py                # Runtime knobs and environment resolution
└── cli.py                   # research-agent command

eval/
├── run_eval.py              # Internal evaluation harness
└── deepresearch_bench.py    # DeepResearch Bench adapter

api/                         # FastAPI + SSE backend
web/                         # React + Vite frontend
tests/                       # Network-mocked test suite
benchmark_results/           # Raw measured outputs committed for inspection
```

## Acknowledgments

This project uses **DeepResearch Bench**, created by Mingxuan Du, Benfeng Xu, Chiwei
Zhu, Xiaorui Wang, and Zhendong Mao. Their open benchmark, expert-written task set, and
RACE/FACT evaluation pipeline made it possible to test this AI agent against an external
standard instead of relying on subjective demos.

- [DeepResearch Bench repository](https://github.com/Ayanami0730/deep_research_bench)
- [Paper: *DeepResearch Bench: A Comprehensive Benchmark for Deep Research Agents*](https://arxiv.org/abs/2506.11763)
- [Live leaderboard](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard)

If you use this project's benchmark artifacts, please also cite the DeepResearch Bench
paper as requested by its authors.

## License

MIT — see [LICENSE](LICENSE).
