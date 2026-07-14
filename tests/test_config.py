from research_agent.config import Config


def test_defaults_match_hardware_appropriate_local_model():
    config = Config()
    assert config.model == "ollama/qwen2.5:7b"
    assert config.max_loops == 3
    assert config.search_backend == "duckduckgo"


def test_max_output_tokens_has_a_modest_default():
    config = Config()
    assert config.max_output_tokens == 2048


def test_ollama_model_gets_localhost_api_base_by_default():
    config = Config(model="ollama/qwen2.5:7b")
    assert config.api_base == "http://localhost:11434"


def test_hosted_model_gets_no_api_base_by_default():
    # Regression guard: a hosted model must not silently inherit Ollama's local port.
    config = Config(model="openai/gpt-4o-mini")
    assert config.api_base is None


def test_explicit_api_base_is_not_overridden():
    config = Config(model="openai/gpt-4o-mini", api_base="https://my-proxy.example.com")
    assert config.api_base == "https://my-proxy.example.com"


def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_MAX_LOOPS", "5")
    config = Config.from_env()
    assert config.max_loops == 5


def test_explicit_override_wins_over_env_var(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_MAX_LOOPS", "5")
    config = Config.from_env(max_loops=7)
    assert config.max_loops == 7


def test_bool_env_var_coercion(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_FETCH_FULL_PAGE", "true")
    config = Config.from_env()
    assert config.fetch_full_page is True


def test_fetch_defaults_are_conservative():
    config = Config()
    assert config.fetch_full_page is False
    assert config.fetch_timeout_seconds == 15.0
    assert config.fetch_max_chars == 4000
    assert config.max_fetch_per_loop == 3


def test_fetch_timeout_seconds_env_var_coerces_to_float(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_FETCH_TIMEOUT_SECONDS", "7.5")
    config = Config.from_env()
    assert config.fetch_timeout_seconds == 7.5


def test_fetch_max_chars_env_var_coerces_to_int(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_FETCH_MAX_CHARS", "8000")
    config = Config.from_env()
    assert config.fetch_max_chars == 8000
