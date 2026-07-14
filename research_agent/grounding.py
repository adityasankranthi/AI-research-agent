"""Citation-presence checking: does each claim in a summary cite a URL that's
actually among the sources gathered for it? This is presence-checking, not
content-entailment checking (whether the cited page truly supports the claim) --
a deeper check would need an LLM call per claim, which is out of scope for a
lightweight pass. Because it's URL-match-based, it works identically whether a
source's `.content` came from a search snippet or a fetched full page."""

import re
from dataclasses import dataclass

from research_agent.state import Source

_CITATION_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
# Short/transitional sentences ("In conclusion, ...") aren't claims worth flagging.
_MIN_CLAIM_WORDS = 8


@dataclass
class GroundingResult:
    sentence: str
    cited_urls: list[str]
    grounded: bool


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def extract_cited_urls(sentence: str) -> list[str]:
    return [url for _, url in _CITATION_RE.findall(sentence)]


def check_grounding(summary: str, sources: list[Source]) -> list[GroundingResult]:
    known_urls = {s.url for s in sources}
    results = []
    for sentence in split_sentences(summary):
        if len(sentence.split()) < _MIN_CLAIM_WORDS:
            continue
        cited = extract_cited_urls(sentence)
        results.append(
            GroundingResult(
                sentence=sentence,
                cited_urls=cited,
                grounded=any(url in known_urls for url in cited),
            )
        )
    return results


def annotate_ungrounded(summary: str, results: list[GroundingResult]) -> str:
    ungrounded = [r.sentence for r in results if not r.grounded]
    if not ungrounded:
        return summary
    footer = "\n\n### Unverified claims\n" + "\n".join(f"- {s}" for s in ungrounded)
    return summary + footer
