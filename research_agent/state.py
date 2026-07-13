from dataclasses import dataclass, field


@dataclass
class Source:
    title: str
    url: str
    content: str


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
    loop_count: int = 0

    def add_sources(self, new_sources: list[Source]) -> None:
        self.sources.extend(new_sources)
