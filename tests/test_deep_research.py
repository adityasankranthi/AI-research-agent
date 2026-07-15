from research_agent.config import Config
from research_agent.deep_research import choose_queries, create_plan, extract_evidence, plan_complete, run_deep_research, update_coverage
from research_agent.state import EvidenceItem, PlanItem, ResearchPlan, Source


class _FakeLLM:
    def __init__(self, tool_responses=(), chat_responses=()):
        self.tool_responses = list(tool_responses)
        self.chat_responses = list(chat_responses)
        self.tools_seen = []

    def chat_with_tool(self, messages, tool):
        self.tools_seen.append(tool["function"]["name"])
        return self.tool_responses.pop(0)

    def chat(self, messages):
        return self.chat_responses.pop(0)


class _SearchTool:
    def __init__(self, sources):
        self.sources = sources
        self.queries = []

    def run(self, query):
        self.queries.append(query)
        return self.sources


def test_create_plan_preserves_structured_requirements_and_caps_items():
    llm = _FakeLLM(tool_responses=[{"title": "Comparison", "items": [
        {"id": "a", "question": "Compare costs", "section": "Costs", "evidence_requirements": ["current prices"]},
        {"id": "b", "question": "Compare risks", "section": "Risks", "evidence_requirements": ["criticism"]},
    ]}])

    plan = create_plan(llm, "compare products", max_items=1)

    assert plan.title == "Comparison"
    assert [item.id for item in plan.items] == ["a"]
    assert plan.items[0].evidence_requirements == ["current prices"]


def test_coverage_requires_configured_evidence_count():
    plan = ResearchPlan("t", [PlanItem("a", "q", "s")])
    evidence = [EvidenceItem("claim", "S", "https://s", "excerpt", "a")]

    update_coverage(plan, evidence, minimum=2)
    assert plan.items[0].status == "partial"
    assert plan_complete(plan) is False

    evidence.append(EvidenceItem("claim 2", "S2", "https://s2", "excerpt", "a"))
    update_coverage(plan, evidence, minimum=2)
    assert plan.items[0].status == "supported"
    assert plan_complete(plan) is True


def test_extract_evidence_rejects_unknown_urls():
    source = Source("Known", "https://known", "supporting text")
    plan = ResearchPlan("t", [PlanItem("a", "q", "s")])
    llm = _FakeLLM(tool_responses=[{"items": [
        {"claim": "valid", "source_title": "Known", "source_url": "https://known", "excerpt": "supporting text", "plan_item_id": "a"},
        {"claim": "invented", "source_title": "Fake", "source_url": "https://fake", "excerpt": "fake", "plan_item_id": "a"},
    ]}])

    evidence = extract_evidence(llm, plan, [source])

    assert [item.claim for item in evidence] == ["valid"]
    assert evidence[0].source_title == "Known"


def test_malformed_array_elements_are_ignored_instead_of_crashing():
    source = Source("Known", "https://known", "supporting text")
    plan = ResearchPlan("t", [PlanItem("a", "q", "s")])
    llm = _FakeLLM(tool_responses=[{"items": ["not an object", None]}])

    assert extract_evidence(llm, plan, [source]) == []

    query_llm = _FakeLLM(tool_responses=[{"queries": ["bad", None]}])
    queries = choose_queries(query_llm, "topic", plan, [], limit=2)
    assert queries == ["topic q primary sources data"]


def test_deep_pipeline_retains_evidence_then_writes_report_once():
    source = Source("Official", "https://agency.gov/report", "official evidence")
    llm = _FakeLLM(
        tool_responses=[
            {"title": "Topic report", "items": [{"id": "core", "question": "What is the answer?", "section": "Answer", "evidence_requirements": ["primary evidence"]}]},
            {"queries": [{"query": "official answer primary source", "plan_item_id": "core", "expected_information": "answer"}]},
            {"items": [{"claim": "The answer is supported.", "source_title": "Official", "source_url": "https://agency.gov/report", "excerpt": "official evidence", "plan_item_id": "core", "confidence": 0.9}]},
            {"unsupported_plan_item_ids": [], "contradictions": [], "writing_instructions": ["Answer directly"]},
        ],
        chat_responses=["# Answer\nThe answer is supported. [Official](https://agency.gov/report)"],
    )
    search = _SearchTool([source])
    config = Config(research_mode="deep", max_loops=3, min_evidence_per_plan_item=1, deep_queries_per_loop=1, enable_final_revision=False, enforce_citation_compliance=False, enable_citation_grounding_check=False)

    state = run_deep_research("topic", llm, {"web_search": search}, config)

    assert state.loop_count == 1
    assert len(state.evidence) == 1
    assert state.plan is not None and state.plan.items[0].status == "supported"
    assert llm.tools_seen == ["create_research_plan", "choose_research_query", "record_evidence", "audit_evidence"]
    assert "[Official](https://agency.gov/report)" in state.running_summary
