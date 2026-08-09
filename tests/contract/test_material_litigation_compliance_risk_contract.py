from __future__ import annotations

from datetime import date
from decimal import Decimal

from ipo_risk.domain.material_litigation_compliance import (
    MaterialLitigationComplianceBuildStatus,
    MaterialLitigationComplianceRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, LegalMatterObservation
from ipo_risk.schemas import (
    DiagnosticCode,
    Evidence,
    RiskCategory,
    RiskLevel,
    VerificationStatus,
)


def _evidence() -> Evidence:
    return Evidence(
        evidence_id="e-legal",
        document_id="ipo-case",
        chunk_id="ipo-case:page:20",
        page=20,
        text="actual pending legal matter",
    )


def _observation(**updates) -> LegalMatterObservation:
    values = {
        "matter_type": "litigation",
        "subject": "MBC contract claim",
        "counterparty_or_regulator": "MBC",
        "event_date": date(2020, 7, 1),
        "amount": Decimal("140.9"),
        "currency": "CNY",
        "amount_unit": "million",
        "current_status": "pending",
        "is_pending": True,
        "is_resolved": False,
        "management_materiality": "material",
        "potential_impact": "cash claim and legal costs",
        "evidence_ids": ["e-legal"],
        "status": ExtractionStatus.EXTRACTED,
    }
    values.update(updates)
    return LegalMatterObservation(**values)


def test_builder_keeps_public_contract_without_auto_verified_or_auto_high() -> None:
    evidence = _evidence()

    result = MaterialLitigationComplianceRiskBuilder().build(
        _observation(), {evidence.evidence_id: evidence}
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.risk_code == "material_litigation_compliance"
    assert result.risk_item.category == RiskCategory.LEGAL
    assert result.risk_item.agent_name == "legal"
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.level == RiskLevel.MEDIUM
    assert result.risk_item.level != RiskLevel.HIGH
    assert result.risk_item.metadata["level_is_provisional"] is True
    assert result.risk_item.evidence == [evidence]


def test_clear_negative_is_not_applicable_but_missing_evidence_is_not() -> None:
    evidence = _evidence()
    negative = _observation(
        matter_type="none",
        subject="",
        counterparty_or_regulator="",
        event_date=None,
        amount=None,
        currency="",
        amount_unit="",
        current_status="not_applicable",
        is_pending=False,
        is_resolved=False,
        is_remediated=False,
        management_materiality="",
        potential_impact="",
    )

    result = MaterialLitigationComplianceRiskBuilder().build(
        negative, {evidence.evidence_id: evidence}
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert result.diagnostic is not None
    assert result.diagnostic.code == DiagnosticCode.NOT_APPLICABLE

    missing = MaterialLitigationComplianceRiskBuilder().build(
        _observation(
            status=ExtractionStatus.NOT_FOUND,
            evidence_ids=[],
            issues=["evidence_not_found"],
        ),
        {},
    )
    assert missing.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert missing.risk_item is None
    assert missing.diagnostic is not None
    assert missing.diagnostic.code == DiagnosticCode.EVIDENCE_NOT_FOUND


def test_frozen_rule_routes_unclear_materiality_to_needs_review() -> None:
    evidence = _evidence()
    result = MaterialLitigationComplianceRiskBuilder().build(
        _observation(
            management_materiality="",
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=["management_materiality_not_established"],
        ),
        {evidence.evidence_id: evidence},
    )

    assert result.status == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.NEEDS_REVIEW
    assert result.risk_item.verification_status != VerificationStatus.VERIFIED
