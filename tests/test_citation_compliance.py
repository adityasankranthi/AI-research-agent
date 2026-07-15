from research_agent.citation_compliance import (
    append_missing_evidence_notes,
    check_citation_compliance,
    remove_unknown_citations,
)
from research_agent.state import EvidenceItem, PlanItem, ResearchPlan, ResearchState


def _state() -> ResearchState:
    state = ResearchState(topic="t")
    state.plan = ResearchPlan("t", [PlanItem("a", "q", "Findings")])
    state.evidence = [
        EvidenceItem("Supported claim.", "Official", "https://known", "excerpt", "a")
    ]
    return state


def test_compliance_requires_a_known_citation_for_each_evidenced_plan_item():
    state = _state()
    missing = check_citation_compliance("Supported claim.", state)
    present = check_citation_compliance(
        "Supported claim [Official](https://known).", state
    )

    assert missing.missing_plan_item_ids == ["a"]
    assert missing.compliant is False
    assert present.compliant is True


def test_unknown_citations_are_removed_without_removing_link_text():
    report = "A claim [Unknown](https://unknown)."

    assert remove_unknown_citations(report, {"https://known"}) == "A claim Unknown."


def test_fallback_notes_make_missing_plan_item_citation_compliant():
    state = _state()

    report = append_missing_evidence_notes("# Report", state, ["a"])

    assert "## Evidence notes" in report
    assert "Supported claim. [Official](https://known)" in report
    assert check_citation_compliance(report, state).compliant is True
