import re
from dataclasses import dataclass
from typing import Protocol

from research_agent.llm import LLMClient


@dataclass
class FactResult:
    fact: str
    covered: bool


class Judge(Protocol):
    def score_facts(self, summary: str, key_facts: list[str]) -> list[FactResult]: ...


_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "to", "and", "or", "in", "on",
    "for", "with", "by", "as", "that", "this", "it", "its", "be", "has", "have", "not",
    "than", "using", "used", "use", "into", "from", "which", "such", "at", "but",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


class KeywordRecallJudge:
    """No LLM call -- cheap, deterministic, free to run on every iteration.

    Considers a fact "covered" if at least `threshold` of its significant
    (non-stopword) keywords appear anywhere in the summary. Coarser than an LLM
    judge -- it can't tell a real paraphrase from coincidental word overlap -- but
    that coarseness is the point: a quick sanity signal with zero cost or latency.
    """

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = threshold

    def score_facts(self, summary: str, key_facts: list[str]) -> list[FactResult]:
        summary_keywords = _keywords(summary)
        results = []
        for fact in key_facts:
            fact_keywords = _keywords(fact)
            covered = bool(fact_keywords) and (
                len(fact_keywords & summary_keywords) / len(fact_keywords) >= self.threshold
            )
            results.append(FactResult(fact=fact, covered=covered))
        return results


FACT_CHECK_TOOL = {
    "type": "function",
    "function": {
        "name": "report_fact_coverage",
        "description": "Report whether each numbered fact is supported by the summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "covered": {
                    "type": "array",
                    "items": {"type": "boolean"},
                    "description": (
                        "One boolean per fact, in the same order as listed, true if the "
                        "summary directly states or clearly implies that fact."
                    ),
                }
            },
            "required": ["covered"],
        },
    },
}

JUDGE_SYSTEM_PROMPT = (
    "You are a strict fact-checker. Given a summary and a numbered list of facts, "
    "determine which facts the summary actually supports -- not facts that are "
    "merely plausible or related, only ones the summary's content directly states "
    "or clearly implies. Call the report_fact_coverage tool with your answer."
)


class LLMJudge:
    """Reuses LLMClient's existing structured-output path (chat_with_tool) -- no new
    LLM-calling machinery, the same tool-calling-with-fallback mechanics the agent
    itself uses."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def score_facts(self, summary: str, key_facts: list[str]) -> list[FactResult]:
        numbered_facts = "\n".join(f"{i + 1}. {fact}" for i, fact in enumerate(key_facts))
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Summary:\n{summary}\n\nFacts:\n{numbered_facts}"},
        ]
        args = self.llm.chat_with_tool(messages, tool=FACT_CHECK_TOOL)
        covered = (args or {}).get("covered") or []

        results = []
        for i, fact in enumerate(key_facts):
            # A model that returns the wrong-length array (uncooperative or
            # malformed) degrades to "not covered" for the missing tail rather than
            # raising -- one bad judge call shouldn't crash an entire eval run.
            is_covered = bool(covered[i]) if i < len(covered) else False
            results.append(FactResult(fact=fact, covered=is_covered))
        return results
