from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.extraction import ExtractionStatus, LitigationComplianceExtractor
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import Evidence


def _evidence(evidence_id: str = "e-legal") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        document_id="ipo-case",
        chunk_id="ipo-case:page:20",
        page=20,
        text="legal matter clause",
    )


def _extract(payload: dict[str, object], evidence: list[Evidence] | None = None):
    provider = MockLLMProvider(
        responses={LitigationComplianceExtractor.task_name: payload}
    )
    return LitigationComplianceExtractor(provider).extract(evidence or [_evidence()])


@pytest.mark.parametrize(
    ("raw_type", "canonical_type"),
    [
        ("litigation", "litigation"),
        ("arbitration", "arbitration"),
        ("administrative penalty", "administrative_penalty"),
        ("regulatory investigation", "regulatory_investigation"),
        ("non compliance", "non_compliance"),
        ("license", "license_permit"),
        ("tax", "tax"),
        ("environmental penalty", "environmental_penalty"),
        ("data privacy", "data_privacy"),
    ],
)
def test_all_legal_matter_types_share_one_extractor(
    raw_type: str, canonical_type: str
) -> None:
    result = _extract(
        {
            "matter_type": raw_type,
            "subject": "actual disclosed matter",
            "counterparty_or_authority": "relevant counterparty or regulator",
            "event_date": "2023-01-01",
            "current_status": "pending",
            "management_materiality": "material",
            "potential_impact": "possible operational or financial impact",
            "license_impact": "no separate license impact disclosed",
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.matter_type == canonical_type
    assert result.status == ExtractionStatus.EXTRACTED


def test_pending_material_litigation_is_normalized_with_amount_and_date() -> None:
    result = _extract(
        {
            "matter_type": "重大訴訟",
            "subject": "與MBC的合同糾紛",
            "counterparty_or_authority": "MBC",
            "event_date": "2020-07-01",
            "amount": "140.9",
            "currency": "人民幣",
            "amount_unit": "百萬元",
            "current_status": "未決",
            "management_materiality": "重大",
            "potential_impact": "可能產生現金索賠及法律費用",
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.matter_type == "litigation"
    assert result.event_date == date(2020, 7, 1)
    assert result.amount == Decimal("140.9")
    assert result.currency == "CNY"
    assert result.amount_unit == "百萬元"
    assert result.current_status == "pending"
    assert result.is_pending is True
    assert result.management_materiality == "material"
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []


def test_resolved_historical_litigation_infers_closed_flags() -> None:
    result = _extract(
        {
            "matter_type": "litigation",
            "subject": "historical product claim",
            "counterparty_or_authority": "claimant",
            "event_date": "2022-12-31",
            "amount": "2.9",
            "currency": "RMB",
            "amount_unit": "million",
            "current_status": "closed",
            "management_materiality": "not material",
            "potential_impact": "judgment paid with no continuing material impact",
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.current_status == "resolved"
    assert result.is_pending is False
    assert result.is_resolved is True
    assert result.management_materiality == "not_material"
    assert result.status == ExtractionStatus.EXTRACTED


def test_remediated_environmental_penalty_uses_same_observation_model() -> None:
    result = _extract(
        {
            "matter_type": "環境處罰",
            "subject": "污水排放超標",
            "counterparty_or_authority": "晉江市環境保護局",
            "event_date": "2017-09-25",
            "amount": "33515",
            "currency": "CNY",
            "amount_unit": "yuan",
            "current_status": "已整改",
            "management_materiality": "不重大",
            "potential_impact": "罰款已支付且問題已解決",
            "is_resolved": True,
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.matter_type == "environmental_penalty"
    assert result.current_status == "remediated"
    assert result.is_remediated is True
    assert result.is_resolved is True
    assert result.status == ExtractionStatus.EXTRACTED


def test_license_matter_requires_specific_operational_impact() -> None:
    complete = _extract(
        {
            "matter_type": "license",
            "subject": "medical service permit renewal",
            "counterparty_or_authority": "local health authority",
            "event_date": "2023-06-30",
            "current_status": "ongoing",
            "management_materiality": "material",
            "potential_impact": "service interruption",
            "license_impact": "renewal failure could suspend the affected clinic",
            "evidence_ids": ["e-legal"],
        }
    )
    incomplete = _extract(
        {
            "matter_type": "license",
            "subject": "medical service permit renewal",
            "counterparty_or_authority": "local health authority",
            "event_date": "2023-06-30",
            "current_status": "ongoing",
            "management_materiality": "material",
            "potential_impact": "service interruption",
            "evidence_ids": ["e-legal"],
        }
    )

    assert complete.matter_type == "license_permit"
    assert complete.status == ExtractionStatus.EXTRACTED
    assert incomplete.status == ExtractionStatus.NEEDS_REVIEW
    assert "license_impact_not_established" in incomplete.issues


def test_explicit_no_actual_matter_is_not_confused_with_missing_evidence() -> None:
    result = _extract(
        {
            "matter_type": "no actual matter",
            "current_status": "not applicable",
            "is_pending": False,
            "is_resolved": False,
            "is_remediated": False,
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.matter_type == "none"
    assert result.current_status == "not_applicable"
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []


def test_conflicting_status_flags_require_review() -> None:
    result = _extract(
        {
            "matter_type": "regulatory investigation",
            "subject": "product inspection",
            "counterparty_or_authority": "market regulator",
            "event_date": "2022-08-01",
            "current_status": "pending",
            "is_pending": False,
            "is_resolved": True,
            "management_materiality": "not material",
            "potential_impact": "no penalty issued to date",
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "pending_status_conflict" in result.issues


def test_no_actual_matter_with_positive_event_status_requires_review() -> None:
    result = _extract(
        {
            "matter_type": "no actual matter",
            "current_status": "pending",
            "is_pending": True,
            "evidence_ids": ["e-legal"],
        }
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "no_actual_matter_conflicts_with_status" in result.issues


def test_unknown_evidence_id_cannot_support_a_formal_observation() -> None:
    result = _extract(
        {
            "matter_type": "administrative penalty",
            "subject": "filing penalty",
            "counterparty_or_authority": "market regulator",
            "event_date": "2021-01-01",
            "current_status": "resolved",
            "management_materiality": "not material",
            "potential_impact": "fine paid",
            "evidence_ids": ["invented-evidence"],
        }
    )

    assert result.evidence_ids == []
    assert result.status == ExtractionStatus.NOT_FOUND
    assert "unknown_evidence_ids" in result.issues
    assert "evidence_not_found" in result.issues
