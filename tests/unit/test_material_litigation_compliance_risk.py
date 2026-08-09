from __future__ import annotations

from datetime import date
from decimal import Decimal

from ipo_risk.domain.material_litigation_compliance import (
    MaterialLitigationComplianceBuildStatus,
    MaterialLitigationComplianceRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, LegalMatterObservation
from ipo_risk.schemas import Evidence, VerificationStatus


def _evidence() -> Evidence:
    return Evidence(
        evidence_id="e-legal",
        document_id="ipo-case",
        chunk_id="ipo-case:page:20",
        page=20,
        text="actual legal matter",
    )


def _observation(**updates) -> LegalMatterObservation:
    values = {
        "matter_type": "litigation",
        "subject": "supplier claim",
        "counterparty_or_regulator": "supplier",
        "event_date": date(2023, 1, 1),
        "amount": Decimal("2"),
        "currency": "CNY",
        "amount_unit": "million",
        "current_status": "pending",
        "is_pending": True,
        "is_resolved": False,
        "is_remediated": None,
        "management_materiality": "material",
        "potential_impact": "cash claim and legal costs",
        "license_impact": "",
        "evidence_ids": ["e-legal"],
        "status": ExtractionStatus.EXTRACTED,
    }
    values.update(updates)
    return LegalMatterObservation(**values)


def _build(observation: LegalMatterObservation):
    evidence = _evidence()
    return MaterialLitigationComplianceRiskBuilder().build(
        observation, {evidence.evidence_id: evidence}
    )


def test_current_pending_material_litigation_generates_candidate() -> None:
    result = _build(_observation())

    assert result.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.metadata["decision_reason"] == "material_pending_matter"


def test_imposed_penalty_without_remediation_generates_candidate() -> None:
    result = _build(
        _observation(
            matter_type="administrative_penalty",
            subject="regulatory fine",
            counterparty_or_regulator="market regulator",
            current_status="pending",
            is_pending=True,
            is_resolved=False,
            is_remediated=False,
            management_materiality="not_material",
            potential_impact="fine and possible follow-up enforcement",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.metadata["decision_reason"] == (
        "unresolved_compliance_or_penalty_matter"
    )


def test_unrenewed_license_with_operational_impact_generates_candidate() -> None:
    result = _build(
        _observation(
            matter_type="license_permit",
            subject="core operating licence",
            counterparty_or_regulator="licensing authority",
            amount=None,
            currency="",
            amount_unit="",
            current_status="pending",
            is_pending=True,
            management_materiality="material",
            potential_impact="business interruption",
            license_impact="licence has not been renewed and operations may be suspended",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.metadata["decision_reason"] == "unresolved_core_license_impact"


def test_actual_matter_with_unclear_closure_amount_or_materiality_needs_review() -> None:
    result = _build(
        _observation(
            current_status="unknown",
            is_pending=None,
            is_resolved=None,
            amount=None,
            management_materiality="",
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=["current_status_not_established"],
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.NEEDS_REVIEW
    assert "amount_not_established" in result.issues
    assert "management_materiality_not_established" in result.issues


def test_resolved_penalty_with_unclear_remediation_needs_review() -> None:
    result = _build(
        _observation(
            matter_type="administrative_penalty",
            subject="historical regulatory fine",
            counterparty_or_regulator="market regulator",
            current_status="resolved",
            is_pending=False,
            is_resolved=True,
            is_remediated=None,
            management_materiality="not_material",
            potential_impact="fine paid",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert "remediation_status_not_established" in result.issues


def test_actual_license_matter_with_unclear_core_impact_needs_review() -> None:
    result = _build(
        _observation(
            matter_type="license_permit",
            subject="operating permit",
            counterparty_or_regulator="licensing authority",
            amount=None,
            current_status="pending",
            is_pending=True,
            management_materiality="material",
            potential_impact="possible operational interruption",
            license_impact="",
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=["license_impact_not_established"],
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert "license_impact_not_established" in result.issues


def test_resolved_non_material_litigation_does_not_generate_current_risk() -> None:
    result = _build(
        _observation(
            current_status="resolved",
            is_pending=False,
            is_resolved=True,
            management_materiality="not_material",
            potential_impact="judgment paid with no continuing impact",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None


def test_pending_but_expressly_non_material_without_continuing_impact_is_not_applicable() -> None:
    result = _build(
        _observation(
            amount=None,
            currency="",
            amount_unit="",
            management_materiality="not_material",
            potential_impact="No continuing impact on the Group's operations.",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert result.metadata["decision_reason"] == (
        "matter_expressly_not_material_without_continuing_impact"
    )
    assert "amount_not_established" not in result.issues


def test_resolved_material_litigation_is_not_reopened_by_missing_amount() -> None:
    result = _build(
        _observation(
            amount=None,
            currency="",
            amount_unit="",
            current_status="resolved",
            is_pending=False,
            is_resolved=True,
            management_materiality="material",
            potential_impact="historical judgment with no continuing impact",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert "amount_not_established" not in result.issues


def test_material_matter_with_unknown_closure_status_needs_review() -> None:
    result = _build(
        _observation(
            current_status="unknown",
            is_pending=None,
            is_resolved=None,
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=["current_status_not_established"],
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.NEEDS_REVIEW
    assert "current_status_not_established" in result.issues


def test_resolved_and_remediated_penalty_is_not_a_current_risk() -> None:
    result = _build(
        _observation(
            matter_type="administrative_penalty",
            current_status="remediated",
            is_pending=False,
            is_resolved=True,
            is_remediated=True,
            management_materiality="material",
            potential_impact="fine paid and remediation completed",
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None


def test_non_standard_materiality_value_needs_review() -> None:
    result = _build(_observation(management_materiality="unclear"))

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert "management_materiality_not_established" in result.issues


def test_pending_and_resolved_status_conflict_needs_review() -> None:
    result = _build(
        _observation(
            current_status="pending",
            is_pending=True,
            is_resolved=True,
        )
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert "pending_and_resolved_conflict" in result.issues
