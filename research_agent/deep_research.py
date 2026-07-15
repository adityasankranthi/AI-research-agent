"""Coverage-driven research pipeline: plan -> evidence -> report.

Unlike the lightweight iterative loop, this pipeline never rewrites an evolving report.
It retains atomic evidence across searches and synthesizes prose once at the end, avoiding
the lossy compression observed when many loops repeatedly summarize prior summaries.
"""

import re
from typing import Callable, Optional
from urllib.parse import urlparse

from research_agent.config import Config
from research_agent.citation_compliance import (
    append_missing_evidence_notes,
    check_citation_compliance,
    remove_unknown_citations,
)
from research_agent.deep_prompts import (
    AUDIT_SYSTEM_PROMPT,
    AUDIT_TOOL,
    CITATION_REPAIR_SYSTEM_PROMPT,
    EVIDENCE_SYSTEM_PROMPT,
    EVIDENCE_TOOL,
    PLAN_SYSTEM_PROMPT,
    PLAN_TOOL,
    QUERY_SYSTEM_PROMPT,
    QUERY_TOOL,
    REPORT_SYSTEM_PROMPT,
    REVIEW_SYSTEM_PROMPT,
    REVIEW_TOOL,
    REVISION_SYSTEM_PROMPT,
)
from research_agent.llm import LLMClient
from research_agent.search import dedupe_sources, format_citations, format_for_context
from research_agent.state import EvidenceItem, PlanItem, ResearchPlan, ResearchState, Source
from research_agent.source_quality import rank_sources
from research_agent.tools import Tool


def create_plan(llm: LLMClient, topic: str, max_items: int) -> ResearchPlan:
    args = llm.chat_with_tool(
        [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": topic},
        ],
        PLAN_TOOL,
    ) or {}
    raw_items = args.get("items") or []
    items: list[PlanItem] = []
    used_ids: set[str] = set()
    for index, raw in enumerate(raw_items[:max_items]):
        if not isinstance(raw, dict):
            continue
        question = str(raw.get("question", "")).strip()
        if not question:
            continue
        item_id = str(raw.get("id") or f"item_{index + 1}").strip()
        if item_id in used_ids:
            item_id = f"{item_id}_{index + 1}"
        used_ids.add(item_id)
        items.append(
            PlanItem(
                id=item_id,
                question=question,
                section=str(raw.get("section") or question).strip(),
                evidence_requirements=[str(x) for x in raw.get("evidence_requirements", [])],
            )
        )
    if not items:
        items = [PlanItem(id="core_answer", question=topic, section="Findings")]
    raw_breadth = str(args.get("breadth") or "").strip().lower()
    breadth = "broad" if raw_breadth == "broad" or _looks_broad(topic) else "focused"
    return ResearchPlan(title=str(args.get("title") or topic), items=items, breadth=breadth)


def _looks_broad(topic: str) -> bool:
    """Conservative fallback when a model omits or under-classifies plan breadth."""
    markers = (
        r"\bgeneral method\b",
        r"\bcompare\b|\bcomparison\b|\bversus\b|\bvs\.?\b",
        r"\boverview\b|\blandscape\b|\bstate of (?:the )?art\b",
        r"\bpros and cons\b|\badvantages and disadvantages\b",
        r"\bmultiple (?:approaches|perspectives|methods|factors)\b",
        r"\btrends?\b.*\b(?:over time|across|between)\b",
    )
    normalized = " ".join(topic.lower().split())
    return any(re.search(marker, normalized) for marker in markers)


def _plan_context(plan: ResearchPlan, evidence: list[EvidenceItem]) -> str:
    urls: dict[str, set[str]] = {}
    for item in evidence:
        urls.setdefault(item.plan_item_id, set()).add(item.source_url)
    return "\n".join(
        f"- {item.id} [{item.status}; {len(urls.get(item.id, set()))} independent sources]: "
        f"{item.question} | needs: {', '.join(item.evidence_requirements) or 'reliable evidence'}"
        for item in plan.items
    )


def update_coverage(plan: ResearchPlan, evidence: list[EvidenceItem], minimum: int) -> None:
    urls: dict[str, set[str]] = {}
    for item in evidence:
        urls.setdefault(item.plan_item_id, set()).add(item.source_url)
    for item in plan.items:
        count = len(urls.get(item.id, set()))
        item.status = "supported" if count >= minimum else "partial" if count else "unresearched"


def plan_complete(plan: ResearchPlan) -> bool:
    return bool(plan.items) and all(item.status == "supported" for item in plan.items)


