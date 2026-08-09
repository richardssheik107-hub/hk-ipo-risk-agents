from __future__ import annotations

import pytest

from ipo_risk.agents.legal import LegalAgent
from ipo_risk.domain.legal_verifiers import (
    LegalRightsVerifier,
    LitigationComplianceVerifier,
)
from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError, UnavailableLLMProvider
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DiagnosticCode, DocumentChunk, IPOProfile, VerificationStatus


RIGHTS_TEXT = (
    "Under the Pre-IPO Investment Agreement, Series B investors hold redemption rights. "
    "The rights survive the Listing and remain effective after Listing."
)
LITIGATION_TEXT = (
    "Material litigation is pending before the High Court. Management considers the claim "
    "material and it may cause operational loss."
)


def _chunk(chunk_id: str, page: int, section: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        document_id="synthetic-ipo",
        chunk_id=chunk_id,
        page=page,
        section=section,
        text=text,
    )


def _positive_chunks() -> list[DocumentChunk]:
    return [
        _chunk("rights-page", 20, "history and reorganisation", RIGHTS_TEXT),
        _chunk("litigation-page", 30, "legal proceedings", LITIGATION_TEXT),
    ]


def _responses(retriever: KeywordDocumentRetriever, chunks: list[DocumentChunk]):
    rights = retriever.retrieve(chunks, "redemption_rights", limit=10)
    litigation = retriever.retrieve(
        chunks, "material_litigation_compliance", limit=10
    )
    return {
        "shareholder_rights_extract": {
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": True,
            "survives_listing": True,
            "termination_timing": "after_listing",
            "restoration_clause": False,
            "impact_on_public_shareholders": "preferential exit right",
            "evidence_ids": [rights[0].evidence_id],
        },
        "litigation_compliance_extract": {
            "matter_type": "litigation",
            "subject": "High Court claim",
            "counterparty_or_authority": "claimant",
            "current_status": "pending",
            "is_pending": True,
            "is_resolved": False,
            "management_materiality": "material",
            "potential_impact": "operational loss",
            "evidence_ids": [litigation[0].evidence_id],
        },
    }


class ErrorProvider:
    name = "error"
    last_call_metadata = None

    def __init__(self, kind: LLMFailureKind) -> None:
        self.kind = kind

    def complete(self, prompt: str) -> str:
        raise AssertionError("unused")

    def generate_structured(self, **kwargs):
        raise LLMProviderError(
            self.kind,
            "safe integration failure",
            recoverable=self.kind == LLMFailureKind.TRANSPORT,
            attempts=2,
        )


def test_real_query_families_preserve_traceability_and_stable_evidence_ids() -> None:
    retriever = KeywordDocumentRetriever()
    chunks = _positive_chunks()

    first_rights = retriever.retrieve(chunks, "redemption_rights", limit=10)
    second_rights = retriever.retrieve(chunks, "redemption_rights", limit=10)
    litigation = retriever.retrieve(
        chunks, "material_litigation_compliance", limit=10
    )

    assert first_rights
    assert litigation
    assert [item.evidence_id for item in first_rights] == [
        item.evidence_id for item in second_rights
    ]
    assert first_rights[0].page == 20
    assert first_rights[0].chunk_id == "rights-page"
    assert litigation[0].page == 30
    assert litigation[0].chunk_id == "litigation-page"


def test_mock_provider_runs_public_retriever_agent_builders_and_verifiers() -> None:
    retriever = KeywordDocumentRetriever()
    chunks = _positive_chunks()
    agent = LegalAgent(
        retriever=retriever,
        llm_provider=MockLLMProvider(_responses(retriever, chunks)),
    )

    risks = agent.analyze(IPOProfile(company_name="Synthetic IPO"), chunks)

    assert {item.risk_code for item in risks} == {
        "redemption_rights",
        "material_litigation_compliance",
    }
    assert all(item.verification_status == VerificationStatus.PENDING for item in risks)
    rights = next(item for item in risks if item.risk_code == "redemption_rights")
    litigation = next(
        item for item in risks if item.risk_code == "material_litigation_compliance"
    )
    rights_result = LegalRightsVerifier().verify(
        rights, {item.evidence_id: item for item in rights.evidence}
    )
    litigation_result = LitigationComplianceVerifier().verify(
        litigation, {item.evidence_id: item for item in litigation.evidence}
    )
    assert rights_result.status == VerificationStatus.VERIFIED
    assert litigation_result.status == VerificationStatus.VERIFIED


def test_unavailable_provider_degrades_one_component_while_negative_other_completes() -> None:
    chunks = [
        _chunk("rights-page", 20, "history and reorganisation", RIGHTS_TEXT),
        _chunk(
            "negative-litigation",
            31,
            "legal proceedings",
            "The Group is not involved in any material litigation.",
        ),
    ]
    agent = LegalAgent(
        retriever=KeywordDocumentRetriever(),
        llm_provider=UnavailableLLMProvider("integration unavailable"),
    )

    assert agent.analyze(IPOProfile(company_name="Synthetic IPO"), chunks) == []

    by_code = {item.risk_code: item for item in agent.last_diagnostics}
    assert by_code["redemption_rights"].code == DiagnosticCode.EXTRACTION_FAILED
    assert "llm_provider_unavailable" in by_code["redemption_rights"].metadata[
        "internal_issue_codes"
    ]
    assert by_code["material_litigation_compliance"].code == DiagnosticCode.NOT_APPLICABLE
    assert "negation_detected" in by_code["material_litigation_compliance"].metadata[
        "internal_issue_codes"
    ]


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [
        (LLMFailureKind.UNAVAILABLE, DiagnosticCode.EXTRACTION_FAILED),
        (LLMFailureKind.RESPONSE_VALIDATION, DiagnosticCode.EXTRACTION_FAILED),
        (LLMFailureKind.TRANSPORT, DiagnosticCode.COMPONENT_FAILURE),
    ],
)
def test_public_provider_errors_are_isolated_and_safely_classified(
    kind: LLMFailureKind, expected_code: DiagnosticCode
) -> None:
    agent = LegalAgent(
        retriever=KeywordDocumentRetriever(),
        llm_provider=ErrorProvider(kind),
    )

    assert agent.analyze(IPOProfile(company_name="Synthetic IPO"), _positive_chunks()) == []
    assert len(agent.last_diagnostics) == 2
    for diagnostic in agent.last_diagnostics:
        assert diagnostic.code == expected_code
        assert diagnostic.metadata["failure_kind"] == kind.value
        assert diagnostic.metadata["attempts"] == 2
        assert "safe integration failure" not in diagnostic.message
