from __future__ import annotations

from ipo_risk.core.config import Settings
from ipo_risk.providers.llm import OpenAIResponsesLLMProvider
from ipo_risk.services.analysis_service import IPOAnalysisService


class _FakeUsage:
    input_tokens = 11
    output_tokens = 7
    total_tokens = 18


class _FakeResponse:
    id = "resp-123"
    output_text = "ok"
    output = []
    usage = _FakeUsage()

    def model_dump_json(self) -> str:
        return '{"id":"resp-123","output_text":"ok"}'


class _FakeResponses:
    def create(self, **kwargs):
        assert kwargs["model"] == "test-model"
        return _FakeResponse()


class _FakeClient:
    responses = _FakeResponses()


def test_responses_provider_records_trace_metadata_on_success():
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=0,
        client=_FakeClient(),
    )

    assert provider.complete("hello") == "ok"
    metadata = provider.last_call_metadata
    assert metadata is not None
    assert metadata.provider_name == "openai_responses"
    assert metadata.model_name == "test-model"
    assert metadata.prompt_version == "legacy_complete"
    assert metadata.request_id == "resp-123"
    assert metadata.token_usage == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }
    assert len(metadata.raw_response_hash) == 64
    assert metadata.latency_ms >= 0


def _service_for(settings: Settings) -> IPOAnalysisService:
    service = IPOAnalysisService.__new__(IPOAnalysisService)
    service.settings = settings
    return service


def test_component_modes_reports_responses_provider_available_with_credentials():
    settings = Settings(
        workflow_version="enhanced_v2",
        llm_provider="openai_responses",
        llm_api_key="test-key",
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
    )
    modes = _service_for(settings)._component_modes()
    assert modes["llm_provider"] == "openai_responses"
    assert modes["llm_status"] == "available"


def test_component_modes_reports_responses_provider_missing_credentials():
    settings = Settings(
        workflow_version="enhanced_v2",
        llm_provider="openai_responses",
        llm_api_key="",
        llm_base_url="https://example.invalid/v1",
        llm_model="test-model",
    )
    modes = _service_for(settings)._component_modes()
    assert modes["llm_status"] == "credentials_unavailable"
