from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from ipo_risk.providers.llm import LLMProviderError, OpenAIResponsesLLMProvider
from ipo_risk.schemas import Evidence, EvidenceSourceType


class _Result(BaseModel):
    label: str
    evidence_ids: list[str] = Field(min_length=1)


class _TimeoutResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raise TimeoutError("simulated responses timeout")


class _FunctionResponse:
    id = "responses-structured-1"
    output = [
        {
            "type": "function_call",
            "name": "submit_structured_result",
            "arguments": json.dumps({"label": "ok", "evidence_ids": ["e1"]}),
        }
    ]
    usage = None

    def model_dump_json(self) -> str:
        return json.dumps({"id": self.id, "output": self.output})


class _InvalidFunctionResponse(_FunctionResponse):
    output = [
        {
            "type": "function_call",
            "name": "submit_structured_result",
            "arguments": "{",
        }
    ]


class _FailOnceResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise TimeoutError("simulated first responses timeout")
        return _FunctionResponse()


class _InvalidResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _InvalidFunctionResponse()


class _InvalidOnceResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return _InvalidFunctionResponse()
        return _FunctionResponse()


class _Usage:
    prompt_tokens = 9
    completion_tokens = 5
    total_tokens = 14


class _Message:
    content = json.dumps({"label": "ok", "evidence_ids": ["e1"]})


class _Choice:
    message = _Message()


class _ChatResponse:
    id = "chat-fallback-1"
    choices = [_Choice()]
    usage = _Usage()


class _ChatCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _ChatResponse()


class _Chat:
    def __init__(self) -> None:
        self.completions = _ChatCompletions()


class _Client:
    def __init__(self, responses=None) -> None:
        self.responses = responses or _TimeoutResponses()
        self.chat = _Chat()


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            evidence_id="e1",
            text="bounded test evidence",
            source_type=EvidenceSourceType.CALCULATION,
        )
    ]


def test_final_supervisor_retries_responses_once_after_transport_failure() -> None:
    client = _Client(_FailOnceResponses())
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=2,
        client=client,
    )

    result = provider.generate_structured(
        task_name="final_supervision_synthesis",
        prompt_version="v04_final_supervision_v1",
        evidence=_evidence(),
        response_model=_Result,
    )

    assert result == _Result(label="ok", evidence_ids=["e1"])
    assert len(client.responses.calls) == 2
    assert client.chat.completions.calls == []
    assert provider.last_call_metadata is not None
    assert provider.last_call_metadata.provider_name == "openai_responses"
    assert provider.last_call_metadata.model_name == "test-model"
    assert provider.last_call_metadata.request_id == "responses-structured-1"
    assert client.responses.calls[-1]["max_output_tokens"] == 2048
    assert client.responses.calls[-1]["reasoning"] == {"effort": "low"}
    assert "Be concise" in client.responses.calls[-1]["instructions"]


def test_final_supervisor_consecutive_transport_failures_fail_closed_without_chat() -> None:
    client = _Client()
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=2,
        client=client,
    )

    with pytest.raises(LLMProviderError) as captured:
        provider.generate_structured(
            task_name="final_supervision_synthesis",
            prompt_version="v04_final_supervision_v1",
            evidence=_evidence(),
            response_model=_Result,
        )

    assert captured.value.kind.value == "transport"
    assert captured.value.attempts == 2
    assert len(client.responses.calls) == 2
    assert client.chat.completions.calls == []


def test_final_supervisor_invalid_structured_json_remains_validation_failure() -> None:
    client = _Client(_InvalidResponses())
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=2,
        client=client,
    )

    with pytest.raises(LLMProviderError) as captured:
        provider.generate_structured(
            task_name="final_supervision_synthesis",
            prompt_version="v04_final_supervision_v1",
            evidence=_evidence(),
            response_model=_Result,
        )

    assert captured.value.kind.value == "response_validation"
    assert captured.value.attempts == 3
    assert len(client.responses.calls) == 3
    assert client.chat.completions.calls == []
    assert provider.last_failure_diagnostics == {
        "stage": "json_parse",
        "structured_attempt": 3,
        "arguments_length": 1,
        "first_char_class": "json_container",
        "arguments_hash": "021fb596db81e6d02bf3d2586ee3981fe519f275c0ac9ca76bbcf2ebb4097d96",
    }


def test_schema_repair_stays_bounded_when_transport_retries_are_disabled() -> None:
    client = _Client(_InvalidOnceResponses())
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=0,
        client=client,
    )

    result = provider.generate_structured(
        task_name="final_supervision_synthesis",
        prompt_version="v04_final_supervision_v1",
        evidence=_evidence(),
        response_model=_Result,
    )

    assert result == _Result(label="ok", evidence_ids=["e1"])
    assert len(client.responses.calls) == 2
    assert "previous function arguments were not valid JSON" in client.responses.calls[1][
        "instructions"
    ]
    assert client.chat.completions.calls == []


def test_non_supervisor_transport_failure_keeps_normal_responses_retry_policy() -> None:
    client = _Client()
    provider = OpenAIResponsesLLMProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="test-model",
        max_retries=2,
        client=client,
    )

    with pytest.raises(LLMProviderError) as captured:
        provider.generate_structured(
            task_name="generic_test_task",
            prompt_version="generic_test_v1",
            evidence=_evidence(),
            response_model=_Result,
        )

    assert captured.value.kind.value == "transport"
    assert captured.value.attempts == 3
    assert len(client.responses.calls) == 3
    assert client.chat.completions.calls == []
    assert client.responses.calls[-1]["max_output_tokens"] == 2048
    assert client.responses.calls[-1]["reasoning"] == {"effort": "low"}
