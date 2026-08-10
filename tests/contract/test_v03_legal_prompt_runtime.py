from __future__ import annotations

import json
from types import SimpleNamespace

from pydantic import BaseModel
import pytest

from ipo_risk.providers.llm import (
    LLMFailureKind,
    LLMProviderError,
    OpenAICompatibleLLMProvider,
)
from ipo_risk.providers.prompt_registry import (
    LITIGATION_COMPLIANCE_INSTRUCTION,
    SHAREHOLDER_RIGHTS_INSTRUCTION,
    PromptResolutionError,
    resolve_domain_instruction,
)
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import Evidence


class Candidate(BaseModel):
    finding: str


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="safe-response",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"finding":"supported"}')
                )
            ],
            usage=None,
        )


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def _provider() -> tuple[OpenAICompatibleLLMProvider, FakeClient]:
    client = FakeClient()
    provider = OpenAICompatibleLLMProvider(
        api_key="synthetic-test-key",
        base_url="https://llm.invalid/v1",
        model="test-model",
        client=client,
    )
    return provider, client


def _evidence() -> Evidence:
    return Evidence(
        evidence_id="legal-evidence-1",
        document_id="synthetic-document",
        chunk_id="synthetic-document:7",
        page=7,
        section="legal",
        text="The supplied Evidence contains the only supported legal fact.",
    )


@pytest.mark.parametrize(
    ("task_name", "prompt_version", "expected"),
    [
        (
            "shareholder_rights_extract",
            "legal_shareholder_rights_v1",
            SHAREHOLDER_RIGHTS_INSTRUCTION,
        ),
        (
            "litigation_compliance_extract",
            "legal_litigation_compliance_v1",
            LITIGATION_COMPLIANCE_INSTRUCTION,
        ),
    ],
)
def test_legal_prompt_resolution_is_exact_and_deterministic(
    task_name: str, prompt_version: str, expected: str
) -> None:
    assert resolve_domain_instruction(task_name, prompt_version) == expected
    assert resolve_domain_instruction(task_name, prompt_version) == expected


@pytest.mark.parametrize(
    ("task_name", "prompt_version"),
    [
        ("shareholder_rights_extract", "legal_shareholder_rights_v2"),
        ("litigation_compliance_extract", "legal_shareholder_rights_v1"),
        ("business_extract", "legal_litigation_compliance_v1"),
    ],
)
def test_unknown_or_mismatched_legal_prompt_fails_closed(
    task_name: str, prompt_version: str
) -> None:
    with pytest.raises(PromptResolutionError):
        resolve_domain_instruction(task_name, prompt_version)

    provider, client = _provider()
    with pytest.raises(LLMProviderError) as caught:
        provider.generate_structured(
            task_name=task_name,
            prompt_version=prompt_version,
            evidence=[_evidence()],
            response_model=Candidate,
        )
    assert caught.value.kind == LLMFailureKind.REQUEST
    assert caught.value.recoverable is False
    assert caught.value.attempts == 0
    assert client.completions.calls == []
    assert task_name not in str(caught.value)
    assert prompt_version not in str(caught.value)


@pytest.mark.parametrize(
    ("task_name", "prompt_version", "instruction"),
    [
        (
            "shareholder_rights_extract",
            "legal_shareholder_rights_v1",
            SHAREHOLDER_RIGHTS_INSTRUCTION,
        ),
        (
            "litigation_compliance_extract",
            "legal_litigation_compliance_v1",
            LITIGATION_COMPLIANCE_INSTRUCTION,
        ),
    ],
)
def test_real_request_contains_domain_instruction_schema_and_selected_evidence(
    task_name: str, prompt_version: str, instruction: str
) -> None:
    provider, client = _provider()
    selected = _evidence()

    result = provider.generate_structured(
        task_name=task_name,
        prompt_version=prompt_version,
        evidence=[selected],
        response_model=Candidate,
    )

    assert result == Candidate(finding="supported")
    call = client.completions.calls[0]
    messages = call["messages"]
    assert messages[0]["role"] == "system"
    assert instruction in messages[0]["content"]
    assert "matching response_schema" in messages[0]["content"]
    payload = json.loads(messages[1]["content"])
    assert payload["response_schema"] == Candidate.model_json_schema()
    assert payload["evidence"] == [
        {
            "evidence_id": selected.evidence_id,
            "document_id": selected.document_id,
            "chunk_id": selected.chunk_id,
            "page": selected.page,
            "section": selected.section,
            "text": selected.text,
            "source_type": selected.source_type.value,
            "relevance_score": selected.relevance_score,
        }
    ]
    assert call["response_format"] == {"type": "json_object"}


def test_unrelated_structured_request_remains_generic_and_compatible() -> None:
    assert resolve_domain_instruction("business_extract", "business_v1") is None
    provider, client = _provider()

    provider.generate_structured(
        task_name="business_extract",
        prompt_version="business_v1",
        evidence=[_evidence()],
        response_model=Candidate,
    )

    system_content = client.completions.calls[0]["messages"][0]["content"]
    assert system_content == "Return exactly one JSON object matching response_schema."
    assert "Domain extraction instruction" not in system_content


def test_mock_uses_same_legal_identity_guard_and_remains_deterministic() -> None:
    provider = MockLLMProvider(
        {"shareholder_rights_extract": {"finding": "supported"}}
    )
    result = provider.generate_structured(
        task_name="shareholder_rights_extract",
        prompt_version="legal_shareholder_rights_v1",
        evidence=[_evidence()],
        response_model=Candidate,
    )
    assert result == Candidate(finding="supported")

    with pytest.raises(LLMProviderError) as caught:
        provider.generate_structured(
            task_name="shareholder_rights_extract",
            prompt_version="legal_shareholder_rights_v2",
            evidence=[_evidence()],
            response_model=Candidate,
        )
    assert caught.value.kind == LLMFailureKind.REQUEST
    assert caught.value.attempts == 0


@pytest.mark.parametrize(
    "instruction",
    [SHAREHOLDER_RIGHTS_INSTRUCTION, LITIGATION_COMPLIANCE_INSTRUCTION],
)
def test_legal_instructions_preserve_frozen_safety_boundary(instruction: str) -> None:
    normalized = " ".join(instruction.lower().split())
    assert "supplied evidence" in normalized
    assert "evidence_ids" in normalized
    if instruction == LITIGATION_COMPLIANCE_INSTRUCTION:
        assert "closed/remediated" in normalized
    assert "risk score" in normalized
    assert "risk level" in normalized
    assert "verification status" in normalized
    assert "investment recommendation" in normalized
