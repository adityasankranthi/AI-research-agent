# Running against DeepResearch Bench

[DeepResearch Bench](https://github.com/Ayanami0730/deep_research_bench) (Apache-2.0) is
a 100-task benchmark of PhD-level research prompts across 22 domains, scored via **RACE**
(comprehensiveness, insight, instruction-following, readability, judged against a
reference article) and **FACT** (extracts inline citations and verifies each via web
scraping, reporting citation accuracy and effective citations per task).

This repo doesn't vendor DeepResearch Bench -- it's a separate checkout you clone
yourself. `eval/deepresearch_bench.py` (installed as `research-agent-bench`) only
generates the article JSONL that checkout's own scoring scripts expect.

The adapter uses `Config.research_mode="deep"`: it plans task requirements, retains
evidence independently of report prose, searches a portfolio of uncovered requirements,
audits evidence, and writes the report once. The 35.50 RACE / 91.1% FACT numbers in the
README are the preserved pre-planner baseline; do not compare a new run to them without
recording model, loop, search, and output-token settings.

## 1. Clone and set up DeepResearch Bench

```bash
git clone https://github.com/Ayanami0730/deep_research_bench.git
cd deep_research_bench
pip install -r requirements.txt
```

Set the judge/scraping keys it needs (not this repo's `.env` -- these are read by
DeepResearch Bench's own scripts):

```bash
export LLM_BACKEND="openrouter"          # or "openai"
export OPENROUTER_API_KEY="sk-or-v1-..."  # or OPENAI_API_KEY if LLM_BACKEND=openai
export JINA_API_KEY="..."                 # web-scraping for the FACT pipeline
```

## 2. Generate articles with this agent

From this repo, point `--query-file` at the checkout's prompts and `--output` at where
it expects your model's raw data (`<model_name>.jsonl`):

```bash
# Cheap smoke test first -- 3 tasks, sanity-check output before spending the full budget.
uv run research-agent-bench \
  --query-file /path/to/deep_research_bench/data/prompt_data/query.jsonl \
  --output /path/to/deep_research_bench/data/test_data/raw_data/research-agent.jsonl \
  --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily \
  --limit 3

# Full run once the smoke test looks right (~50 English tasks by default; add
# --language "" for all 100, but note this agent's prompts are English-only).
uv run research-agent-bench \
  --query-file /path/to/deep_research_bench/data/prompt_data/query.jsonl \
  --output /path/to/deep_research_bench/data/test_data/raw_data/research-agent.jsonl \
  --model openrouter/anthropic/claude-haiku-4-5 \
  --search-backend tavily
```

The deep adapter currently defaults to a 6-loop safety cap, two targeted queries per
loop, up to eight plan items, two independent source URLs per supported item, a 6,144
token report budget, and one bounded revision pass. Treat these as the first planner
baseline, not proven optimal settings; use the CLI flags to run controlled ablations.

Each task logs a diagnostic citation-grounding ratio (`grounded=N/M`) as it completes --
sourced from the same `research_agent/grounding.py` check the agent itself uses, just
computed here for visibility rather than annotated into the submitted article. A ratio
near 0 across every task would mean something about the citation format broke; expect
most tasks to land well above that.

## 3. Score it

Back in the `deep_research_bench` checkout, add `"research-agent"` to
`run_benchmark.sh`'s `TARGET_MODELS` array, then run:

```bash
bash run_benchmark.sh
```

This runs RACE (`deepresearch_bench_race.py`) and the 5-stage FACT pipeline (extract →
deduplicate → scrape → validate → stat), writing:

- `results/race/research-agent/race_result.txt`
- `results/fact/research-agent/fact_result.txt`

`run_benchmark.sh` has its own commented-out `LIMIT="--limit 3"` line -- uncomment it to
score just the smoke-test subset first, cheaply, before running the full 100-task (or
~50-task English-only) evaluation.

## Notes

- `--search-backend tavily` is the default here specifically because DuckDuckGo starts
  rate-limiting at this scale.
- `--fetch-full-page` defaults on for this adapter (unlike the plain CLI) since fuller
  source content generally means a more comprehensive, better-cited report -- exactly
  what RACE and FACT reward.
- A task whose `run()` raises (e.g. the summarizer's fail-loud error on a genuinely
  broken model response) is logged and its id omitted from the output JSONL rather than
  submitted with an empty article -- DeepResearch Bench's own RACE script already
  reports a missing id explicitly ("Target article not found for ID X"), which is more
  honest than scoring a bad report as if it were real.

## A tuning result worth knowing before you experiment

A 3-task RACE comparison (topics 51-53) tried a stronger model with a much higher loop
cap and search breadth against the defaults below:

| Config | Model | `--loops` cap | `--max-search-results` | `--max-output-tokens` | RACE overall |
|---|---|---|---|---|---|
| Default | claude-haiku-4-5 | 4 | 5 | 2048 | **0.38** |
| Tuned, v1 | claude-sonnet-5 | 12 | 8 | 2048 (unchanged) | 0.25 |
| Tuned, v2 | claude-sonnet-5 | 12 | 8 | 6144 | 0.37 |

The v1 regression traces to `Config.max_output_tokens` being a fixed ceiling on every LLM
call including the final summary -- it doesn't scale with `--loops`, so 12 loops'
worth of gathered material got compressed into the same 2048-token report instead of
producing a deeper one (the v1 articles were literally *shorter*, 305-833 words, than the
default config's 945-1230 words, despite 5-6x more sources). Raising `--max-output-tokens`
to 6144 alongside the higher caps (v2) recovered nearly all of that loss, but still didn't
clearly beat the simple default config on this sample.

**Takeaway:** at n=3 this isn't a statistically meaningful result either way, so treat it
as "no proven win yet" rather than "tuning doesn't work" -- but it is a real, reproducible
warning that raising `--loops`/`--max-search-results` without also raising
`--max-output-tokens` actively hurts report quality. If you want to chase a real
improvement here, a larger sample (10-15+ tasks per config) is needed before the
difference means anything.
