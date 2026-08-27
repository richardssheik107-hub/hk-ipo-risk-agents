from __future__ import annotations

import json

from pydantic import BaseModel, Field

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


class _StructuredResult(BaseModel):
    label: str
    evidence_ids: list[str] = Field(min_length=1)


class _StructuredResponse:
    usage = _FakeUsage()

    def __init__(self, response_id: str, arguments: dict[str, object]) -> None:
        self.id = response_id
        self.output_text = ""
        self.output = [
            {
                "type": "function_call",
                "name": OpenAIResponsesLLMProvider.tool_name,
                "arguments": json.dumps(arguments),
            }
        ]

    def model_dump_json(self) -> str:
        return json.dumps({"id": self.id, "output": self.output}, sort_keys=True)


class _SequenceResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.responses = [
            _StructuredResponse("resp-invalid", {"label": None, "evidence_ids": ["e1"]}),
            _StructuredResponse("resp-valid", {"label": "ok", "evidence_ids": ["e1"]}),
        ]

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class _SequenceClient:
    def __init__(self) -> None:
        self.responses = _SequenceResponses()


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


def test_responses_provider_exposes_exact_instruction_hash_without_prompt_text():
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=0,
        client=_FakeClient(),
    )

    generic = provider.structured_prompt_hash("generic_task", "generic_v1")
    legal = provider.structured_prompt_hash(
        "litigation_compliance_extract", "legal_litigation_compliance_v1"
    )

    assert len(generic) == 64
    assert len(legal) == 64
    assert legal != generic


def test_responses_provider_retries_schema_invalid_function_arguments_with_safe_feedback():
    client = _SequenceClient()
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=1,
        client=client,
    )

    result = provider.generate_structured(
        task_name="generic_test_task",
        prompt_version="generic_test_v1",
        evidence=[],
        response_model=_StructuredResult,
    )

    assert result == _StructuredResult(label="ok", evidence_ids=["e1"])
    assert len(client.responses.calls) == 2
    assert "failed local schema validation" in str(
        client.responses.calls[1]["instructions"]
    )
    assert "label" in str(client.responses.calls[1]["instructions"])
    assert provider.last_call_metadata is not None
    assert provider.last_call_metadata.request_id == "resp-valid"
    assert provider.last_attempt_trace == [
        {
            "stage": "transport",
            "structured_attempt": 1,
            "attempt": 1,
            "outcome": "success",
        },
        {
            "stage": "structured_validation",
            "structured_attempt": 1,
            "outcome": "failure",
            "failure_kind": "pydantic_validation",
            "retry_scheduled": True,
        },
        {
            "stage": "transport",
            "structured_attempt": 2,
            "attempt": 1,
            "outcome": "success",
        },
        {
            "stage": "structured_validation",
            "structured_attempt": 2,
            "outcome": "success",
        },
    ]


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
