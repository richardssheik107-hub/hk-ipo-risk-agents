from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.extraction import ExtractionStatus, ShareholderRightsExtractor, ShareholderRightsFact
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
        text=f"candidate clause {index}",
    )


def test_existing_candidate_model_is_compatibly_extended_for_structured_legal_facts() -> None:
    candidate = ShareholderRightCandidate(
        right_type="redemption_right",
        holder="Series B investors",
        evidence_ids=["e-1"],
    )

    assert candidate.is_effective is None
    assert candidate.termination_event == ""
    assert candidate.termination_timing == ""
    assert candidate.restoration_clause is None
    assert candidate.restoration_condition == ""
    assert candidate.impact_on_public_shareholders == ""
    assert candidate.uncertainty_reason == ""


def test_candidate_schema_rejects_llm_risk_decisions() -> None:
    with pytest.raises(ValidationError):
        ShareholderRightCandidate.model_validate(
            {
                "right_type": "redemption_right",
                "holder": "Series B investors",
                "is_effective": True,
                "evidence_ids": ["e-1"],
                "risk_level": "high",
            }
        )


def test_extractor_calls_llm_for_typed_candidate_only_and_limits_retrieved_evidence() -> None:
    provider = RecordingProvider(
        {
            "right_type": "redemption right",
            "holder": "Series B investors",
            "is_effective": False,
            "termination_event": "listing",
            "termination_timing": "upon listing",
            "restoration_clause": True,
            "restoration_condition": "listing does not occur",
            "impact_on_public_shareholders": "may require cash settlement",
            "evidence_ids": ["e-1", "e-2"],
        }
    )

    result = ShareholderRightsExtractor(provider).extract([_evidence(index) for index in range(1, 12)])

    assert isinstance(result, ShareholderRightsFact)
    assert not isinstance(result, RiskItem)
    assert len(provider.calls) == 1
    assert provider.calls[0]["task_name"] == "shareholder_rights_extract"
    assert provider.calls[0]["prompt_version"] == "legal_shareholder_rights_v1"
    assert provider.calls[0]["response_model"] is ShareholderRightCandidate
    assert [item.evidence_id for item in provider.calls[0]["evidence"]] == [
        f"e-{index}" for index in range(1, 11)
    ]
    assert result.right_type == "redemption_right"
    assert result.termination_event == "listing"
    assert result.termination_timing == "on_listing"
    assert result.restoration_clause is True
    assert result.status == ExtractionStatus.EXTRACTED


def test_extractor_does_not_call_llm_without_retrieved_evidence() -> None:
    provider = RecordingProvider({})

    result = ShareholderRightsExtractor(provider).extract([])

    assert provider.calls == []
    assert result.status == ExtractionStatus.NOT_FOUND
    assert result.issues == ["evidence_not_found"]
    assert result.evidence_ids == []
