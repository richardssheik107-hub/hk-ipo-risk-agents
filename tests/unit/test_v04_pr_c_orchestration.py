from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.schemas.market import (
    IPOMarketMetadata,
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


def _metadata(case_id: str, year: int) -> IPOMarketMetadata:
    return IPOMarketMetadata(
        case_id=case_id,
        stock_code=f"{case_id[-4:]}.HK",
        cohort_year=year,
        listing_date=date(year, 1, 2),
        listing_price=Decimal("10"),
        currency="HKD",
        exchange=MarketExchange.HKEX,
        official_ipo_universe_member=True,
        modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
        eligibility_reason=(
            MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER
        ),
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture",
            dataset_version="fixture-v1",
            source_record_id=case_id,
        ),
    )


def _label(item: IPOMarketMetadata, value: str | None) -> MarketOutcomeLabel:
    available = value is not None
    assert item.listing_date is not None
    return MarketOutcomeLabel(
        case_id=item.case_id,
        stock_code=item.stock_code,
        cohort_year=item.cohort_year,
        dataset_split=(
            MarketDatasetSplit.DEVELOPMENT
            if item.cohort_year <= 2023
            else MarketDatasetSplit.VALIDATION
            if item.cohort_year == 2024
            else MarketDatasetSplit.BLIND
        ),
        listing_date=item.listing_date,
        horizon=MarketLabelHorizon.FIVE_DAYS,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=(
            item.listing_date + timedelta(days=7) if available else None
        ),
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
            None
            if available
            else MarketLabelMissingReason.NO_ELIGIBLE_SESSION
        ),
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture",
            dataset_version="fixture-v1",
            source_record_id=f"label-{item.case_id}",
        ),
    )


def _fixture_rows():
    metadata = (
        _metadata("ipo_2020_0001", 2020),
        _metadata("ipo_2021_0002", 2021),
        _metadata("ipo_2022_0003", 2022),
        _metadata("ipo_2023_0004", 2023),
        _metadata("ipo_2024_0005", 2024),
        _metadata("ipo_2024_0006", 2024),
    )
    returns = ("-0.30", "-0.10", "0.10", "0.20", "-0.20", None)
    labels = {
        item.case_id: _label(item, value)
        for item, value in zip(metadata, returns, strict=True)
    }
    return metadata, labels


def test_materialization_freezes_development_threshold_and_keeps_unavailable(
    tmp_path: Path,
) -> None:
    metadata, labels = _fixture_rows()
    result = pr_c.materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels,
        generation_failures=[],
        output_dir=tmp_path / "out",
        source_context={"fixture": True},
        verify_determinism=True,
        expected_case_count=None,
    )

    summary = result["summary"]
    assert summary["poor_performer_threshold"] == "-0.30"
    assert summary["development_threshold_sample_count"] == 4
    assert summary["available_by_split"] == {"development": 4, "validation": 1}
    assert summary["unavailable_by_split"] == {"validation": 1}
    assert summary["failure_count"] == 0
    assert summary["blind_2025_y_accessed"] is False
    assert result["reproducibility"]["passed"] is True
    unavailable = next(
        row for row in result["coverage"] if row["case_id"] == "ipo_2024_0006"
    )
    assert unavailable["target_status"] == "unavailable"
    assert unavailable["missing_reason"] == "no_eligible_session"
    assert (tmp_path / "out" / "frozen_threshold_policy.json").is_file()
    assert len(list((tmp_path / "out" / "targets").glob("*.json"))) == 6


def test_resume_is_conflict_safe_and_semantically_stable(tmp_path: Path) -> None:
    metadata, labels = _fixture_rows()
    output = tmp_path / "out"
    first = pr_c.materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels,
        generation_failures=[],
        output_dir=output,
        source_context={"fixture": True},
        expected_case_count=None,
    )
    second = pr_c.materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels,
        generation_failures=[],
        output_dir=output,
        source_context={"fixture": True},
        resume=True,
        expected_case_count=None,
    )
    assert first["summary"] == second["summary"]

    changed = dict(labels)
    changed["ipo_2024_0005"] = _label(metadata[4], "-0.90")
    with pytest.raises(ValueError, match="provenance/content conflict"):
        pr_c.materialize_from_labels(
            metadata=metadata,
            labels_by_case=changed,
            generation_failures=[],
            output_dir=output,
            source_context={"fixture": True},
            resume=True,
            expected_case_count=None,
        )


def test_generation_failure_stays_visible_in_coverage(tmp_path: Path) -> None:
    metadata, labels = _fixture_rows()
    failed_case = metadata[-1].case_id
    labels.pop(failed_case)
    result = pr_c.materialize_from_labels(
        metadata=metadata,
        labels_by_case=labels,
        generation_failures=[
            {
                "case_id": failed_case,
                "stage": "five_day_label_generation",
                "reason": "FixtureError: broken source row",
            }
        ],
        output_dir=tmp_path / "out",
        source_context={"fixture": True},
        expected_case_count=None,
    )
    failed = next(row for row in result["coverage"] if row["case_id"] == failed_case)
    assert len(result["coverage"]) == len(metadata)
    assert result["summary"]["failure_count"] == 1
    assert failed["target_status"] == "failed"
    assert failed["failure_stage"] == "five_day_label_generation"


def test_blind_metadata_and_unknown_labels_fail_closed(tmp_path: Path) -> None:
    metadata, labels = _fixture_rows()
    blind = _metadata("ipo_2025_0007", 2025)
    with pytest.raises(ValueError, match="Blind"):
        pr_c.materialize_from_labels(
            metadata=metadata + (blind,),
            labels_by_case=labels,
            generation_failures=[],
            output_dir=tmp_path / "blind",
            source_context={},
            expected_case_count=None,
        )

    labels["outside"] = _label(metadata[0], "0.01").model_copy(
        update={"case_id": "outside"}
    )
    with pytest.raises(ValueError, match="outside official cohort"):
        pr_c.materialize_from_labels(
            metadata=metadata,
            labels_by_case=labels,
            generation_failures=[],
            output_dir=tmp_path / "outside",
            source_context={},
            expected_case_count=None,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "wrong-case"),
        ("stock_code", "9999.HK"),
        ("cohort_year", 2022),
        ("listing_date", date(2023, 2, 1)),
        ("dataset_split", MarketDatasetSplit.VALIDATION),
        ("horizon", MarketLabelHorizon.ONE_DAY),
    ],
)
def test_metadata_label_identity_mismatch_fails_closed(
    tmp_path: Path, field: str, value
) -> None:
    metadata, labels = _fixture_rows()
    case_id = metadata[0].case_id
    labels[case_id] = labels[case_id].model_copy(update={field: value})
    if field == "case_id":
        with pytest.raises(ValueError, match="key/case_id"):
            pr_c.materialize_from_labels(
                metadata=metadata,
                labels_by_case=labels,
                generation_failures=[],
                output_dir=tmp_path / field,
                source_context={},
                expected_case_count=None,
            )
    else:
        with pytest.raises(ValueError, match="identity mismatch"):
            pr_c.materialize_from_labels(
                metadata=metadata,
                labels_by_case=labels,
                generation_failures=[],
                output_dir=tmp_path / field,
                source_context={},
                expected_case_count=None,
            )
