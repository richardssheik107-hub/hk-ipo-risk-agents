"""Unit tests for the standalone v0.3 Business Verifier."""

from __future__ import annotations

from ipo_risk.agents.business_policy import RULE_VERSION, SEVERITY_POLICY
from ipo_risk.agents.business_verifier import V03BusinessVerifier
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


def evidence(evidence_id: str, page: int, text: str, *, section: str = "業務") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="doc-1",
        chunk_id=f"doc-1:page:{page}",
        page=page,
        section=section,
        text=text,
        source_type=EvidenceSourceType.PROSPECTUS,
        relevance_score=1.0,
    )


POSITIVE_EVIDENCE = (
    evidence("e1", 13, "JAB-3068（我們的核心產品）處於臨床II期。"),
    evidence("e2", 17, "目前，我們的產品尚未獲准進行商業銷售，我們尚未從產品銷售產生任何收入。"),
)


def candidate(**overrides) -> RiskItem:
    payload = {
        "risk_code": "precommercial_product",
        "category": RiskCategory.BUSINESS,
        "risk_type": "Pre-commercial core product",
        "level": RiskLevel.MEDIUM,
        "score": 60,
        "conclusion": (
            "Core product JAB-3068 is not yet commercialized and the selected "
            "prospectus evidence reports no direct product sales revenue."
        ),
        "evidence": list(POSITIVE_EVIDENCE),
        "agent_name": "business",
        "verification_status": VerificationStatus.PENDING,
        "metadata": {
            "rule_version": RULE_VERSION,
            "severity_policy": SEVERITY_POLICY,
            "score_is_rule_based": True,
            "score_is_probability": False,
            "product_name": "JAB-3068",
            "development_stage": "phase_ii",
            "has_product_revenue": False,
            "revenue_source_types": ["licensing"],
        },
    }
    payload.update(overrides)
    return RiskItem(**payload)


def test_valid_candidate_is_verified() -> None:
    result = V03BusinessVerifier().verify([candidate()])

    assert len(result.verified_risks) == 1
    verified = result.verified_risks[0]
    assert verified.verification_status == VerificationStatus.VERIFIED
    assert verified.level == RiskLevel.MEDIUM
    assert verified.score == 60
    assert "not a probability" in verified.verification_notes


def test_out_of_scope_risk_stays_pending() -> None:
    risk = candidate(risk_code="continuous_loss", agent_name="financial")

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert "outside the v0.3 Business Verifier scope" in (
        result.pending_risks[0].verification_notes
    )


def test_escalated_level_is_rejected() -> None:
    result = V03BusinessVerifier().verify([candidate(level=RiskLevel.HIGH, score=80)])

    assert len(result.rejected_risks) == 1
    assert "risk_level_outside_frozen_policy" in result.rejected_risks[0].verification_notes


def test_wrong_severity_policy_is_rejected() -> None:
    risk = candidate()
    risk.metadata["severity_policy"] = "business_candidate_high_v9"

    result = V03BusinessVerifier().verify([risk])

    assert len(result.rejected_risks) == 1
    assert "severity_policy_invalid" in result.rejected_risks[0].verification_notes


def test_commercialized_evidence_is_rejected() -> None:
    risk = candidate(
        evidence=[
            evidence(
                "e3",
                107,
                "我們生產及銷售包裝飲用水產品，產品所產生的收益佔我們總收益的57.9%。",
            )
        ]
    )

    result = V03BusinessVerifier().verify([risk])

    assert len(result.rejected_risks) == 1
    assert "evidence_shows_" in result.rejected_risks[0].verification_notes


def test_metadata_product_revenue_true_is_rejected() -> None:
    risk = candidate()
    risk.metadata["has_product_revenue"] = True

    result = V03BusinessVerifier().verify([risk])

    assert len(result.rejected_risks) == 1
    assert "metadata_product_revenue_contradicts_risk" in (
        result.rejected_risks[0].verification_notes
    )


def test_unknown_product_identity_needs_review() -> None:
    risk = candidate()
    risk.metadata["product_name"] = "unknown"

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW
    assert "Core product identity is unclear" in result.pending_risks[0].verification_notes


def test_unknown_stage_needs_review() -> None:
    risk = candidate()
    risk.metadata["development_stage"] = "unknown"

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW


def test_missing_no_revenue_sentence_needs_review() -> None:
    risk = candidate(
        evidence=[evidence("e1", 13, "JAB-3068（我們的核心產品）處於臨床II期。")]
    )

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW
    assert "both pre-commercial rule inputs" in result.pending_risks[0].verification_notes


def test_product_name_absent_from_evidence_needs_review() -> None:
    risk = candidate()
    risk.metadata["product_name"] = "XYZ-999"

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert "does not appear in the Evidence text" in (
        result.pending_risks[0].verification_notes
    )


def test_needs_review_input_is_not_auto_verified() -> None:
    risk = candidate(verification_status=VerificationStatus.NEEDS_REVIEW)

    result = V03BusinessVerifier().verify([risk])

    assert len(result.pending_risks) == 1
    assert result.pending_risks[0].verification_status == VerificationStatus.NEEDS_REVIEW


def test_certainty_claim_is_rejected() -> None:
    risk = candidate(conclusion="核心产品JAB-3068必然失败，投资者必然破产。")

    result = V03BusinessVerifier().verify([risk])

    assert len(result.rejected_risks) == 1
    assert "conclusion_contains_certainty_claim" in (
        result.rejected_risks[0].verification_notes
    )


def test_cross_document_evidence_is_rejected() -> None:
    other = evidence("e9", 5, "我們尚未商業化，尚未從產品銷售產生任何收入。")
    other = other.model_copy(update={"document_id": "doc-2"})
    risk = candidate(evidence=[POSITIVE_EVIDENCE[0], other])

    result = V03BusinessVerifier().verify([risk])

    assert len(result.rejected_risks) == 1
    assert "cross_document_evidence" in result.rejected_risks[0].verification_notes


def test_external_evidence_mismatch_is_rejected() -> None:
    risk = candidate()
    tampered = [
        item.model_copy(update={"text": item.text + "（已篡改）"})
        for item in POSITIVE_EVIDENCE
    ]

    result = V03BusinessVerifier().verify(
        [risk], {"precommercial_product": tampered}
    )

    assert len(result.rejected_risks) == 1
    assert "external_evidence_identity_or_text_mismatch" in (
        result.rejected_risks[0].verification_notes
    )


def test_matching_external_evidence_still_verifies() -> None:
    risk = candidate()

    result = V03BusinessVerifier().verify(
        [risk], {"precommercial_product": list(POSITIVE_EVIDENCE)}
    )

    assert len(result.verified_risks) == 1
