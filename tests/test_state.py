from research_agent.state import ResearchState, Source


def test_add_sources_accumulates_across_loops():
    state = ResearchState(topic="test topic")
    state.add_sources([Source(title="A", url="http://a.com", content="a")])
    state.add_sources([Source(title="B", url="http://b.com", content="b")])

    assert [s.url for s in state.sources] == ["http://a.com", "http://b.com"]


def test_sources_default_factory_is_isolated_per_instance():
    # Regression guard for the classic dataclass pitfall: `sources: list = []` would
    # share one list across every ResearchState instance. default_factory=list avoids it.
    first = ResearchState(topic="t1")
    second = ResearchState(topic="t2")
    first.add_sources([Source(title="A", url="http://a.com", content="a")])

    assert second.sources == []
