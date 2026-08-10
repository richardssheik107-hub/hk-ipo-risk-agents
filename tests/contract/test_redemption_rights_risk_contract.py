from __future__ import annotations

from ipo_risk.domain.redemption_rights import (
    RedemptionRightsBuildStatus,
    RedemptionRightsRiskBuilder,
)
from ipo_risk.domain.legal_verifiers import LegalRightsVerifier
from ipo_risk.extraction import ExtractionStatus, ShareholderRightsFact
from ipo_risk.schemas import (
    DiagnosticCode,
    Evidence,
    RiskCategory,
    RiskLevel,
    VerificationStatus,
)


def _evidence() -> Evidence:
    return Evidence(
        evidence_id="e-rights",
        document_id="ipo-case",
        chunk_id="ipo-case:page:10",
        page=10,
        text="auditable shareholder-rights clause",
    )


def _fact(**updates) -> ShareholderRightsFact:
    values = {
        "right_type": "redemption_right",
        "holder": "Pre-IPO investors",
        "is_effective": True,
        "survives_listing": True,
        "restoration_clause": False,
        "evidence_ids": ["e-rights"],
        "status": ExtractionStatus.EXTRACTED,
    }
    values.update(updates)
    return ShareholderRightsFact(**values)


def test_builder_keeps_public_risk_contract_and_never_auto_verifies_or_auto_highs() -> None:
    evidence = _evidence()

    result = RedemptionRightsRiskBuilder().build(_fact(), {evidence.evidence_id: evidence})

    assert result.status == RedemptionRightsBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.risk_code == "redemption_rights"
    assert result.risk_item.category == RiskCategory.LEGAL
    assert result.risk_item.agent_name == "legal"
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.level == RiskLevel.MEDIUM
    assert result.risk_item.score == 50
    assert result.risk_item.level != RiskLevel.HIGH
    assert result.risk_item.level != RiskLevel.CRITICAL
    assert result.risk_item.calculation is None
    assert result.risk_item.metadata["level_is_provisional"] is True
    assert result.risk_item.metadata["score_is_rule_based"] is True
    assert result.risk_item.metadata["score_is_probability"] is False
    assert result.risk_item.evidence == [evidence]

    verified = LegalRightsVerifier().verify(
        result.risk_item, {evidence.evidence_id: evidence}
    )
    assert verified.reviewed_risk.level == RiskLevel.MEDIUM
    assert verified.reviewed_risk.score == 50


def test_explicit_absence_is_not_applicable_but_missing_evidence_is_not() -> None:
    evidence = _evidence()
    absent = _fact(
        right_type="none",
        holder="",
        is_effective=False,
        survives_listing=False,
    )

    result = RedemptionRightsRiskBuilder().build(absent, {evidence.evidence_id: evidence})

    assert result.status == RedemptionRightsBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert result.diagnostic is not None
    assert result.diagnostic.code == DiagnosticCode.NOT_APPLICABLE

    missing = RedemptionRightsRiskBuilder().build(
        _fact(status=ExtractionStatus.NOT_FOUND, evidence_ids=[], issues=["evidence_not_found"]),
        {},
    )
    assert missing.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert missing.risk_item is None
    assert missing.diagnostic is not None
    assert missing.diagnostic.code == DiagnosticCode.EVIDENCE_NOT_FOUND
