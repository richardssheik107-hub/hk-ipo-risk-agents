from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from ipo_risk.extraction import (
    ExtractionStatus,
    LegalMatterEvidenceKind,
    LitigationComplianceExtractor,
    classify_legal_matter_evidence,
)
from ipo_risk.schemas import Evidence, LLMCallMetadata


class FailIfCalledProvider:
    name = "must-not-be-called"
    last_call_metadata: LLMCallMetadata | None = None

    def complete(self, prompt: str) -> str:
        raise AssertionError("LLM must not be called for deterministic negative/template text")

    def generate_structured(self, **kwargs):
        raise AssertionError("LLM must not be called for deterministic negative/template text")


class RecordingProvider:
    name = "recording"
    last_call_metadata: LLMCallMetadata | None = None

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, prompt: str) -> str:
        return "unused"

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[BaseModel],
    ) -> BaseModel:
        self.calls += 1
        return response_model.model_validate(self.payload)


def _evidence(text: str, evidence_id: str = "e-legal") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id=f"ipo-case:{evidence_id}",
        page=1,
        text=text,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "The Group is not involved in any material litigation.",
            LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
        ),
        (
            "董事确认本集团不存在任何重大诉讼。",
            LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
        ),
        (
            "The company is not currently subject to litigation.",
            LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
        ),
        (
            "No proceedings remain pending before the High Court.",
            LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
        ),
        (
            "The regulator did not impose a penalty on the company.",
            LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
        ),
        (
            "We may be exposed to litigation in the future.",
            LegalMatterEvidenceKind.GENERIC_FUTURE_RISK,
        ),
        (
            "In the ordinary course of business, the Group may from time to time "
            "become involved in legal proceedings.",
            LegalMatterEvidenceKind.TEMPLATE_STATEMENT,
        ),
    ],
)
def test_negative_and_template_language_is_classified_without_creating_an_event(
    text: str, expected: LegalMatterEvidenceKind
) -> None:
    assert classify_legal_matter_evidence(_evidence(text)).kind == expected


@pytest.mark.parametrize(
    "text",
    [
        "The company is currently subject to litigation brought by a supplier.",
        "Proceedings remain pending before the High Court.",
        "The regulator imposed a penalty of RMB 2 million.",
        "The licence has not yet been renewed.",
        "本公司涉及的诉讼仍在审理中。",
    ],
)
def test_actual_event_language_has_priority(text: str) -> None:
    assert (
        classify_legal_matter_evidence(_evidence(text)).kind
        == LegalMatterEvidenceKind.ACTUAL_MATTER
    )


@pytest.mark.parametrize(
    "text",
    [
        "The Group is not involved in any material litigation.",
        "董事确认本集团不存在任何重大诉讼。",
        "The company is not currently subject to litigation.",
        "No proceedings remain pending before the High Court.",
        "The regulator did not impose a penalty on the company.",
        "We may be exposed to litigation in the future.",
        "In the ordinary course of business, we may from time to time become involved "
        "in legal proceedings.",
    ],
)
def test_extractor_short_circuits_clear_negative_or_template_evidence(text: str) -> None:
    result = LitigationComplianceExtractor(FailIfCalledProvider()).extract([_evidence(text)])

    assert result.matter_type == "none"
    assert result.current_status == "not_applicable"
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.metadata["extraction_short_circuit"] == "deterministic_no_actual_matter"


def test_actual_matter_prevents_negative_statement_from_short_circuiting_llm() -> None:
    provider = RecordingProvider(
        {
            "matter_type": "litigation",
            "subject": "supplier claim",
            "counterparty_or_authority": "supplier",
            "event_date": "2023-01-01",
            "amount": "2",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "pending",
            "management_materiality": "material",
            "potential_impact": "cash claim and legal costs",
            "evidence_ids": ["e-actual"],
        }
    )
    evidence = [
        _evidence("Proceedings remain pending before the High Court.", "e-actual"),
        _evidence("The Group is not involved in any other material litigation.", "e-negative"),
    ]

    result = LitigationComplianceExtractor(provider).extract(evidence)

    assert provider.calls == 1
    assert result.matter_type == "litigation"
    assert result.is_pending is True
