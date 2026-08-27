from __future__ import annotations

from typing import Any

from ipo_risk.agents.business_extraction import DeterministicBusinessExtractor
from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.providers.llm import UnavailableLLMProvider
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import (
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    IPOProfile,
    VerificationStatus,
)


class StaticRetriever:
    def __init__(self, evidence: list[Evidence]) -> None:
        self.evidence = evidence

    def retrieve(self, chunks, query, limit=3):
        return self.evidence[:limit]


class ExplodingRetriever:
    def retrieve(self, chunks, query, limit=3):
        raise RuntimeError("private retrieval payload")


class ExplodingExtractor(DeterministicBusinessExtractor):
    def extract(self, evidence):
        raise RuntimeError("private extraction payload")


def chunk(text: str, *, section: str = "業務") -> DocumentChunk:
    return DocumentChunk(document_id="doc", chunk_id="c1", page=10, section=section, text=text)


def evidence_for(item: DocumentChunk, *, evidence_id: str = "e1", **updates: Any) -> Evidence:
    payload = {
        "evidence_id": evidence_id,
        "document_id": item.document_id,
        "chunk_id": item.chunk_id,
        "page": item.page,
        "section": item.section,
        "text": item.text,
    }
    payload.update(updates)
    return Evidence(**payload)


def agent_for(text: str, **kwargs):
    item = chunk(text)
    return V03BusinessAgent(retriever=StaticRetriever([evidence_for(item)]), **kwargs), [item]


POSITIVE = (
    "ABC-101（我們的核心產品）處於臨床III期，尚未商業化，"
    "尚未從產品銷售產生任何收入。"
)
NEGATIVE = (
    "ABC-101 (our core product) was commercially launched. "
    "Revenue generated from sales of ABC-101 products amounted to RMB 10 million."
)


def test_clean_positive_returns_one_pending_owned_risk() -> None:
    agent, chunks = agent_for(POSITIVE)
    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)
    assert len(risks) == 1
    risk = risks[0]
    assert risk.risk_code == "precommercial_product"
    assert risk.category.value == "business"
    assert risk.level.value == "medium"
    assert risk.score == 60
    assert risk.verification_status == VerificationStatus.PENDING
    assert risk.calculation is None
    assert agent.last_diagnostics[0].code == DiagnosticCode.RISK_GENERATED


def test_clean_negative_is_not_applicable() -> None:
    agent, chunks = agent_for(NEGATIVE)
    assert agent.analyze(IPOProfile(company_name="Demo"), chunks) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.NOT_APPLICABLE


def test_non_product_revenue_does_not_cancel_positive() -> None:
    for source in ("licensing revenue", "milestone income", "R&D service revenue", "collaboration revenue"):
        agent, chunks = agent_for(f"{POSITIVE} The company records {source} only.")
        risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)
        assert len(risks) == 1
        assert risks[0].metadata["has_product_revenue"] is False


def test_ambiguous_revenue_needs_review() -> None:
    agent, chunks = agent_for(
        "ABC-101 (our core product) is in Phase III and not yet commercialized. The company recorded revenue."
    )
    assert agent.analyze(IPOProfile(company_name="Demo"), chunks) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.NEEDS_REVIEW


def test_conflicting_revenue_is_reported() -> None:
    agent, chunks = agent_for(f"{POSITIVE} Revenue generated from sales of ABC-101 products amounted to RMB 10 million.")
    assert agent.analyze(IPOProfile(company_name="Demo"), chunks) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.CONFLICTING_VALUES


def test_no_evidence_and_retriever_failure_are_distinct() -> None:
    no_evidence = V03BusinessAgent(retriever=StaticRetriever([]))
    assert no_evidence.analyze(IPOProfile(company_name="Demo"), []) == []
    assert no_evidence.last_diagnostics[0].code == DiagnosticCode.EVIDENCE_NOT_FOUND

    failed = V03BusinessAgent(retriever=ExplodingRetriever())
    assert failed.analyze(IPOProfile(company_name="Demo"), [chunk(POSITIVE)]) == []
    assert failed.last_diagnostics[0].code == DiagnosticCode.COMPONENT_FAILURE
    assert "private" not in failed.last_diagnostics[0].message


def test_invalid_evidence_identity_blocks_risk() -> None:
    item = chunk(POSITIVE)
    invalid = evidence_for(item, chunk_id="missing")
    agent = V03BusinessAgent(retriever=StaticRetriever([invalid]))
    assert agent.analyze(IPOProfile(company_name="Demo"), [item]) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.NEEDS_REVIEW


def test_valid_mock_llm_can_fill_missing_product_revenue_fact() -> None:
    text = "ABC-101 (our core product) is in Phase III and not yet commercialized."
    item = chunk(text)
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC-101",
                "development_stage": "phase_iii",
                "has_product_revenue": False,
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
    agent = V03BusinessAgent(retriever=StaticRetriever([evidence_for(item)]), llm_provider=provider)
    risks = agent.analyze(IPOProfile(company_name="Demo"), [item])
    assert len(risks) == 1
    assert agent.last_diagnostics[0].metadata["llm_cross_check"] == "consistent"


