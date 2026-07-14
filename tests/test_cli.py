from typer.testing import CliRunner

from research_agent.cli import app
from research_agent.state import ResearchState, Source

runner = CliRunner()


class _FakeLLMClient:
    def __init__(self):
        self.total_cost = 0.0
        self.n_calls = 0


def test_cli_runs_prints_report_and_writes_output_and_trajectory(tmp_path, monkeypatch):
    def fake_run(topic, llm, tools, config, on_iteration=None):
        state = ResearchState(topic=topic)
        state.add_sources([Source(title="A", url="http://a.com", content="a")])
        state.loop_count = 1
        state.search_query = "q"
        state.running_summary = "## Summary\nfake summary\n\n### Sources:\n* A : http://a.com"
        if on_iteration:
            on_iteration(0, state)
        return state

    monkeypatch.setattr("research_agent.cli.run", fake_run)

    output_path = tmp_path / "report.md"
    trajectory_path = tmp_path / "trajectory.json"

    result = runner.invoke(
        app,
        [
            "--topic",
            "test topic",
            "--loops",
            "1",
            "--model",
            "openai/gpt-4o-mini",
            "--output",
            str(output_path),
            "--trajectory",
            str(trajectory_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "fake summary" in result.output
    assert output_path.read_text() == (
        "## Summary\nfake summary\n\n### Sources:\n* A : http://a.com"
    )
    assert trajectory_path.exists()


def test_cli_does_not_default_api_base_for_a_hosted_model(monkeypatch):
    captured = {}

    def fake_build_components(config):
        captured["model"] = config.model
        captured["api_base"] = config.api_base
        return _FakeLLMClient(), object()

    def fake_run(topic, llm, tools, config, on_iteration=None):
        return ResearchState(topic=topic, running_summary="summary")

    monkeypatch.setattr("research_agent.cli.build_components", fake_build_components)
    monkeypatch.setattr("research_agent.cli.run", fake_run)

    result = runner.invoke(app, ["--topic", "t", "--model", "openai/gpt-4o-mini"])

    assert result.exit_code == 0, result.output
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["api_base"] is None


def test_cli_defaults_api_base_for_ollama_model(monkeypatch):
    captured = {}

    def fake_build_components(config):
        captured["api_base"] = config.api_base
        return _FakeLLMClient(), object()

    def fake_run(topic, llm, tools, config, on_iteration=None):
        return ResearchState(topic=topic, running_summary="summary")

    monkeypatch.setattr("research_agent.cli.build_components", fake_build_components)
    monkeypatch.setattr("research_agent.cli.run", fake_run)

    result = runner.invoke(app, ["--topic", "t", "--model", "ollama/qwen2.5:7b"])

    assert result.exit_code == 0, result.output
    assert captured["api_base"] == "http://localhost:11434"
