from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel
import pytest

from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import (
    LLMFailureKind,
    LLMProviderError,
    OpenAICompatibleLLMProvider,
    UnavailableLLMProvider,
)
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import Evidence


class Candidate(BaseModel):
    finding: str
    confidence: float


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.completions = FakeCompletions(outcomes)
        self.chat = SimpleNamespace(completions=self.completions)


def response(content: str, *, request_id: str = "req-safe"):
    return SimpleNamespace(
        id="response-id",
        _request_id=request_id,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=12,
            completion_tokens=5,
            total_tokens=17,
        ),
    )


def provider(outcomes, *, max_retries: int = 2):
    client = FakeClient(outcomes)
    instance = OpenAICompatibleLLMProvider(
        api_key="test-secret",
        base_url="https://llm.invalid/v1",
        model="test-model",
        timeout_seconds=9,
        max_retries=max_retries,
        client=client,
    )
    return instance, client


def evidence(text: str = "Synthetic evidence") -> Evidence:
    return Evidence(
        evidence_id="ev-1",
        document_id="doc-1",
        chunk_id="chunk-1",
        page=7,
        section="business",
        text=text,
        metadata={"local_path": "C:/must-not-be-sent/prospectus.pdf"},
    )


def test_settings_environment_overrides_yaml_and_coerces_integers(tmp_path, monkeypatch):
    config = tmp_path / "settings.yaml"
    config.write_text(
        "llm_provider: unavailable\nllm_timeout_seconds: 31\nllm_max_retries: 4\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IPO_RISK_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("IPO_RISK_LLM_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("IPO_RISK_LLM_MAX_RETRIES", "1")
    settings = load_settings(str(config))
    assert settings.llm_provider == "openai_compatible"
    assert settings.llm_timeout_seconds == 17
    assert settings.llm_max_retries == 1
    assert isinstance(settings.llm_timeout_seconds, int)
    assert isinstance(settings.llm_max_retries, int)


def test_settings_repr_never_exposes_api_key():
    secret = "secret-that-must-not-appear"
    assert secret not in repr(Settings(llm_api_key=secret))


def test_mock_complete_records_legacy_metadata():
    instance = MockLLMProvider()
    assert instance.complete("hello") == "mock response"
    assert instance.last_call_metadata is not None
    assert instance.last_call_metadata.prompt_version == "legacy_complete"
    assert len(instance.last_call_metadata.raw_response_hash) == 64


def test_real_structured_call_validates_exact_model_and_safe_metadata():
    instance, _ = provider([response('{"finding":"candidate","confidence":0.8}')])
    result = instance.generate_structured(
        task_name="legal_extract",
        prompt_version="legal_v1",
        evidence=[evidence()],
        response_model=Candidate,
    )
    assert result == Candidate(finding="candidate", confidence=0.8)
    assert instance.last_call_metadata is not None
    assert instance.last_call_metadata.provider_name == "openai_compatible"
    assert instance.last_call_metadata.model_name == "test-model"
    assert instance.last_call_metadata.prompt_version == "legal_v1"
    assert instance.last_call_metadata.token_usage == {
        "prompt_tokens": 12,
        "completion_tokens": 5,
        "total_tokens": 17,
    }
    assert instance.last_call_metadata.request_id == "req-safe"
    assert len(instance.last_call_metadata.raw_response_hash) == 64


def test_structured_request_contains_only_selected_evidence_and_no_metadata_path():
    instance, client = provider([response('{"finding":"ok","confidence":1}')])
    selected = evidence("Only this text is allowed")
    instance.generate_structured(
        task_name="business_extract",
        prompt_version="business_v1",
        evidence=[selected],
        response_model=Candidate,
    )
    call = client.completions.calls[0]
    payload = json.loads(call["messages"][1]["content"])
    assert payload["task_name"] == "business_extract"
    assert payload["prompt_version"] == "business_v1"
    assert payload["response_schema"] == Candidate.model_json_schema()
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["text"] == "Only this text is allowed"
    assert "metadata" not in payload["evidence"][0]
    assert "must-not-be-sent" not in call["messages"][1]["content"]


def test_complete_uses_legacy_path_and_records_hash():
    instance, client = provider([response("plain text")])
    assert instance.complete("summarize") == "plain text"
    assert client.completions.calls[0]["messages"] == [
        {"role": "user", "content": "summarize"}
    ]
    assert "response_format" not in client.completions.calls[0]
    assert instance.last_call_metadata.prompt_version == "legacy_complete"


@pytest.mark.parametrize(
    "invalid",
    ["not-json", '{"finding":4,"confidence":"wrong"}', "{}"],
)
def test_invalid_structured_output_never_crosses_provider_boundary(invalid):
    instance, client = provider([response(invalid), response(invalid)], max_retries=1)
    with pytest.raises(LLMProviderError) as caught:
        instance.generate_structured(
            task_name="extract",
            prompt_version="v1",
            evidence=[],
            response_model=Candidate,
        )
    assert caught.value.kind == LLMFailureKind.RESPONSE_VALIDATION
    assert caught.value.attempts == 2
    assert len(client.completions.calls) == 2


def test_response_validation_can_recover_within_budget():
    instance, client = provider(
        [response("not-json"), response('{"finding":"ok","confidence":0.5}')],
        max_retries=1,
    )
    result = instance.generate_structured(
        task_name="extract",
        prompt_version="v1",
        evidence=[],
        response_model=Candidate,
    )
    assert result.finding == "ok"
    assert len(client.completions.calls) == 2


class RateLimitError(Exception):
    status_code = 429


class AuthenticationError(Exception):
    status_code = 401


class BadRequestError(Exception):
    status_code = 400


def test_recoverable_transport_failure_respects_total_attempt_budget():
    instance, client = provider(
        [RateLimitError("remote secret"), RateLimitError("remote secret"), RateLimitError("remote secret")],
        max_retries=2,
    )
    with pytest.raises(LLMProviderError) as caught:
        instance.complete("hello")
    assert caught.value.kind == LLMFailureKind.TRANSPORT
    assert caught.value.recoverable is True
    assert caught.value.attempts == 3
    assert len(client.completions.calls) == 3
    assert "remote secret" not in str(caught.value)


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (AuthenticationError("credential detail"), LLMFailureKind.AUTHENTICATION),
        (BadRequestError("request body detail"), LLMFailureKind.REQUEST),
    ],
)
def test_nonrecoverable_remote_errors_fail_immediately_and_safely(error, kind):
    instance, client = provider([error], max_retries=4)
    with pytest.raises(LLMProviderError) as caught:
        instance.complete("hello")
    assert caught.value.kind == kind
    assert caught.value.recoverable is False
    assert caught.value.attempts == 1
    assert len(client.completions.calls) == 1
    assert str(error) not in str(caught.value)


