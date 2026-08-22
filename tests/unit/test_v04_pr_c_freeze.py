from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.pr_c_freeze import (
    EXPECTED_UNAVAILABLE_CASE_IDS,
    EXPECTED_UNAVAILABLE_REASON_BY_CASE,
    FORMAL_PR_C_EXPECTATIONS,
    PRCFreezeExpectations,
    audit_pr_c_freeze,
)
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketExchange,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityEligibilityReason,
)
from scripts import run_v04_pr_c as pr_c


def _label(case_id: str, year: int, value: str | None) -> MarketOutcomeLabel:
    listing = date(year, 1, 2)
    available = value is not None
    return MarketOutcomeLabel(
        case_id=case_id,
        stock_code=f"{case_id[-4:]}.HK",
        cohort_year=year,
        dataset_split=(
            MarketDatasetSplit.DEVELOPMENT
            if year <= 2023
            else MarketDatasetSplit.VALIDATION
        ),
        listing_date=listing,
        horizon=MarketLabelHorizon.FIVE_DAYS,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=listing + timedelta(days=7) if available else None,
        target_close=(
            Decimal("10") * (Decimal("1") + Decimal(value))
            if available
            else None
        ),
        raw_return=Decimal(value) if available else None,
        availability=(
            MarketLabelAvailability.AVAILABLE
            if available
            else MarketLabelAvailability.UNAVAILABLE
        ),
        missing_reason=(
            None if available else MarketLabelMissingReason.NO_ELIGIBLE_SESSION
        ),
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture",
            dataset_version="fixture-v1",
            source_record_id=case_id,
        ),
    )


def _materialize_fixture(tmp_path: Path):
    def metadata(case_id: str, stock_code: str, year: int, record_id: str):
        return pr_c.IPOMarketMetadata(
            case_id=case_id,
            stock_code=stock_code,
            cohort_year=year,
            listing_date=date(year, 1, 2),
            listing_price=Decimal("10"),
            exchange=MarketExchange.HKEX,
            official_ipo_universe_member=True,
            modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
            eligibility_reason=(
                MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER
            ),
            source="fixture",
            provenance=MarketDataProvenance(
                source="fixture", dataset_version="v1", source_record_id=record_id
            ),
        )

    metadata = (
        metadata("ipo_2023_0001", "0001.HK", 2023, "m1"),
        metadata("ipo_2023_0002", "0002.HK", 2023, "m2"),
        metadata("ipo_2024_0003", "0003.HK", 2024, "m3"),
    )
    labels = {
        metadata[0].case_id: _label(metadata[0].case_id, 2023, "-0.2"),
        metadata[1].case_id: _label(metadata[1].case_id, 2023, None),
        metadata[2].case_id: _label(metadata[2].case_id, 2024, "0.1"),
    }
    output = tmp_path / "run"
    pr_c.materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels,
        generation_failures=[],
        output_dir=output,
        source_context={
            "git_revision": "a" * 40,
            "raw_eod_sha256": "b" * 64,
            "official_bridge_sha256": "c" * 64,
            "blind_outcomes_included": False,
        },
        verify_determinism=True,
        expected_case_count=None,
    )
    expectations = PRCFreezeExpectations(
        official_case_count=3,
        development_case_count=2,
        validation_case_count=1,
        available_count=2,
        development_available_count=1,
        validation_available_count=1,
        unavailable_case_ids=(metadata[1].case_id,),
        raw_eod_sha256="b" * 64,
        official_bridge_sha256="c" * 64,
        unavailable_reason_by_case=(
            (metadata[1].case_id, MarketLabelMissingReason.NO_ELIGIBLE_SESSION.value),
        ),
    )
    return output, expectations


def test_formal_expectations_match_governed_label_readiness() -> None:
    assert FORMAL_PR_C_EXPECTATIONS.official_case_count == 438
    assert FORMAL_PR_C_EXPECTATIONS.development_case_count == 368
    assert FORMAL_PR_C_EXPECTATIONS.validation_case_count == 70
    assert FORMAL_PR_C_EXPECTATIONS.available_count == 424
    assert FORMAL_PR_C_EXPECTATIONS.development_available_count == 354
    assert FORMAL_PR_C_EXPECTATIONS.validation_available_count == 70
    assert len(EXPECTED_UNAVAILABLE_CASE_IDS) == 14
    assert tuple(sorted(EXPECTED_UNAVAILABLE_CASE_IDS)) == tuple(
        sorted(FORMAL_PR_C_EXPECTATIONS.unavailable_case_ids)
    )

    reasons = dict(EXPECTED_UNAVAILABLE_REASON_BY_CASE)
    assert set(reasons) == set(EXPECTED_UNAVAILABLE_CASE_IDS)
    assert sum(value == "missing_base_price" for value in reasons.values()) == 12
    assert sum(value == "no_eligible_session" for value in reasons.values()) == 2
    assert reasons["ipo_2020_06688"] == "no_eligible_session"
    assert reasons["ipo_2022_07841"] == "no_eligible_session"


def test_freeze_gate_accepts_complete_deterministic_materialization(
    tmp_path: Path,
) -> None:
    output, expectations = _materialize_fixture(tmp_path)
    manifest = audit_pr_c_freeze(output, expectations=expectations)
    assert manifest["gate_passed"] is True
    assert manifest["official_case_count"] == 3
    assert manifest["available_count"] == 2
    assert manifest["threshold_fit_split"] == "development"
    assert manifest["validation_used_for_threshold"] is False
    assert manifest["blind_2025_y_accessed"] is False
    assert manifest["unavailable_reason_counts"] == {"no_eligible_session": 1}
    assert len(manifest["freeze_manifest_hash"]) == 64


def test_freeze_gate_rejects_coverage_or_determinism_drift(tmp_path: Path) -> None:
    output, expectations = _materialize_fixture(tmp_path)
    reproducibility_path = output / "reproducibility_report.json"
    reproducibility = json.loads(reproducibility_path.read_text(encoding="utf-8"))
    reproducibility["mismatch_count"] = 1
    reproducibility["passed"] = False
    reproducibility_path.write_text(json.dumps(reproducibility), encoding="utf-8")
    with pytest.raises(ValueError, match="did not pass"):
        audit_pr_c_freeze(output, expectations=expectations)


def test_freeze_gate_rejects_target_tampering(tmp_path: Path) -> None:
    output, expectations = _materialize_fixture(tmp_path)
    target_path = output / "targets" / "ipo_2024_0003.json"
    payload = json.loads(target_path.read_text(encoding="utf-8"))
    payload["poor_performer_5d"] = not payload["poor_performer_5d"]
    target_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="target hash mismatch"):
        audit_pr_c_freeze(output, expectations=expectations)
