from research_agent.prompts import (
    REFLECTION_TOOL,
    SEARCH_QUERY_TOOL,
    current_date,
    reflection_user_message,
    summarizer_user_message,
)


def test_current_date_has_month_day_year_shape():
    assert len(current_date().split()) == 3


def test_summarizer_user_message_without_existing_summary():
    message = summarizer_user_message("topic", existing_summary="", new_context="new stuff")
    assert "<Existing Summary>" not in message
    assert "new stuff" in message
    assert "topic" in message


def test_summarizer_user_message_with_existing_summary():
    message = summarizer_user_message(
        "topic", existing_summary="old stuff", new_context="new stuff"
    )
    assert "<Existing Summary>" in message
    assert "old stuff" in message
    assert "new stuff" in message


def test_reflection_user_message_includes_summary():
    assert "current summary" in reflection_user_message("current summary")


def test_search_query_tool_schema_has_required_fields():
    params = SEARCH_QUERY_TOOL["function"]["parameters"]
    assert set(params["required"]) == {"query", "rationale"}


def test_reflection_tool_schema_has_required_fields():
    params = REFLECTION_TOOL["function"]["parameters"]
    assert set(params["required"]) == {"knowledge_gap", "follow_up_query"}