def _source_domain(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname[4:] if hostname.startswith("www.") else hostname


def breadth_requirements_met(
    plan: ResearchPlan,
    evidence: list[EvidenceItem],
    loop_count: int,
    config: Config,
) -> bool:
    """Return whether global evidence breadth permits an early stop."""
    if plan.breadth != "broad":
        return True
    urls = {item.source_url for item in evidence}
    domains = {_source_domain(url) for url in urls}
    domains.discard("")
    return (
        loop_count >= config.broad_question_min_loops
        and len(urls) >= config.broad_question_min_evidence_sources
        and len(domains) >= config.broad_question_min_source_domains
    )


def _breadth_gap(
    plan: ResearchPlan,
    evidence: list[EvidenceItem],
    loop_count: int,
    config: Config,
) -> str:
    if plan.breadth != "broad" or breadth_requirements_met(plan, evidence, loop_count, config):
        return ""
    urls = {item.source_url for item in evidence}
    domains = {_source_domain(url) for url in urls}
    domains.discard("")
    return (
        "Broad-question breadth gate is not met: "
        f"loops {loop_count}/{config.broad_question_min_loops}, "
        f"evidence sources {len(urls)}/{config.broad_question_min_evidence_sources}, "
        f"source domains {len(domains)}/{config.broad_question_min_source_domains}. "
        "Seek evidence from previously unseen organizations or domains."
    )


def choose_queries(
    llm: LLMClient,
    topic: str,
    plan: ResearchPlan,
    evidence: list[EvidenceItem],
    limit: int,
    breadth_gap: str = "",
) -> list[str]:
    context = _plan_context(plan, evidence)
    if breadth_gap:
        context += f"\n\n{breadth_gap}"
    args = llm.chat_with_tool(
        [
            {"role": "system", "content": QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Research task:\n{topic}\n\nCoverage plan:\n{context}"},
        ],
        QUERY_TOOL,
    ) or {}
    known_ids = {item.id for item in plan.items}
    queries: list[str] = []
    for proposal in args.get("queries") or []:
        if not isinstance(proposal, dict):
            continue
        query = str(proposal.get("query") or "").strip()
        plan_item_id = str(proposal.get("plan_item_id") or "").strip()
        if query and plan_item_id in known_ids and query not in queries:
            queries.append(query)
        if len(queries) >= limit:
            break
    if queries:
        return queries
    target = next((item for item in plan.items if item.status != "supported"), plan.items[0])
    suffix = "independent perspectives alternative sources" if breadth_gap else "primary sources data"
    return [f"{topic} {target.question} {suffix}"]


def extract_evidence(
    llm: LLMClient, plan: ResearchPlan, sources: list[Source]
) -> list[EvidenceItem]:
    if not sources:
        return []
    args = llm.chat_with_tool(
        [
            {"role": "system", "content": EVIDENCE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Plan:\n{_plan_context(plan, [])}\n\nSources:\n{format_for_context(sources)}",
            },
        ],
        EVIDENCE_TOOL,
    ) or {}
    known_urls = {source.url: source for source in sources}
    known_ids = {item.id for item in plan.items}
    evidence: list[EvidenceItem] = []
    for raw in args.get("items") or []:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("source_url", "")).strip()
        plan_item_id = str(raw.get("plan_item_id", "")).strip()
        claim = str(raw.get("claim", "")).strip()
        if not claim or url not in known_urls or plan_item_id not in known_ids:
            continue
        source = known_urls[url]
        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 1.0))))
        except (TypeError, ValueError):
            confidence = 1.0
        evidence.append(
            EvidenceItem(
                claim=claim,
                source_title=source.title,
                source_url=url,
                excerpt=str(raw.get("excerpt", "")).strip(),
                plan_item_id=plan_item_id,
                confidence=confidence,
            )
        )
    return evidence


def audit_evidence(llm: LLMClient, state: ResearchState) -> dict[str, list[str]]:
    assert state.plan is not None
    evidence = "\n".join(
        f"- {item.plan_item_id}: {item.claim} [{item.source_title}]({item.source_url})"
        for item in state.evidence
    ) or "(no retained evidence)"
    args = llm.chat_with_tool(
        [
            {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original request:\n{state.topic}\n\nPlan:\n"
                f"{_plan_context(state.plan, state.evidence)}\n\nEvidence:\n{evidence}",
            },
        ],
        AUDIT_TOOL,
    ) or {}
    return {
        "unsupported_plan_item_ids": [str(x) for x in args.get("unsupported_plan_item_ids", [])],
        "contradictions": [str(x) for x in args.get("contradictions", [])],
        "writing_instructions": [str(x) for x in args.get("writing_instructions", [])],
    }


