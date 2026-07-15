"""Mechanical postconditions for citations in deep-research reports."""

import re
from dataclasses import dataclass

from research_agent.state import EvidenceItem, ResearchState

_CITATION_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


@dataclass(frozen=True)
class CitationCompliance:
    cited_urls: list[str]
    unknown_urls: list[str]
    required_plan_item_ids: list[str]
    missing_plan_item_ids: list[str]

    @property
    def compliant(self) -> bool:
        return not self.unknown_urls and not self.missing_plan_item_ids


def check_citation_compliance(report: str, state: ResearchState) -> CitationCompliance:
    cited_urls = [url for _, url in _CITATION_RE.findall(report)]
    known_urls = {item.source_url for item in state.evidence}
    evidence_by_plan: dict[str, set[str]] = {}
    for item in state.evidence:
        evidence_by_plan.setdefault(item.plan_item_id, set()).add(item.source_url)
    required_ids = sorted(evidence_by_plan)
    cited_set = set(cited_urls)
    missing_ids = [
        item_id for item_id in required_ids if not (evidence_by_plan[item_id] & cited_set)
    ]
    return CitationCompliance(
        cited_urls=cited_urls,
        unknown_urls=sorted({url for url in cited_urls if url not in known_urls}),
        required_plan_item_ids=required_ids,
        missing_plan_item_ids=missing_ids,
    )


def remove_unknown_citations(report: str, known_urls: set[str]) -> str:
    """Preserve link text while removing a citation URL the agent never gathered."""

    def replace(match: re.Match[str]) -> str:
        label, url = match.groups()
        return match.group(0) if url in known_urls else label

    return _CITATION_RE.sub(replace, report)


def append_missing_evidence_notes(
    report: str,
    state: ResearchState,
    missing_plan_item_ids: list[str],
) -> str:
    """Deterministic last resort: add supported claim/citation pairs for missing sections."""
    if not missing_plan_item_ids or state.plan is None:
        return report
    sections = {item.id: item.section for item in state.plan.items}
    blocks: list[str] = []
    for item_id in missing_plan_item_ids:
        evidence = [item for item in state.evidence if item.plan_item_id == item_id][:2]
        if not evidence:
            continue
        bullets = "\n".join(
            f"- {item.claim} [{item.source_title}]({item.source_url})" for item in evidence
        )
        blocks.append(f"### Verified evidence: {sections.get(item_id, item_id)}\n{bullets}")
    return report + ("\n\n## Evidence notes\n\n" + "\n\n".join(blocks) if blocks else "")
