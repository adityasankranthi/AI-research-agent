"""Cheap, deterministic source ordering before expensive page fetches."""

import re
from urllib.parse import urlparse

from research_agent.state import Source

_PRIMARY_SUFFIXES = (".gov", ".gov.uk", ".edu", ".ac.uk", ".int")
_LOW_SIGNAL_HOSTS = (
    "linkedin.com",
    "facebook.com",
    "pinterest.com",
    "quora.com",
    "medium.com",
)
_WORD_RE = re.compile(r"[a-z0-9]{3,}")


def source_score(source: Source, query: str) -> float:
    """Rank authority, relevance, and usable content without another model call."""
    parsed = urlparse(source.url)
    host = parsed.netloc.lower().removeprefix("www.")
    score = 0.0
    if any(host.endswith(suffix) for suffix in _PRIMARY_SUFFIXES):
        score += 4.0
    if host.endswith(".org"):
        score += 1.0
    if any(low_signal in host for low_signal in _LOW_SIGNAL_HOSTS):
        score -= 3.0
    if source.url.lower().endswith(".pdf"):
        score += 1.5
    query_terms = set(_WORD_RE.findall(query.lower()))
    source_terms = set(_WORD_RE.findall(f"{source.title} {source.content}".lower()))
    if query_terms:
        score += 3.0 * len(query_terms & source_terms) / len(query_terms)
    score += min(len(source.content), 4000) / 4000
    return score


def rank_sources(sources: list[Source], query: str) -> list[Source]:
    return sorted(sources, key=lambda source: source_score(source, query), reverse=True)
