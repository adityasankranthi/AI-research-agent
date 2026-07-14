import time as time_module

from typer.testing import CliRunner

from eval.dataset import EvalCase
from eval.judge import FactResult
from eval.run_eval import app
from research_agent.state import ResearchState, Source

runner = CliRunner()


class _FakeJudge:
    def score_facts(self, summary, key_facts):
        return [FactResult(fact=f, covered=(f == "fact a")) for f in key_facts]


def _fake_build_components(config):
    return object(), object()


def test_run_eval_prints_score_table_and_aggregate(monkeypatch):
    fake_cases = [EvalCase(topic="topic one", key_facts=["fact a", "fact b"])]
    monkeypatch.setattr("eval.run_eval.DATASET", fake_cases)

    def fake_run(topic, llm, tools, config, on_iteration=None):
        state = ResearchState(topic=topic, running_summary="fact a is covered here")
        state.add_sources([Source(title="S", url="http://s.com", content="c")])
        state.loop_count = 2
        return state

    monkeypatch.setattr("eval.run_eval.run", fake_run)
    monkeypatch.setattr("eval.run_eval.build_components", _fake_build_components)
    monkeypatch.setattr("eval.run_eval._build_judge", lambda kind, model: _FakeJudge())

    result = runner.invoke(
        app, ["--model", "test/model", "--judge", "keyword", "--concurrency", "1"]
    )

    assert result.exit_code == 0, result.output
    assert "1/2" in result.output
    assert "avg fact coverage: 50%" in result.output


def test_run_eval_preserves_dataset_order_regardless_of_completion_order(monkeypatch):
    fake_cases = [
        EvalCase(topic="topic A", key_facts=["fact a"]),
        EvalCase(topic="topic B", key_facts=["fact a"]),
        EvalCase(topic="topic C", key_facts=["fact a"]),
    ]
    monkeypatch.setattr("eval.run_eval.DATASET", fake_cases)

    def fake_run(topic, llm, tools, config, on_iteration=None):
        # Topic A finishes last, reversing completion order relative to submission
        # order -- the printed table must still list A, B, C (dataset order).
        if topic == "topic A":
            time_module.sleep(0.05)
        return ResearchState(topic=topic, running_summary="fact a is here")

    monkeypatch.setattr("eval.run_eval.run", fake_run)
    monkeypatch.setattr("eval.run_eval.build_components", _fake_build_components)
    monkeypatch.setattr("eval.run_eval._build_judge", lambda kind, model: _FakeJudge())

    result = runner.invoke(
        app, ["--model", "test/model", "--judge", "keyword", "--concurrency", "3"]
    )

    assert result.exit_code == 0, result.output
    table_output = result.output[result.output.index("Eval results") :]
    assert table_output.index("topic A") < table_output.index("topic B") < table_output.index(
        "topic C"
    )
