from __future__ import annotations

from ipo_risk.domain.redemption_rights import (
    RedemptionRightsBuildStatus,
    RedemptionRightsRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, ShareholderRightsFact
from ipo_risk.schemas import Evidence, EvidenceSourceType, VerificationStatus


def _evidence(
    evidence_id: str = "e-rights",
    source_type: EvidenceSourceType = EvidenceSourceType.PROSPECTUS,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id="ipo-case:page:10",
        page=10,
        text="auditable shareholder-rights clause",
        source_type=source_type,
    )


def _fact(**updates) -> ShareholderRightsFact:
    values = {
        "right_type": "redemption_right",
        "holder": "Pre-IPO investors",
        "is_effective": True,
        "survives_listing": True,
        "termination_event": "",
        "termination_timing": "",
        "restoration_clause": False,
        "restoration_condition": "",
        "evidence_ids": ["e-rights"],
        "status": ExtractionStatus.EXTRACTED,
    }
    values.update(updates)
    return ShareholderRightsFact(**values)


def _build(fact: ShareholderRightsFact, evidence: Evidence | None = None):
    selected = evidence or _evidence()
    return RedemptionRightsRiskBuilder().build(fact, {selected.evidence_id: selected})


def test_case_a_right_survives_listing_and_enters_verification() -> None:
    result = _build(_fact(right_type="director_nomination_right", holder="Ali WB"))

    assert result.status == RedemptionRightsBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.metadata["decision_reason"] == "right_survives_listing"


def test_case_b_clear_listing_termination_without_restoration_is_not_current_risk() -> None:
    result = _build(
        _fact(
            is_effective=False,
            survives_listing=False,
            termination_event="listing",
            termination_timing="on_listing",
            restoration_clause=False,
        )
    )

    assert result.status == RedemptionRightsBuildStatus.NOT_APPLICABLE
    assert result.risk_item is None
    assert result.diagnostic is not None


def test_case_c_conditional_restoration_enters_verification_without_becoming_high() -> None:
    result = _build(
        _fact(
            is_effective=False,
            survives_listing=False,
            termination_event="listing_application",
            termination_timing="on_listing_application",
            restoration_clause=True,
            restoration_condition="listing application is withdrawn or rejected",
        )
    )

    assert result.status == RedemptionRightsBuildStatus.BUILT
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.PENDING
    assert result.risk_item.level.value == "medium"
    assert result.risk_item.metadata["decision_reason"] == (
        "restoration_condition_requires_verification"
    )
    assert "may be restored" in result.risk_item.conclusion


def test_case_d_incomplete_terms_produce_needs_review_candidate() -> None:
    result = _build(
        _fact(
            is_effective=None,
            survives_listing=None,
            restoration_clause=None,
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=["effectiveness_not_established"],
        )
    )

    assert result.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.NEEDS_REVIEW
    assert result.diagnostic is not None
    assert "effectiveness_not_established" in result.issues


def test_restoration_without_trigger_condition_requires_review() -> None:
    result = _build(
        _fact(
            is_effective=False,
            survives_listing=False,
            restoration_clause=True,
            restoration_condition="",
        )
    )

    assert result.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert "restoration_condition_missing" in result.issues


def test_builder_rejects_missing_or_non_prospectus_evidence_as_formal_support() -> None:
    missing = RedemptionRightsRiskBuilder().build(_fact(), {})
    assert missing.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert missing.risk_item is None

    market_evidence = _evidence(source_type=EvidenceSourceType.MARKET_DATA)
    invalid_source = _build(_fact(), market_evidence)
    assert invalid_source.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert invalid_source.risk_item is None
    assert "evidence_source_type_invalid" in invalid_source.issues


def test_unknown_right_type_is_reviewed_instead_of_treated_as_absent() -> None:
    result = _build(_fact(right_type="unknown"))

    assert result.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert result.risk_item is not None
    assert result.risk_item.verification_status == VerificationStatus.NEEDS_REVIEW
    assert "right_type_unknown" in result.issues


def test_no_special_rights_with_positive_status_is_not_accepted_as_not_applicable() -> None:
    result = _build(
        _fact(
            right_type="none",
            holder="",
            is_effective=True,
            survives_listing=True,
            restoration_clause=False,
        )
    )

    assert result.status == RedemptionRightsBuildStatus.NEEDS_REVIEW
    assert result.risk_item is None
    assert "no_special_rights_conflicts_with_status" in result.issues
