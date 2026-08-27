from __future__ import annotations

import pytest

from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.providers.prompt_registry import PromptResolutionError, resolve_domain_instruction
from ipo_risk.schemas import (
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    IPOProfile,
    VerificationStatus,
)


class _StaticRetriever:
    def __init__(self, evidence: list[Evidence]) -> None:
        self.evidence = evidence

    def retrieve(self, chunks, query, limit=3):
        return self.evidence[:limit]


def _business_case():
    text = (
        "ABC-101（我們的核心產品）處於臨床III期，尚未商業化，"
        "尚未從產品銷售產生任何收入。"
    )
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="c1",
        page=10,
        section="業務",
        text=text,
    )
    evidence = Evidence(
        evidence_id="e1",
        document_id="doc",
        chunk_id="c1",
        page=10,
        section="業務",
        text=text,
    )
    return chunk, evidence


def test_registered_domain_prompts_define_schema_safe_canonical_vocabularies():
    legal = resolve_domain_instruction(
        "litigation_compliance_extract", "legal_litigation_compliance_v1"
    )
    business = resolve_domain_instruction(
        "business_precommercial_commercialization_extract",
        "business_precommercial_v1",
    )

    assert legal is not None
    assert "current_status must be one of" in legal
    assert "literal string unknown instead of" in legal
    assert business is not None
    assert "phase_iii" in business
    assert "direct product-sales revenue" in business


def test_business_prompt_identity_is_fail_closed_when_version_is_mismatched():
    with pytest.raises(PromptResolutionError):
        resolve_domain_instruction(
            "business_precommercial_core_product_extract",
            "business_precommercial_v999",
        )


def test_equivalent_llm_business_formatting_does_not_create_false_conflict():
    chunk, evidence = _business_case()
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC101",
                "development_stage": "Phase III",
                "has_product_revenue": False,
                "evidence_ids": ["e1"],
            },
            "business_precommercial_core_product_extract": {
                "product_name": "ABC 101",
                "is_core_product": True,
                "launch_status": "not yet launched",
                "evidence_ids": ["e1"],
            },
        }
    )
    agent = V03BusinessAgent(
        retriever=_StaticRetriever([evidence]),
        llm_provider=provider,
    )

    risks = agent.analyze(IPOProfile(company_name="Demo"), [chunk])

    assert len(risks) == 1
    diagnostic = agent.last_diagnostics[0]
    assert diagnostic.code == DiagnosticCode.RISK_GENERATED
    assert diagnostic.metadata["llm_cross_check"] == "consistent"
    assert diagnostic.metadata["llm_normalization"] == "business_candidate_canonical_v1"


def test_true_business_semantic_conflict_discards_llm_but_preserves_deterministic_risk():
    chunk, evidence = _business_case()
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC-101",
                "development_stage": "phase_iii",
                "has_product_revenue": True,
                "evidence_ids": ["e1"],
            },
            "business_precommercial_core_product_extract": {
                "product_name": "ABC-101",
                "is_core_product": True,
                "launch_status": "not_launched",
                "evidence_ids": ["e1"],
            },
        }
    )
    agent = V03BusinessAgent(
        retriever=_StaticRetriever([evidence]),
        llm_provider=provider,
    )

    risks = agent.analyze(IPOProfile(company_name="Demo"), [chunk])

    assert len(risks) == 1
    assert risks[0].verification_status == VerificationStatus.PENDING
    assert risks[0].metadata["has_product_revenue"] is False
    diagnostic = agent.last_diagnostics[0]
    assert diagnostic.code == DiagnosticCode.CONFLICTING_VALUES
    assert diagnostic.metadata["llm_conflicts"] == ["product_revenue"]
    assert diagnostic.metadata["llm_augmentation_applied"] is False
    assert diagnostic.metadata["deterministic_candidate_preserved"] is True
