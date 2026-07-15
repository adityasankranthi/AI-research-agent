from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Source:
    title: str
    url: str
    content: str


@dataclass
class PlanItem:
    """One independently verifiable requirement in a research task."""

    id: str
    question: str
    section: str
    evidence_requirements: list[str] = field(default_factory=list)
    status: Literal["unresearched", "partial", "supported"] = "unresearched"


@dataclass
class ResearchPlan:
    title: str
    items: list[PlanItem] = field(default_factory=list)
    breadth: Literal["focused", "broad"] = "focused"


@dataclass
class EvidenceItem:
    """A claim retained independently of the prose report that will use it."""

    claim: str
    source_title: str
    source_url: str
    excerpt: str
    plan_item_id: str
    confidence: float = 1.0


@dataclass
class ResearchState:
    """Everything the agent loop reads and writes across iterations.

    State merging across loop iterations is handled explicitly, not inferred from a
    type annotation by a framework: `add_sources()` is called once per iteration by
    the loop itself, so it's always clear exactly where and how the source list grows.
    """

    topic: str
    search_query: str = ""
    running_summary: str = ""
    sources: list[Source] = field(default_factory=list)
    plan: ResearchPlan | None = None
    evidence: list[EvidenceItem] = field(default_factory=list)
    loop_count: int = 0

    def add_sources(self, new_sources: list[Source]) -> None:
        self.sources.extend(new_sources)

    def add_evidence(self, new_evidence: list[EvidenceItem]) -> None:
        """Deduplicate evidence by normalized claim + URL, preserving first-seen order."""
        seen = {(e.claim.strip().lower(), e.source_url) for e in self.evidence}
        for item in new_evidence:
            key = (item.claim.strip().lower(), item.source_url)
            if key not in seen:
                self.evidence.append(item)
                seen.add(key)