def write_report(llm: LLMClient, state: ResearchState, audit: dict[str, list[str]]) -> str:
    assert state.plan is not None
    sections: list[str] = []
    for plan_item in state.plan.items:
        items = [e for e in state.evidence if e.plan_item_id == plan_item.id]
        rendered = "\n".join(
            f"- Claim: {e.claim}\n  Support: {e.excerpt}\n"
            f"  Citation: [{e.source_title}]({e.source_url})"
            for e in items
        ) or "- No reliable evidence was retained; state this limitation explicitly."
        sections.append(f"## {plan_item.section}\nQuestion: {plan_item.question}\n{rendered}")
    content = llm.chat(
        [
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original request:\n{state.topic}\n\nEvidence by planned section:\n"
                + "\n\n".join(sections)
                + "\n\nEvidence audit:\n"
                + "\n".join(
                    f"- {instruction}"
                    for instruction in (
                        audit["writing_instructions"]
                        + [f"Contradiction to resolve: {x}" for x in audit["contradictions"]]
                        + [f"Unsupported section: {x}" for x in audit["unsupported_plan_item_ids"]]
                    )
                ),
            },
        ]
    )
    if not content.strip():
        raise RuntimeError("Final report writer returned an empty response")
    return content


def review_and_revise(
    llm: LLMClient,
    state: ResearchState,
    report: str,
    audit: dict[str, list[str]],
) -> str:
    assert state.plan is not None
    review = llm.chat_with_tool(
        [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Original request:\n{state.topic}\n\nPlan:\n"
                f"{_plan_context(state.plan, state.evidence)}\n\nAudit:\n{audit}\n\nDraft:\n{report}",
            },
        ],
        REVIEW_TOOL,
    ) or {}
    instructions = [str(x) for x in review.get("instructions", [])]
    if not review.get("revision_needed") or not instructions:
        return report
    revised = llm.chat(
        [
            {"role": "system", "content": REVISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Review instructions:\n- " + "\n- ".join(instructions)
                + f"\n\nEvidence audit:\n{audit}\n\nDraft report:\n{report}",
            },
        ]
    )
    return revised if revised.strip() else report


def enforce_citations(llm: LLMClient, state: ResearchState, report: str) -> str:
    """Make citation compliance a final postcondition, not a prompt-only hope."""
    compliance = check_citation_compliance(report, state)
    if compliance.compliant:
        return report
    evidence_inventory = "\n".join(
        f"- Plan item {item.plan_item_id}: {item.claim} "
        f"[{item.source_title}]({item.source_url})"
        for item in state.evidence
    )
    repaired = llm.chat(
        [
            {"role": "system", "content": CITATION_REPAIR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Evidence inventory:\n{evidence_inventory}\n\nReport:\n{report}",
            },
        ]
    )
    candidate = repaired if repaired.strip() else report
    known_urls = {item.source_url for item in state.evidence}
    candidate = remove_unknown_citations(candidate, known_urls)
    remaining = check_citation_compliance(candidate, state)
    candidate = append_missing_evidence_notes(candidate, state, remaining.missing_plan_item_ids)
    final = check_citation_compliance(candidate, state)
    if not final.compliant:
        raise RuntimeError(
            "Final report failed citation compliance after repair: "
            f"unknown_urls={final.unknown_urls}, missing_plan_items={final.missing_plan_item_ids}"
        )
    return candidate


def run_deep_research(
    topic: str,
    llm: LLMClient,
    tools: dict[str, Tool],
    config: Config,
    on_iteration: Optional[Callable[[int, ResearchState], None]] = None,
    on_query: Optional[Callable[[str], None]] = None,
) -> ResearchState:
    # Local import avoids coupling the data pipeline to the lightweight loop module.
    from research_agent.agent import enrich_with_fetch

    state = ResearchState(topic=topic)
    state.plan = create_plan(llm, topic, config.max_plan_items)
    update_coverage(state.plan, state.evidence, config.min_evidence_per_plan_item)

    for index in range(config.max_loops):
        queries = choose_queries(
            llm,
            topic,
            state.plan,
            state.evidence,
            config.deep_queries_per_loop,
            _breadth_gap(state.plan, state.evidence, state.loop_count, config),
        )
        all_sources: list[Source] = []
        for query in queries:
            state.search_query = query
            if on_query:
                on_query(query)
            all_sources.extend(tools["web_search"].run(query=query))
        sources = rank_sources(dedupe_sources(all_sources), " ".join(queries))
        sources = enrich_with_fetch(tools, sources, config.max_fetch_per_loop)
        sources = dedupe_sources(sources)
        existing_urls = {source.url for source in state.sources}
        new_sources = [source for source in sources if source.url not in existing_urls]
        state.add_sources(new_sources)
        state.add_evidence(extract_evidence(llm, state.plan, new_sources))
        update_coverage(state.plan, state.evidence, config.min_evidence_per_plan_item)
        state.loop_count += 1
        if on_iteration:
            on_iteration(index, state)
        if (
            config.allow_early_stop
            and plan_complete(state.plan)
            and breadth_requirements_met(state.plan, state.evidence, state.loop_count, config)
        ):
            break

    audit = audit_evidence(llm, state)
    report = write_report(llm, state, audit)
    if config.enable_final_revision:
        report = review_and_revise(llm, state, report, audit)
    if config.enforce_citation_compliance:
        report = enforce_citations(llm, state, report)
    state.running_summary = f"## Summary\n{report}\n\n### Sources:\n{format_citations(state.sources)}"
    return state
