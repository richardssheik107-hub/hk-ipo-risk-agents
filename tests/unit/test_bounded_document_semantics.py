from __future__ import annotations

import pytest
from pydantic import ValidationError

from ipo_risk.extraction.bounded_semantics import (
    BusinessSemanticFact,
    DisclosureToneFact,
    EvidenceScopeError,
    PipelineStage,
    RelatedPartyTransactionFact,
    RevenueSource,
    SemanticStatus,
    extract_scoped,
    reconcile_business_fact,
    validate_evidence_scope,
)
from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError, UnavailableLLMProvider
from ipo_risk.schemas import Evidence


def _evidence(evidence_id: str = "e-1") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="doc-1",
        chunk_id="doc-1:page:8",
        page=8,
        text="Bounded disclosure text.",
    )


class StaticProvider:
    name = "stub"

    def __init__(self, payload):
        self.payload = payload

    def generate_structured(self, **kwargs):
        return kwargs["response_model"].model_validate(self.payload)


def test_business_semantic_contract_distinguishes_product_sales_from_licensing() -> None:
    fact = BusinessSemanticFact(
        product_name="ABC-101",
        is_core_product=True,
        pipeline_stage=PipelineStage.PHASE_III,
        is_commercialized=False,
        has_product_sales_revenue=False,
        revenue_sources=[RevenueSource.LICENSING, RevenueSource.MILESTONE],
        evidence_ids=["e-1"],
    )
    assert fact.pipeline_stage is PipelineStage.PHASE_III
    assert RevenueSource.PRODUCT_SALES not in fact.revenue_sources


def test_related_party_fact_is_private_structured_proposal() -> None:
    fact = RelatedPartyTransactionFact(
        counterparty="Controlling shareholder",
        relationship="controller",
        transaction_nature="continuing service agreement",
        is_ongoing=True,
        evidence_ids=["e-1"],
    )
    assert fact.is_ongoing is True


def test_scope_guard_rejects_out_of_scope_evidence() -> None:
    fact = BusinessSemanticFact(product_name="ABC", evidence_ids=["invented"])
    with pytest.raises(EvidenceScopeError):
        validate_evidence_scope(fact, [_evidence()])


def test_scope_guard_rejects_duplicate_evidence_ids() -> None:
    fact = DisclosureToneFact(supporting_evidence_ids=["e-1", "e-1"])
    with pytest.raises(EvidenceScopeError):
        validate_evidence_scope(fact, [_evidence()])


def test_extract_scoped_rejects_invalid_structured_response() -> None:
    provider = StaticProvider({"product_name": "ABC", "evidence_ids": []})
    with pytest.raises(ValidationError):
        extract_scoped(
            provider,
            task_name="business_semantic_extract",
            prompt_version="private_test_v1",
            evidence=[_evidence()],
            response_model=BusinessSemanticFact,
        )


def test_llm_unavailable_degrades_without_network() -> None:
    with pytest.raises(LLMProviderError) as raised:
        extract_scoped(
            UnavailableLLMProvider(),
            task_name="business_semantic_extract",
            prompt_version="private_test_v1",
            evidence=[_evidence()],
            response_model=BusinessSemanticFact,
        )
    assert raised.value.kind is LLMFailureKind.UNAVAILABLE


def test_deterministic_fact_conflict_is_not_overwritten() -> None:
    llm = BusinessSemanticFact(
        product_name="ABC-101",
        is_commercialized=True,
        has_product_sales_revenue=True,
        evidence_ids=["e-1"],
    )
    result = reconcile_business_fact(
        {
            "product_name": "ABC-101",
            "is_commercialized": False,
            "has_product_sales_revenue": False,
        },
        llm,
    )
    assert result.status is SemanticStatus.NEEDS_REVIEW
    assert result.facts["is_commercialized"] is False
    assert result.facts["has_product_sales_revenue"] is False
    assert result.conflicts == ["is_commercialized", "has_product_sales_revenue"]


def test_disclosure_tone_requires_bounded_support() -> None:
    fact = DisclosureToneFact(
        tone_risk=True,
        hedging_language=["may"],
        obfuscation_signal=True,
        missing_quantification=True,
        supporting_evidence_ids=["e-1"],
    )
    assert validate_evidence_scope(fact, [_evidence()]) is fact
