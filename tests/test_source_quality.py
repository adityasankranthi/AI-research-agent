from research_agent.source_quality import rank_sources, source_score
from research_agent.state import Source


def test_primary_source_ranks_above_low_signal_social_source():
    government = Source("Official labor statistics", "https://bls.gov/data/report.pdf", "labor statistics employment report")
    linkedin = Source("Labor statistics opinion", "https://linkedin.com/posts/example", "labor statistics employment report")

    assert rank_sources([linkedin, government], "labor statistics employment") == [government, linkedin]
    assert source_score(government, "labor statistics") > source_score(linkedin, "labor statistics")


def test_ranking_rewards_query_relevance():
    relevant = Source("Battery recycling market data", "https://example.org/battery", "battery recycling market data and forecasts")
    irrelevant = Source("Unrelated report", "https://example.org/other", "sports results and commentary")

    assert rank_sources([irrelevant, relevant], "battery recycling market")[0] is relevant
