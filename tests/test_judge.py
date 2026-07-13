from eval.judge import FactResult, KeywordRecallJudge, LLMJudge


def test_keyword_recall_judge_marks_fact_covered_when_keywords_overlap():
    judge = KeywordRecallJudge(threshold=0.6)
    summary = "The Model Context Protocol was created by Anthropic as an open standard."
    facts = ["MCP was created by Anthropic"]

    results = judge.score_facts(summary, facts)

    assert results == [FactResult(fact="MCP was created by Anthropic", covered=True)]


def test_keyword_recall_judge_marks_fact_uncovered_when_no_overlap():
    judge = KeywordRecallJudge(threshold=0.6)
    summary = "Bananas are a good source of potassium."
    facts = ["Rust achieves memory safety without a garbage collector"]

    results = judge.score_facts(summary, facts)

    assert results[0].covered is False


def test_keyword_recall_judge_respects_threshold():
    judge = KeywordRecallJudge(threshold=0.9)
    summary = "Kubernetes automates deployment of containers."
    facts = [
        "Kubernetes automates deployment, scaling, and management of containerized applications"
    ]

    results = judge.score_facts(summary, facts)

    # Only ~3 of 7 significant keywords overlap -- well under a 0.9 threshold.
    assert results[0].covered is False


class _FakeLLM:
    def __init__(self, response):
        self._response = response

    def chat_with_tool(self, messages, tool):
        return self._response


def test_llm_judge_maps_covered_array_to_facts_in_order():
    llm = _FakeLLM({"covered": [True, False]})
    judge = LLMJudge(llm)

    results = judge.score_facts("some summary", ["fact one", "fact two"])

    assert results == [
        FactResult(fact="fact one", covered=True),
        FactResult(fact="fact two", covered=False),
    ]


def test_llm_judge_defaults_to_not_covered_when_tool_call_fails():
    llm = _FakeLLM(None)
    judge = LLMJudge(llm)

    results = judge.score_facts("some summary", ["fact one", "fact two"])

    assert results == [
        FactResult(fact="fact one", covered=False),
        FactResult(fact="fact two", covered=False),
    ]


def test_llm_judge_handles_short_covered_array_gracefully():
    # A model that returns fewer booleans than facts shouldn't crash the eval run.
    llm = _FakeLLM({"covered": [True]})
    judge = LLMJudge(llm)

    results = judge.score_facts("some summary", ["fact one", "fact two"])

    assert results == [
        FactResult(fact="fact one", covered=True),
        FactResult(fact="fact two", covered=False),
    ]