def test_unavailable_provider_is_deterministic_and_zero_network():
    instance = UnavailableLLMProvider("runtime configuration missing")
    with pytest.raises(LLMProviderError) as caught:
        instance.complete("must not leave process")
    assert caught.value.kind == LLMFailureKind.UNAVAILABLE
    assert caught.value.attempts == 0
    assert instance.last_call_metadata is None


def test_registry_exposes_all_three_provider_names():
    registry = default_registry()
    assert isinstance(registry.create("llm_provider", "mock"), MockLLMProvider)
    assert isinstance(registry.create("llm_provider", "unavailable"), UnavailableLLMProvider)
    with pytest.raises(LLMProviderError) as caught:
        registry.create(
            "llm_provider",
            "openai_compatible",
            api_key="",
            base_url="",
            model="",
        )
    assert caught.value.kind == LLMFailureKind.UNAVAILABLE


def test_container_degrades_missing_real_configuration_to_unavailable():
    settings = replace(Settings(), llm_provider="openai_compatible")
    result = DependencyContainer(settings, default_registry()).create_llm_provider()
    assert isinstance(result, UnavailableLLMProvider)


def test_container_injects_complete_real_configuration(monkeypatch):
    fake = FakeClient([response("ok")])
    monkeypatch.setattr(
        OpenAICompatibleLLMProvider,
        "_build_client",
        staticmethod(lambda **kwargs: fake),
    )
    settings = replace(
        Settings(),
        llm_provider="openai_compatible",
        llm_api_key="runtime-only",
        llm_base_url="https://runtime.invalid/v1",
        llm_model="runtime-model",
        llm_timeout_seconds=23,
        llm_max_retries=1,
    )
    result = DependencyContainer(settings, default_registry()).create_llm_provider()
    assert isinstance(result, OpenAICompatibleLLMProvider)
    assert result.model == "runtime-model"
    assert result.timeout_seconds == 23
    assert result.max_retries == 1


def test_openai_dependency_is_declared_without_vendor_sdk():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8").lower()
    assert '"openai>=1.40,<3"' in pyproject
    assert "volcano" not in pyproject
    assert "doubao" not in pyproject
