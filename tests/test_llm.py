import json
from types import SimpleNamespace

import pytest

from research_agent.llm import LLMClient, extract_json_object


def test_extract_json_object_from_pure_json():
    assert extract_json_object('{"query": "x"}') == {"query": "x"}


def test_extract_json_object_from_embedded_prose():
    text = 'Sure, here you go:\n```json\n{"query": "x", "rationale": "y"}\n```\nHope that helps.'
    assert extract_json_object(text) == {"query": "x", "rationale": "y"}


def test_extract_json_object_returns_none_for_unparseable_text():
    assert extract_json_object("I cannot comply with that request.") is None


def test_extract_json_object_returns_none_for_empty_text():
    assert extract_json_object("") is None
    assert extract_json_object(None) is None


def _fake_response(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=None)


def test_chat_with_tool_uses_native_tool_call(monkeypatch):
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="search_query", arguments=json.dumps({"query": "x"}))
    )
    response = _fake_response(tool_calls=[tool_call])
    monkeypatch.setattr("research_agent.llm.litellm.completion", lambda **kwargs: response)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model")
    result = client.chat_with_tool(
        [], tool={"type": "function", "function": {"name": "search_query"}}
    )

    assert result == {"query": "x"}


def test_chat_with_tool_falls_back_to_text_extraction(monkeypatch):
    response = _fake_response(content='{"query": "fallback"}', tool_calls=None)
    monkeypatch.setattr("research_agent.llm.litellm.completion", lambda **kwargs: response)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model")
    result = client.chat_with_tool(
        [], tool={"type": "function", "function": {"name": "search_query"}}
    )

    assert result == {"query": "fallback"}


def test_chat_returns_message_content(monkeypatch):
    response = _fake_response(content="a summary")
    monkeypatch.setattr("research_agent.llm.litellm.completion", lambda **kwargs: response)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model")
    assert client.chat([{"role": "user", "content": "hi"}]) == "a summary"


def test_chat_forwards_max_tokens_to_litellm(monkeypatch):
    response = _fake_response(content="ok")
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr("research_agent.llm.litellm.completion", fake_completion)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model", max_tokens=4096)
    client.chat([{"role": "user", "content": "hi"}])

    assert captured["max_tokens"] == 4096


def test_chat_forwards_provider_prefixed_model_string_and_no_api_base(monkeypatch):
    # No provider-specific branch exists in LLMClient -- any litellm model string is
    # just forwarded as-is. This test is the regression guard for that claim.
    response = _fake_response(content="ok")
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr("research_agent.llm.litellm.completion", fake_completion)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="openrouter/anthropic/claude-haiku-4-5")
    client.chat([{"role": "user", "content": "hi"}])

    assert captured["model"] == "openrouter/anthropic/claude-haiku-4-5"
    assert captured["api_base"] is None


def test_chat_forwards_api_key_to_litellm(monkeypatch):
    response = _fake_response(content="ok")
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr("research_agent.llm.litellm.completion", fake_completion)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model", api_key="sk-test")
    client.chat([{"role": "user", "content": "hi"}])

    assert captured["api_key"] == "sk-test"


def test_chat_with_tool_forwards_api_key_to_litellm(monkeypatch):
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="search_query", arguments=json.dumps({"query": "x"}))
    )
    response = _fake_response(tool_calls=[tool_call])
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr("research_agent.llm.litellm.completion", fake_completion)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.0)

    client = LLMClient(model="test/model", api_key="sk-test")
    client.chat_with_tool([], tool={"type": "function", "function": {"name": "search_query"}})

    assert captured["api_key"] == "sk-test"


def test_cost_accumulates_across_calls(monkeypatch):
    response = _fake_response(content="ok")
    monkeypatch.setattr("research_agent.llm.litellm.completion", lambda **kwargs: response)
    monkeypatch.setattr("research_agent.llm.litellm.completion_cost", lambda response: 0.002)

    client = LLMClient(model="test/model")
    client.chat([])
    client.chat([])

    assert client.total_cost == pytest.approx(0.004)
    assert client.n_calls == 2
