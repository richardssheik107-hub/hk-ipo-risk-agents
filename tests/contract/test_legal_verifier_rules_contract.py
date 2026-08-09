from __future__ import annotations

from pydantic import TypeAdapter

from ipo_risk.domain.legal_verifiers import (
    LegalRightsVerifier,
    LegalVerificationResult,
    LitigationComplianceVerifier,
)
from ipo_risk.schemas import Evidence, RiskCategory, RiskItem, RiskLevel, VerificationStatus


def _risk(risk_code: str, canonical_code: str, evidence: Evidence) -> RiskItem:
    return RiskItem(
        risk_code=risk_code,
        category=RiskCategory.LEGAL,
        risk_type="legal risk",
        level=RiskLevel.MEDIUM,
        score=50,
        conclusion="Requires legal verification.",
        evidence=[evidence],
        agent_name="legal",
        verification_status=VerificationStatus.PENDING,
        metadata={
            "canonical_code": canonical_code,
            "holder": "Series B investors",
            "survives_listing": True,
            "restoration_clause": False,
            "matter_type": "litigation",
            "management_materiality": "material",
            "potential_impact": "operational loss",
            "builder_issues": [],
            "fact_issues": [],
            "observation_issues": [],
        },
    )


def test_legal_verifier_result_is_serializable_and_deterministic() -> None:
    evidence = Evidence(
        evidence_id="e-right",
        document_id="ipo-case",
        chunk_id="ipo-case:20",
        page=20,
        text=(
            "Under the Pre-IPO Investment Agreement, Series B investors hold redemption "
            "rights that survive the Listing and remain effective after Listing."
        ),
    )
    risk = _risk("redemption_rights", "LEGAL_REDEMPTION_RIGHTS", evidence)
    verifier = LegalRightsVerifier()

    first = verifier.verify(risk, {evidence.evidence_id: evidence})
    second = verifier.verify(risk, {evidence.evidence_id: evidence})
    restored = TypeAdapter(LegalVerificationResult).validate_json(
        first.model_dump_json()
    )

    assert first == second
    assert restored == first
    assert first.status == VerificationStatus.VERIFIED


def test_domain_verifiers_do_not_change_public_verifier_signature() -> None:
    assert LegalRightsVerifier.risk_code == "redemption_rights"
    assert LitigationComplianceVerifier.risk_code == "material_litigation_compliance"
    assert "available_evidence" in LegalRightsVerifier.verify.__annotations__
    assert "available_evidence" in LitigationComplianceVerifier.verify.__annotations__
