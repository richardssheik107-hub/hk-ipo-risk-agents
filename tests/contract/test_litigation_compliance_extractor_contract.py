from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ipo_risk.agents.legal_models import LitigationComplianceCandidate
from ipo_risk.extraction import (
    ExtractionStatus,
    LegalMatterObservation,
    LitigationComplianceExtractor,
)
from ipo_risk.schemas import Evidence, LLMCallMetadata, RiskItem


class RecordingProvider:
    name = "recording"
    last_call_metadata: LLMCallMetadata | None = None

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

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
        self.calls.append(
            {
                "task_name": task_name,
                "prompt_version": prompt_version,
                "evidence": evidence,
                "response_model": response_model,
            }
        )
        return response_model.model_validate(self.payload)


def _evidence(index: int) -> Evidence:
    return Evidence(
        evidence_id=f"e-{index}",
        document_id="ipo-case",
        chunk_id=f"ipo-case:page:{index}",
        page=index,
        text=f"legal matter clause {index}",
    )


def test_existing_litigation_candidate_is_compatibly_extended() -> None:
    candidate = LitigationComplianceCandidate(
        matter_type="litigation",
        current_status="pending",
        evidence_ids=["e-1"],
    )

    assert candidate.subject == ""
    assert candidate.event_date is None
    assert candidate.amount is None
    assert candidate.currency == ""
    assert candidate.is_pending is None
    assert candidate.is_resolved is None
    assert candidate.is_remediated is None
    assert candidate.management_materiality == ""
    assert candidate.license_impact == ""
    assert candidate.uncertainty_reason == ""


def test_candidate_preserves_frozen_default_extra_field_compatibility() -> None:
    candidate = LitigationComplianceCandidate.model_validate(
        {
            "matter_type": "litigation",
            "current_status": "pending",
            "evidence_ids": ["e-1"],
            "risk_level": "high",
        }
    )

    assert candidate.matter_type == "litigation"
    assert not hasattr(candidate, "risk_level")


def test_unified_extractor_uses_one_typed_task_and_limits_evidence() -> None:
    provider = RecordingProvider(
        {
            "matter_type": "material litigation",
            "subject": "MBC contract dispute",
            "counterparty_or_authority": "MBC",
            "event_date": "2020-07-01",
            "amount": "140.9",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "pending",
            "is_pending": True,
            "management_materiality": "material",
            "potential_impact": "cash claim and legal costs",
            "evidence_ids": ["e-1", "e-2"],
        }
    )

    result = LitigationComplianceExtractor(provider).extract(
        [_evidence(index) for index in range(1, 12)]
    )

    assert isinstance(result, LegalMatterObservation)
    assert not isinstance(result, RiskItem)
    assert len(provider.calls) == 1
    assert provider.calls[0]["task_name"] == "litigation_compliance_extract"
    assert provider.calls[0]["prompt_version"] == "legal_litigation_compliance_v1"
    assert provider.calls[0]["response_model"] is LitigationComplianceCandidate
    assert len(provider.calls[0]["evidence"]) == 10
    assert result.matter_type == "litigation"


def test_extractor_does_not_call_llm_without_evidence() -> None:
    provider = RecordingProvider({})

    result = LitigationComplianceExtractor(provider).extract([])

    assert provider.calls == []
    assert result.status == ExtractionStatus.NOT_FOUND
    assert result.issues == ["evidence_not_found"]
