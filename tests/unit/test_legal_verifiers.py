from __future__ import annotations

from ipo_risk.domain.legal_verifiers import (
    LegalRightsVerifier,
    LitigationComplianceVerifier,
)
from ipo_risk.domain.material_litigation_compliance import (
    MaterialLitigationComplianceBuildStatus,
    MaterialLitigationComplianceRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, LegalMatterObservation
from ipo_risk.schemas import (
    Evidence,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


def _evidence(text: str, evidence_id: str = "e-legal", page: int = 20) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id=f"ipo-case:page:{page}",
        page=page,
        text=text,
    )


def _risk(
    risk_code: str,
    evidence: list[Evidence],
    **metadata_updates,
) -> RiskItem:
    if risk_code == "redemption_rights":
        metadata = {
            "canonical_code": "LEGAL_REDEMPTION_RIGHTS",
            "holder": "Series B investors",
            "survives_listing": True,
            "restoration_clause": False,
            "builder_issues": [],
            "fact_issues": [],
        }
    else:
        metadata = {
            "canonical_code": "LEGAL_MATERIAL_LITIGATION_COMPLIANCE",
            "matter_type": "litigation",
            "management_materiality": "material",
            "potential_impact": "operational loss",
            "builder_issues": [],
            "observation_issues": [],
        }
    metadata.update(metadata_updates)
    return RiskItem(
        risk_code=risk_code,
        category=RiskCategory.LEGAL,
        risk_type="legal matter",
        level=RiskLevel.MEDIUM,
        score=50,
        conclusion="Legal effect requires verification.",
        evidence=evidence,
        calculation=None,
        agent_name="legal",
        verification_status=VerificationStatus.PENDING,
        metadata=metadata,
    )


def _available(evidence: list[Evidence]) -> dict[str, Evidence]:
    return {item.evidence_id: item for item in evidence}


def test_rights_verifier_verifies_complete_current_special_investor_clause() -> None:
    evidence = [
        _evidence(
            "Under the Pre-IPO Investment Agreement, Series B investors hold redemption "
            "rights. The rights survive the Listing and remain effective after Listing."
        )
    ]
    result = LegalRightsVerifier().verify(
        _risk("redemption_rights", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.VERIFIED
    assert result.verified_risk is not None


def test_rights_verifier_requires_complete_lifecycle_context() -> None:
    evidence = [
        _evidence(
            "Under the Pre-IPO Investment Agreement, Series B investors hold redemption "
            "rights in connection with the proposed Listing."
        )
    ]
    result = LegalRightsVerifier().verify(
        _risk("redemption_rights", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "termination_waiver_restoration_context_incomplete" in result.issues


def test_rights_verifier_detects_termination_on_later_evidence() -> None:
    evidence = [
        _evidence(
            "Series B investors hold redemption rights that remain effective for the Listing.",
            "e-right",
            20,
        ),
        _evidence(
            "Prior to Listing, those redemption rights terminate upon Listing and will not "
            "be restored.",
            "e-termination",
            21,
        ),
    ]
    result = LegalRightsVerifier().verify(
        _risk("redemption_rights", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "conflicting_rights_lifecycle_evidence" in result.issues


def test_rights_verifier_rejects_ordinary_articles_right() -> None:
    evidence = [
        _evidence(
            "Under the Articles of Association, all shareholders have a pre-emptive right "
            "that remains effective following Listing."
        )
    ]
    result = LegalRightsVerifier().verify(
        _risk("redemption_rights", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.REJECTED
    assert "ordinary_articles_right_misclassified_as_special_investor_right" in result.issues


def test_rights_verifier_rejects_historical_waived_right() -> None:
    evidence = [
        _evidence(
            "Prior to the Listing, Series B investors held redemption rights, but those "
            "rights were waived and terminated upon Listing and will not be restored."
        )
    ]
    result = LegalRightsVerifier().verify(
        _risk(
            "redemption_rights",
            evidence,
            survives_listing=True,
            restoration_clause=False,
        ),
        _available(evidence),
    )

    assert result.status == VerificationStatus.REJECTED
    assert "historical_terminated_right_presented_as_current" in result.issues


def test_rights_verifier_checks_holder_against_evidence() -> None:
    evidence = [
        _evidence(
            "Under the Pre-IPO Investment Agreement, Series A investors hold redemption "
            "rights that survive the Listing and remain effective."
        )
    ]
    result = LegalRightsVerifier().verify(
        _risk("redemption_rights", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "holder_not_supported_by_evidence" in result.issues


def test_litigation_verifier_verifies_actual_material_pending_case() -> None:
    evidence = [
        _evidence(
            "Proceedings remain pending before the High Court. Management considers the "
            "claim material and it may cause operational loss."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.VERIFIED
    assert result.verified_risk is not None


def test_litigation_verifier_rejects_future_risk_warning() -> None:
    evidence = [_evidence("We may be exposed to litigation in the future.")]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.REJECTED
    assert "general_risk_or_negative_statement_misclassified_as_actual_matter" in result.issues


def test_litigation_verifier_routes_actual_and_negative_conflict_to_review() -> None:
    evidence = [
        _evidence(
            "Proceedings remain pending and the material claim may cause operational loss.",
            "e-actual",
            30,
        ),
        _evidence(
            "The Group is not involved in any material litigation.",
            "e-negative",
            31,
        ),
    ]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "conflicting_actual_and_negative_evidence" in result.issues


def test_litigation_verifier_rejects_historical_resolved_non_material_case() -> None:
    evidence = [
        _evidence(
            "Previously, the litigation was settled and closed. Management confirmed that "
            "it was not material and had no material adverse impact."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.REJECTED
    assert "historical_resolved_matter_presented_as_current" in result.issues


def test_litigation_verifier_requires_penalty_remediation_status() -> None:
    evidence = [
        _evidence(
            "The regulator imposed a material penalty of RMB 2 million on the company."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk(
            "material_litigation_compliance",
            evidence,
            matter_type="administrative_penalty",
            potential_impact="penalty of RMB 2 million",
        ),
        _available(evidence),
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "closure_status_not_established" in result.issues
    assert "remediation_status_not_established" in result.issues


def test_litigation_verifier_rejects_completed_remediation() -> None:
    evidence = [
        _evidence(
            "The regulator imposed a material penalty, but the matter was resolved and "
            "remediation was completed."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk(
            "material_litigation_compliance",
            evidence,
            matter_type="administrative_penalty",
            potential_impact="penalty",
            is_pending=False,
            is_resolved=True,
            is_remediated=True,
        ),
        _available(evidence),
    )

    assert result.status == VerificationStatus.REJECTED
    assert "resolved_or_remediated_matter_presented_as_current" in result.issues


def test_litigation_verifier_verifies_unresolved_core_license_impact() -> None:
    evidence = [
        _evidence(
            "The company's core operating licence has not yet been renewed and operations "
            "may be suspended, causing business interruption."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk(
            "material_litigation_compliance",
            evidence,
            matter_type="license_permit",
            potential_impact="business interruption",
        ),
        _available(evidence),
    )

    assert result.status == VerificationStatus.VERIFIED


def test_litigation_verifier_rejects_cleared_license_impact() -> None:
    evidence = [
        _evidence(
            "The historical operating licence issue was resolved and the licence has been "
            "renewed with no operational impact."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk(
            "material_litigation_compliance",
            evidence,
            matter_type="license_permit",
            potential_impact="business interruption",
        ),
        _available(evidence),
    )

    assert result.status == VerificationStatus.REJECTED
    assert "resolved_license_impact_presented_as_current" in result.issues


def test_litigation_verifier_does_not_accept_unsupported_material_impact() -> None:
    evidence = [_evidence("Proceedings remain pending before the High Court.")]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), _available(evidence)
    )

    assert result.status == VerificationStatus.NEEDS_REVIEW
    assert "material_impact_not_supported_by_evidence" in result.issues


def test_legal_verifier_without_available_evidence_stays_pending() -> None:
    evidence = [
        _evidence(
            "Proceedings remain pending and the material claim may cause operational loss."
        )
    ]
    result = LitigationComplianceVerifier().verify(
        _risk("material_litigation_compliance", evidence), {}
    )

    assert result.status == VerificationStatus.PENDING
    assert result.verified_risk is None


def test_builder_and_verifier_allow_nonblocking_missing_subject_label() -> None:
    evidence = _evidence(
        "Material litigation is pending before the High Court. Management considers "
        "the claim material and it may cause operational loss."
    )
    observation = LegalMatterObservation(
        matter_type="litigation",
        subject="",
        counterparty_or_regulator="claimant",
        current_status="pending",
        is_pending=True,
        is_resolved=False,
        management_materiality="material",
        potential_impact="operational loss",
        evidence_ids=[evidence.evidence_id],
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["subject_not_identified"],
    )

    built = MaterialLitigationComplianceRiskBuilder().build(
        observation, {evidence.evidence_id: evidence}
    )

    assert built.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert built.risk_item is not None
    verified = LitigationComplianceVerifier().verify(
        built.risk_item, {evidence.evidence_id: evidence}
    )
    assert verified.status == VerificationStatus.VERIFIED


def test_unresolved_penalty_builder_candidate_is_not_rejected_for_nonmaterial_label() -> None:
    evidence = _evidence(
        "The regulator imposed a penalty that remains pending. Management considers it "
        "not material, but follow-up enforcement remains possible."
    )
    observation = LegalMatterObservation(
        matter_type="administrative_penalty",
        subject="regulatory fine",
        counterparty_or_regulator="the regulator",
        current_status="pending",
        is_pending=True,
        is_resolved=False,
        is_remediated=False,
        management_materiality="not_material",
        potential_impact="follow-up enforcement",
        evidence_ids=[evidence.evidence_id],
        status=ExtractionStatus.EXTRACTED,
    )

    built = MaterialLitigationComplianceRiskBuilder().build(
        observation, {evidence.evidence_id: evidence}
    )

    assert built.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert built.risk_item is not None
    verified = LitigationComplianceVerifier().verify(
        built.risk_item, {evidence.evidence_id: evidence}
    )
    assert verified.status == VerificationStatus.NEEDS_REVIEW
    assert verified.status != VerificationStatus.REJECTED
