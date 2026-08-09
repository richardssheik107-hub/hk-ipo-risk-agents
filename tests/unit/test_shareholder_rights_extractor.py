from __future__ import annotations

from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.extraction import ExtractionStatus, ShareholderRightsExtractor
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import Evidence


def _evidence(evidence_id: str = "e-rights") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id="ipo-case:page:1",
        page=1,
        text="shareholder rights clause",
    )


def _extract(payload: dict[str, object], evidence: list[Evidence] | None = None):
    provider = MockLLMProvider(
        responses={ShareholderRightsExtractor.task_name: payload}
    )
    return ShareholderRightsExtractor(provider).extract(evidence or [_evidence()])


def test_normalization_maps_multilingual_right_type_and_conditional_restoration() -> None:
    result = _extract(
        {
            "right_type": "贖回權",
            "holder": "  B輪投資者  ",
            "is_effective": False,
            "termination_event": "上市",
            "termination_timing": "上市時",
            "restoration_clause": True,
            "restoration_condition": "上市申請遭拒後自動恢復",
            "impact_on_public_shareholders": "  可能產生現金清償義務  ",
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.right_type == "redemption_right"
    assert result.holder == "B輪投資者"
    assert result.is_effective is False
    assert result.survives_listing is None
    assert result.termination_event == "listing"
    assert result.termination_timing == "on_listing"
    assert result.restoration_clause is True
    assert result.restoration_condition == "上市申請遭拒後自動恢復"
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []


def test_currently_effective_right_that_ends_at_listing_is_not_a_status_conflict() -> None:
    result = _extract(
        {
            "right_type": "redemption_right",
            "holder": "Pre-IPO investors",
            "is_effective": True,
            "survives_listing": False,
            "termination_event": "listing",
            "termination_timing": "upon listing",
            "restoration_clause": False,
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.is_effective is True
    assert result.survives_listing is False
    assert result.status == ExtractionStatus.EXTRACTED
    assert "conflicting_effectiveness_status" not in result.issues


def test_explicitly_terminated_right_without_restoration_is_a_complete_fact() -> None:
    result = _extract(
        {
            "right_type": "liquidation preference",
            "holder": "Pre-IPO investors",
            "is_effective": False,
            "survives_listing": False,
            "termination_event": "listing",
            "termination_timing": "upon listing",
            "restoration_clause": False,
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.right_type == "liquidation_preference"
    assert result.is_effective is False
    assert result.restoration_clause is False
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []


def test_legacy_survives_listing_field_can_establish_effectiveness() -> None:
    candidate = ShareholderRightCandidate(
        right_type="director nomination right",
        holder="Ali WB",
        survives_listing=True,
        evidence_ids=["e-rights"],
    )
    provider = MockLLMProvider()

    result = ShareholderRightsExtractor(provider).normalize(candidate, [_evidence()])

    assert result.right_type == "director_nomination_right"
    assert result.is_effective is True
    assert result.survives_listing is True
    assert result.status == ExtractionStatus.EXTRACTED


def test_explicit_no_special_rights_is_distinct_from_missing_evidence() -> None:
    result = _extract(
        {
            "right_type": "無特殊權利",
            "is_effective": False,
            "survives_listing": False,
            "restoration_clause": False,
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.right_type == "none"
    assert result.holder == ""
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []


def test_incomplete_clause_is_preserved_as_needs_review_not_promoted_to_risk() -> None:
    result = _extract(
        {
            "right_type": "repurchase right",
            "holder": "Pre-IPO investor",
            "trigger_or_termination": "exercisable as set out in the convertible bond instrument",
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.right_type == "repurchase_right"
    assert result.is_effective is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.issues == ["effectiveness_not_established"]


def test_terminated_right_without_restoration_finding_stays_uncertain() -> None:
    result = _extract(
        {
            "right_type": "redemption_right",
            "holder": "Pre-IPO investor",
            "is_effective": False,
            "termination_event": "listing application",
            "termination_timing": "upon submission of listing application",
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.restoration_clause is None
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "restoration_status_not_established" in result.issues


def test_unknown_evidence_id_is_not_accepted_as_source_support() -> None:
    result = _extract(
        {
            "right_type": "redemption_right",
            "holder": "Series B investors",
            "is_effective": True,
            "evidence_ids": ["hallucinated-evidence"],
        }
    )

    assert result.evidence_ids == []
    assert result.status == ExtractionStatus.NOT_FOUND
    assert "unknown_evidence_ids" in result.issues
    assert "evidence_not_found" in result.issues


def test_llm_uncertainty_and_contradictory_status_are_deterministically_flagged() -> None:
    result = _extract(
        {
            "right_type": "special rights",
            "holder": "Investor A",
            "is_effective": False,
            "survives_listing": True,
            "uncertainty_reason": "termination date is ambiguous",
            "evidence_ids": ["e-rights"],
        }
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_effectiveness_status" in result.issues
    assert "llm_reported_uncertainty" in result.issues
    assert "termination date is ambiguous" in result.uncertainty_reason
