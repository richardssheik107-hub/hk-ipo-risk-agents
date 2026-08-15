from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.exceptions import BlindDataLeakageError
from ipo_risk.market.features import MARKET_FEATURE_MANIFEST_V1, PreListingMarketFeatureEngine
from ipo_risk.modeling.dataset import V04BlindFeatureExporter, V04ModelingDatasetBuilder
from ipo_risk.modeling.exceptions import ModelingDatasetJoinError
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.modeling.market_dataset import (
    V04MarketAugmentedBlindFeatureExporter,
    V04MarketAugmentedDatasetBuilder,
)
from ipo_risk.modeling.snapshot import DocumentRiskSnapshotBuilder
from ipo_risk.schemas import IPOAnalysisResult, TaskStatus
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityEligibilityReason,
    MarketSecurityType,
    expected_market_split,
)
from ipo_risk.schemas.market_features import (
    MarketReferenceBar,
    PreListingMarketFeatureContext,
)
from ipo_risk.schemas.modeling import DocumentRiskSnapshotBuildContext


def provenance(record_id: str) -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture", dataset_version="fixture-v1", source_record_id=record_id
    )


def document_snapshot(year: int, code: str = "0001.HK"):
    listing = date(year, 3, 1)
    split = expected_market_split(year)
    case_id = f"ipo_{year}_{code[:4]}"
    result = IPOAnalysisResult(
        analysis_id=f"analysis-{year}-{code}",
        request_id=f"request-{year}-{code}",
        company_name="Fixture IPO",
        stock_code=code,
        workflow_version="enhanced_v2",
        schema_version="1.0",
        status=TaskStatus.COMPLETED,
        metadata={
            "case_id": case_id,
            "dataset_split": split.value,
            "ipo_profile": {"stock_code": code, "listing_date": listing.isoformat()},
            "document": {"document_id": f"document-{year}-{code}"},
            "supervision": {"conflicts": []},
        },
    )
    return DocumentRiskSnapshotBuilder().build(
        result,
        DocumentRiskSnapshotBuildContext(
            case_id=case_id,
            document_id=f"document-{year}-{code}",
            stock_code=code,
            cohort_year=year,
            listing_date=listing,
            dataset_split=split,
            official_ipo_universe_member=True,
            security_type=MarketSecurityType.UNKNOWN,
            modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
            eligibility_reason=(
                MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER
            ),
            document_pipeline_version="v03_enhanced_v2",
            document_pipeline_commit="c" * 40,
        ),
    )


def label(year: int, code: str = "0001.HK") -> MarketOutcomeLabel:
    listing = date(year, 3, 1)
    return MarketOutcomeLabel(
        case_id=f"ipo_{year}_{code[:4]}",
        stock_code=code,
        cohort_year=year,
        dataset_split=expected_market_split(year),
        listing_date=listing,
        horizon=MarketLabelHorizon.FIVE_DAYS,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=listing + timedelta(days=7),
        target_close=Decimal("11"),
        raw_return=Decimal("0.1"),
        availability=MarketLabelAvailability.AVAILABLE,
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=provenance(f"label-{year}-{code}"),
    )


def market_snapshot(year: int, code: str = "0001.HK"):
    listing = date(year, 3, 1)
    bars = [
        MarketReferenceBar(
            reference_id="HSI",
            trading_date=date(year, 1, 1) + timedelta(days=index),
            close=Decimal(100 + index),
            provenance=provenance(f"hsi-{year}-{index}"),
        )
        for index in range(40)
    ]
    return PreListingMarketFeatureEngine().build(
        PreListingMarketFeatureContext(
            case_id=f"ipo_{year}_{code[:4]}",
            stock_code=code,
            cohort_year=year,
            listing_date=listing,
            dataset_split=expected_market_split(year),
            benchmark_reference_id="HSI",
            source="fixture",
            provenance=provenance(f"market-{year}-{code}"),
        ),
        benchmark_bars=bars,
        prior_ipos=(),
    )


def modeling_row(year: int, code: str = "0001.HK"):
    return V04ModelingDatasetBuilder().join(document_snapshot(year, code), label(year, code))


@pytest.mark.parametrize("year", [2020, 2021, 2022, 2023])
def test_development_years_are_accepted(year: int) -> None:
    pair = (modeling_row(year), market_snapshot(year))
    result = V04MarketAugmentedDatasetBuilder().build_development([pair])
    assert result.dataset_split is MarketDatasetSplit.DEVELOPMENT


def test_2024_validation_is_accepted_but_not_as_development() -> None:
    pair = (modeling_row(2024), market_snapshot(2024))
    builder = V04MarketAugmentedDatasetBuilder()
    with pytest.raises(ModelingDatasetJoinError, match="not development"):
        builder.build_development([pair])
    assert builder.build_validation([pair]).dataset_split is MarketDatasetSplit.VALIDATION


def test_2025_outcome_is_rejected_before_augmented_join() -> None:
    with pytest.raises(BlindDataLeakageError):
        V04ModelingDatasetBuilder().join(document_snapshot(2025), label(2025))


def test_feature_only_2025_combined_export_has_no_outcome_or_target_field() -> None:
    document_x = V04BlindFeatureExporter().export([document_snapshot(2025)]).records[0]
    dataset = V04MarketAugmentedBlindFeatureExporter().export(
        [(document_x, market_snapshot(2025))]
    )
    payload = dataset.model_dump(mode="json")
    row = payload["records"][0]
    assert dataset.dataset_split is MarketDatasetSplit.BLIND
    assert "outcome_label" not in row
    assert "target" not in row
    assert "label_horizon" not in row


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "wrong-case"),
        ("stock_code", "9999.HK"),
        ("cohort_year", 2022),
        ("listing_date", date(2023, 3, 2)),
        ("dataset_split", MarketDatasetSplit.VALIDATION),
    ],
)
def test_document_market_feature_identity_mismatches_fail(field: str, value) -> None:
    row = modeling_row(2023)
    changed = market_snapshot(2023).model_copy(update={field: value})
    with pytest.raises(ModelingDatasetJoinError, match=field):
        V04MarketAugmentedDatasetBuilder().join(row, changed)


def test_combined_order_is_document_then_market_and_has_120_features() -> None:
    result = V04MarketAugmentedDatasetBuilder().join(
        modeling_row(2023), market_snapshot(2023)
    )
    vector = result.feature_vector
    document_names = tuple(item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features)
    market_names = tuple(item.name for item in MARKET_FEATURE_MANIFEST_V1.features)
    assert len(document_names) == 100
    assert len(market_names) == 20
    assert len(vector.feature_names) == 120
    assert vector.feature_names == document_names + market_names
    assert result.document_manifest_hash == DOCUMENT_FEATURE_MANIFEST_V1.content_hash()
    assert result.market_manifest_hash == MARKET_FEATURE_MANIFEST_V1.content_hash()


def test_augmented_dataset_order_and_provenance_are_deterministic() -> None:
    pairs = [
        (modeling_row(2023, "0002.HK"), market_snapshot(2023, "0002.HK")),
        (modeling_row(2023, "0001.HK"), market_snapshot(2023, "0001.HK")),
    ]
    builder = V04MarketAugmentedDatasetBuilder()
    first = builder.build_development(pairs)
    second = builder.build_development(reversed(pairs))
    assert first == second
    assert [row.case_id for row in first.records] == sorted(
        row.case_id for row in first.records
    )
    assert first.records[0].document_pipeline_commit == "c" * 40
    assert first.records[0].market_observation_date < first.records[0].listing_date
