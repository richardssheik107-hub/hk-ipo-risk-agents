import pytest

from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import OpenAIResponsesLLMProvider, UnavailableLLMProvider


def test_default_registry_contains_openai_responses_provider() -> None:
    provider = default_registry().create(
        "llm_provider",
        "openai_responses",
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        client=object(),
    )
    assert isinstance(provider, OpenAIResponsesLLMProvider)


def test_openai_responses_with_incomplete_config_degrades_safely() -> None:
    settings = Settings(llm_provider="openai_responses")
    provider = DependencyContainer(settings=settings, registry=default_registry()).create_llm_provider()
    assert isinstance(provider, UnavailableLLMProvider)
    assert provider.reason == "Responses API configuration is incomplete"


def test_v045_ai_runtime_uses_one_bounded_300_second_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IPO_RISK_LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("IPO_RISK_LLM_MAX_RETRIES", raising=False)
    settings = load_settings("configs/v045_competition_ai.yaml")

    assert settings.llm_timeout_seconds == 300
    assert settings.llm_max_retries == 0
