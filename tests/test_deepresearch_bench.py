import json

from typer.testing import CliRunner

from eval.deepresearch_bench import app
from research_agent.state import ResearchState, Source

runner = CliRunner()


def _write_queries(path, queries):
    path.write_text("\n".join(json.dumps(q) for q in queries))


class _FakeLLMClient:
    total_cost = 0.0


def _fake_build_components(config):
    return _FakeLLMClient(), object()


def test_writes_expected_jsonl_shape(tmp_path, monkeypatch):
    query_file = tmp_path / "query.jsonl"
    _write_queries(
        query_file,
        [
            {"id": 1, "topic": "Science", "language": "en", "prompt": "prompt one"},
            {"id": 2, "topic": "Science", "language": "en", "prompt": "prompt two"},
        ],
    )
    output_file = tmp_path / "model.jsonl"

    def fake_run(topic, llm, tools, config, on_iteration=None):
        state = ResearchState(topic=topic, running_summary=f"summary for {topic}")
        state.add_sources([Source(title="S", url="http://s.com", content="c")])
        return state

    monkeypatch.setattr("eval.deepresearch_bench.run", fake_run)
    monkeypatch.setattr("eval.deepresearch_bench.build_components", _fake_build_components)

    result = runner.invoke(
        app,
        [
            "--query-file", str(query_file),
            "--output", str(output_file),
            "--model", "test/model",
            "--concurrency", "1",
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in output_file.read_text().splitlines()]
    assert lines == [
        {"id": 1, "prompt": "prompt one", "article": "summary for prompt one"},
        {"id": 2, "prompt": "prompt two", "article": "summary for prompt two"},
    ]


def test_limit_and_language_filter_queries(tmp_path, monkeypatch):
    query_file = tmp_path / "query.jsonl"
    _write_queries(
        query_file,
        [
            {"id": 1, "topic": "T", "language": "en", "prompt": "p1"},
            {"id": 2, "topic": "T", "language": "zh", "prompt": "p2"},
            {"id": 3, "topic": "T", "language": "en", "prompt": "p3"},
        ],
    )
    output_file = tmp_path / "model.jsonl"

    def fake_run(topic, llm, tools, config, on_iteration=None):
        return ResearchState(topic=topic, running_summary="summary")

    monkeypatch.setattr("eval.deepresearch_bench.run", fake_run)
    monkeypatch.setattr("eval.deepresearch_bench.build_components", _fake_build_components)

    result = runner.invoke(
        app,
        [
            "--query-file", str(query_file),
            "--output", str(output_file),
            "--language", "en",
            "--limit", "1",
            "--concurrency", "1",
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in output_file.read_text().splitlines()]
    assert lines == [{"id": 1, "prompt": "p1", "article": "summary"}]


def test_ids_filter_selects_specific_tasks(tmp_path, monkeypatch):
    query_file = tmp_path / "query.jsonl"
    _write_queries(
        query_file,
        [
            {"id": 1, "topic": "T", "language": "en", "prompt": "p1"},
            {"id": 2, "topic": "T", "language": "en", "prompt": "p2"},
            {"id": 3, "topic": "T", "language": "en", "prompt": "p3"},
        ],
    )
    output_file = tmp_path / "model.jsonl"

    def fake_run(topic, llm, tools, config, on_iteration=None):
        return ResearchState(topic=topic, running_summary="summary")

    monkeypatch.setattr("eval.deepresearch_bench.run", fake_run)
    monkeypatch.setattr("eval.deepresearch_bench.build_components", _fake_build_components)

    result = runner.invoke(
        app,
        [
            "--query-file", str(query_file),
            "--output", str(output_file),
            "--ids", "1,3",
            "--concurrency", "1",
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in output_file.read_text().splitlines()]
    assert {line["id"] for line in lines} == {1, 3}


def test_a_raising_task_is_skipped_and_counted_not_written(tmp_path, monkeypatch):
    query_file = tmp_path / "query.jsonl"
    _write_queries(
        query_file,
        [
            {"id": 1, "topic": "T", "language": "en", "prompt": "good prompt"},
            {"id": 2, "topic": "T", "language": "en", "prompt": "bad prompt"},
        ],
    )
    output_file = tmp_path / "model.jsonl"

    def fake_run(topic, llm, tools, config, on_iteration=None):
        if topic == "bad prompt":
            raise RuntimeError("summarizer exploded")
        return ResearchState(topic=topic, running_summary="summary")

    monkeypatch.setattr("eval.deepresearch_bench.run", fake_run)
    monkeypatch.setattr("eval.deepresearch_bench.build_components", _fake_build_components)

    result = runner.invoke(
        app,
        [
            "--query-file", str(query_file),
            "--output", str(output_file),
            "--concurrency", "1",
        ],
    )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in output_file.read_text().splitlines()]
    assert lines == [{"id": 1, "prompt": "good prompt", "article": "summary"}]
    assert "failed" in result.output
    assert "1/2 tasks succeeded" in result.output