def test_llm_evidence_out_of_scope_preserves_deterministic_risk() -> None:
    item = chunk(POSITIVE)
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC-101", "development_stage": "phase_iii",
                "has_product_revenue": False, "evidence_ids": ["outside"],
            },
            "business_precommercial_core_product_extract": {
                "product_name": "ABC-101", "is_core_product": True,
                "launch_status": "not_launched", "evidence_ids": ["e1"],
            },
        }
    )
    agent = V03BusinessAgent(retriever=StaticRetriever([evidence_for(item)]), llm_provider=provider)
    risks = agent.analyze(IPOProfile(company_name="Demo"), [item])
    assert len(risks) == 1
    assert risks[0].verification_status == VerificationStatus.PENDING
    assert risks[0].metadata["has_product_revenue"] is False
    assert agent.last_diagnostics[0].code == DiagnosticCode.NEEDS_REVIEW
    assert agent.last_diagnostics[0].metadata["issue"] == "evidence_out_of_scope"
    assert agent.last_diagnostics[0].metadata["llm_augmentation_applied"] is False
    assert agent.last_diagnostics[0].metadata["deterministic_candidate_preserved"] is True


def test_llm_conflict_does_not_override_deterministic_fact() -> None:
    item = chunk(POSITIVE)
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC-101", "development_stage": "phase_iii",
                "has_product_revenue": True, "evidence_ids": ["e1"],
            },
            "business_precommercial_core_product_extract": {
                "product_name": "ABC-101", "is_core_product": True,
                "launch_status": "not_launched", "evidence_ids": ["e1"],
            },
        }
    )
    agent = V03BusinessAgent(retriever=StaticRetriever([evidence_for(item)]), llm_provider=provider)
    risks = agent.analyze(IPOProfile(company_name="Demo"), [item])
    assert len(risks) == 1
    assert risks[0].verification_status == VerificationStatus.PENDING
    assert risks[0].metadata["has_product_revenue"] is False
    assert agent.last_diagnostics[0].code == DiagnosticCode.CONFLICTING_VALUES
    assert agent.last_diagnostics[0].metadata["issue"] == "candidate_conflict"
    assert agent.last_diagnostics[0].metadata["llm_conflicts"] == ["product_revenue"]
    assert agent.last_diagnostics[0].metadata["llm_augmentation_applied"] is False
    assert agent.last_diagnostics[0].metadata["deterministic_candidate_preserved"] is True


def test_llm_conflict_cannot_turn_deterministic_negative_into_a_risk() -> None:
    item = chunk(NEGATIVE)
    provider = MockLLMProvider(
        responses={
            "business_precommercial_commercialization_extract": {
                "product_name": "ABC-101", "development_stage": "phase_iii",
                "has_product_revenue": False, "evidence_ids": ["e1"],
            },
            "business_precommercial_core_product_extract": {
                "product_name": "ABC-101", "is_core_product": True,
                "launch_status": "not_launched", "evidence_ids": ["e1"],
            },
        }
    )
    agent = V03BusinessAgent(retriever=StaticRetriever([evidence_for(item)]), llm_provider=provider)

    assert agent.analyze(IPOProfile(company_name="Demo"), [item]) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.NOT_APPLICABLE
    assert agent.last_diagnostics[0].metadata["issue"] == "candidate_conflict"
    assert agent.last_diagnostics[0].metadata["deterministic_candidate_preserved"] is True


def test_unavailable_llm_does_not_block_sufficient_deterministic_facts() -> None:
    agent, chunks = agent_for(POSITIVE, llm_provider=UnavailableLLMProvider())
    assert len(agent.analyze(IPOProfile(company_name="Demo"), chunks)) == 1
    assert agent.last_diagnostics[0].metadata["llm_failure_kind"] == "unavailable"


def test_llm_failure_with_insufficient_facts_degrades_honestly() -> None:
    agent, chunks = agent_for(
        "ABC-101 (our core product) is in Phase III.",
        llm_provider=UnavailableLLMProvider(),
    )
    assert agent.analyze(IPOProfile(company_name="Demo"), chunks) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.NEEDS_REVIEW


def test_extractor_failure_is_isolated() -> None:
    agent, chunks = agent_for(POSITIVE, extractor=ExplodingExtractor())
    assert agent.analyze(IPOProfile(company_name="Demo"), chunks) == []
    assert agent.last_diagnostics[0].code == DiagnosticCode.COMPONENT_FAILURE


def test_repeated_analysis_resets_diagnostics_and_risk_id_is_stable() -> None:
    agent, chunks = agent_for(POSITIVE)
    first = agent.analyze(IPOProfile(company_name="Demo"), chunks)
    second = agent.analyze(IPOProfile(company_name="Demo"), chunks)
    assert len(agent.last_diagnostics) == 1
    assert first[0].risk_id == second[0].risk_id
    assert first[0].calculation is None
    assert first[0].metadata["score_is_rule_based"] is True
    assert first[0].metadata["score_is_probability"] is False
