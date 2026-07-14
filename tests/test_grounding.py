from research_agent.grounding import (
    annotate_ungrounded,
    check_grounding,
    extract_cited_urls,
    split_sentences,
)
from research_agent.state import Source

SOURCES = [
    Source(title="A", url="http://a.com", content="a"),
    Source(title="B", url="http://b.com", content="b"),
]


def test_extract_cited_urls_parses_single_citation():
    sentence = "The sky is blue according to [A](http://a.com)."
    assert extract_cited_urls(sentence) == ["http://a.com"]


def test_extract_cited_urls_parses_multiple_citations():
    sentence = "Confirmed by both [A](http://a.com) and [B](http://b.com)."
    assert extract_cited_urls(sentence) == ["http://a.com", "http://b.com"]


def test_extract_cited_urls_returns_empty_list_when_no_citation():
    assert extract_cited_urls("A plain sentence with no citation at all.") == []


def test_split_sentences_splits_on_terminal_punctuation():
    text = "First sentence here. Second sentence here! Third one here?"
    assert split_sentences(text) == [
        "First sentence here.",
        "Second sentence here!",
        "Third one here?",
    ]


def test_check_grounding_marks_sentence_grounded_when_cited_url_is_a_known_source():
    summary = "This is a long enough claim about the topic [A](http://a.com)."
    results = check_grounding(summary, SOURCES)
    assert len(results) == 1
    assert results[0].grounded is True
    assert results[0].cited_urls == ["http://a.com"]


def test_check_grounding_flags_sentence_with_uncited_long_claim():
    summary = "This is a fairly long uncited claim about the research topic at hand."
    results = check_grounding(summary, SOURCES)
    assert len(results) == 1
    assert results[0].grounded is False


def test_check_grounding_flags_sentence_citing_an_unknown_url():
    summary = "This is a long enough claim about the topic [C](http://c.com)."
    results = check_grounding(summary, SOURCES)
    assert results[0].grounded is False


def test_check_grounding_skips_short_transitional_sentences():
    summary = "In conclusion. This is a fairly long uncited claim about the topic though."
    results = check_grounding(summary, SOURCES)
    # "In conclusion." is below the word-count threshold and skipped entirely.
    assert len(results) == 1


def test_check_grounding_returns_empty_list_for_empty_summary():
    assert check_grounding("", SOURCES) == []


def test_annotate_ungrounded_returns_summary_unchanged_when_all_grounded():
    summary = "This is a long enough claim about the topic [A](http://a.com)."
    results = check_grounding(summary, SOURCES)
    assert annotate_ungrounded(summary, results) == summary


def test_annotate_ungrounded_appends_footer_for_ungrounded_sentences():
    summary = "This is a fairly long uncited claim about the research topic at hand."
    results = check_grounding(summary, SOURCES)
    annotated = annotate_ungrounded(summary, results)
    assert annotated.startswith(summary)
    assert "### Unverified claims" in annotated
    assert "This is a fairly long uncited claim" in annotated
