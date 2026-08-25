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
    def __init__(self) -> None:
        self.responses = _TimeoutResponses()
        self.chat = _Chat()


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            evidence_id="e1",
            text="bounded test evidence",
            source_type=EvidenceSourceType.CALCULATION,
        )
    ]


def test_final_supervisor_transport_failure_falls_back_once_to_same_model_chat_json() -> None:
    client = _Client()
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
    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 1
    assert client.chat.completions.calls[0]["model"] == "test-model"
    assert client.chat.completions.calls[0]["response_format"] == {"type": "json_object"}
    assert provider.last_call_metadata is not None
    assert provider.last_call_metadata.provider_name == "openai_responses_chat_fallback"
    assert provider.last_call_metadata.model_name == "test-model"
    assert provider.last_call_metadata.request_id == "chat-fallback-1"


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
