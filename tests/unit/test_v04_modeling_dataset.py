from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.exceptions import BlindDataLeakageError
from ipo_risk.market.exceptions import IneligibleMarketSecurityError
from ipo_risk.modeling.dataset import (
    V04BlindFeatureExporter,
    V04ModelingDatasetBuilder,
)
from ipo_risk.modeling.exceptions import ModelingDatasetJoinError
from ipo_risk.modeling.snapshot import DocumentRiskSnapshotBuilder
from ipo_risk.schemas import IPOAnalysisResult, RiskLevel, TaskStatus
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
from ipo_risk.schemas.modeling import DocumentRiskSnapshotBuildContext


def provenance(year: int) -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture",
        dataset_version="fixture-v1",
        source_record_id=f"row-{year}",
    )


def snapshot(year: int, code: str = "0001.HK"):
    split = expected_market_split(year)
    result = IPOAnalysisResult(
        analysis_id=f"analysis-{year}-{code}",
        request_id=f"request-{year}-{code}",
        company_name="Fixture IPO",
        stock_code=code,
        workflow_version="enhanced_v2",
        schema_version="1.0",
        status=TaskStatus.COMPLETED,
        metadata={
            "case_id": f"ipo_{year}_{code[:4]}",
            "dataset_split": split.value,
            "ipo_profile": {
                "stock_code": code,
                "listing_date": date(year, 1, 2).isoformat(),
            },
            "document": {"document_id": f"document-{year}-{code}"},
            "supervision": {"conflicts": []},
        },
    )
    context = DocumentRiskSnapshotBuildContext(
        case_id=f"ipo_{year}_{code[:4]}",
        document_id=f"document-{year}-{code}",
        stock_code=code,
        cohort_year=year,
        listing_date=date(year, 1, 2),
        dataset_split=split,
        official_ipo_universe_member=True,
        security_type=MarketSecurityType.UNKNOWN,
        modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
        eligibility_reason=MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER,
        document_pipeline_version="v03_enhanced_v2",
        document_pipeline_commit="c" * 40,
    )
    return DocumentRiskSnapshotBuilder().build(result, context)


def label(year: int, code: str = "0001.HK") -> MarketOutcomeLabel:
    listing_date = date(year, 1, 2)
    return MarketOutcomeLabel(
        case_id=f"ipo_{year}_{code[:4]}",
        stock_code=code,
        cohort_year=year,
        dataset_split=expected_market_split(year),
        listing_date=listing_date,
        horizon=MarketLabelHorizon.FIVE_DAYS,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=listing_date + timedelta(days=7),
        target_close=Decimal("11"),
        raw_return=Decimal("0.1"),
        availability=MarketLabelAvailability.AVAILABLE,
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=provenance(year),
    )


@pytest.mark.parametrize("year", [2020, 2021, 2022, 2023])
def test_2020_to_2023_are_accepted_for_development(year: int) -> None:
    dataset = V04ModelingDatasetBuilder().build_development(
        [(snapshot(year), label(year))]
    )
    assert dataset.dataset_split is MarketDatasetSplit.DEVELOPMENT
    assert dataset.records[0].cohort_year == year


def test_2024_is_validation_and_rejected_by_development_builder() -> None:
    pair = (snapshot(2024), label(2024))
    with pytest.raises(ModelingDatasetJoinError, match="not development"):
        V04ModelingDatasetBuilder().build_development([pair])
    validation = V04ModelingDatasetBuilder().build_validation([pair])
    assert validation.dataset_split is MarketDatasetSplit.VALIDATION


def test_2025_document_features_are_allowed_without_outcome() -> None:
    blind = V04BlindFeatureExporter().export([snapshot(2025)])
    payload = blind.model_dump(mode="json")
    assert blind.dataset_split is MarketDatasetSplit.BLIND
    assert blind.records[0].cohort_year == 2025
    assert "outcome_label" not in payload["records"][0]


def test_2025_outcome_cannot_form_or_enter_modeling_dataset() -> None:
    pair = (snapshot(2025), label(2025))
    builder = V04ModelingDatasetBuilder()
    with pytest.raises(BlindDataLeakageError):
        builder.join(*pair)
    with pytest.raises(BlindDataLeakageError):
        builder.build_development([pair])


def test_unknown_security_type_remains_eligible_for_official_case() -> None:
    official_unknown = snapshot(2023)
    record = V04ModelingDatasetBuilder().join(official_unknown, label(2023))
    assert record.security_type is MarketSecurityType.UNKNOWN
    assert record.official_ipo_universe_member is True


def test_nonofficial_case_cannot_enter_modeling_or_blind_feature_export() -> None:
    official = snapshot(2023)
    outside = official.model_copy(
        update={
            "official_ipo_universe_member": False,
            "security_type": MarketSecurityType.ORDINARY_EQUITY,
            "modeling_eligibility": MarketSecurityEligibility.INELIGIBLE,
            "eligibility_reason": (
                MarketSecurityEligibilityReason.NOT_OFFICIAL_IPO_UNIVERSE_MEMBER
            ),
        }
    )
    with pytest.raises(IneligibleMarketSecurityError):
        V04ModelingDatasetBuilder().join(outside, label(2023))

    blind = snapshot(2025).model_copy(
        update={
            "official_ipo_universe_member": False,
            "security_type": MarketSecurityType.ORDINARY_EQUITY,
            "modeling_eligibility": MarketSecurityEligibility.INELIGIBLE,
            "eligibility_reason": (
                MarketSecurityEligibilityReason.NOT_OFFICIAL_IPO_UNIVERSE_MEMBER
            ),
        }
    )
    with pytest.raises(IneligibleMarketSecurityError):
        V04BlindFeatureExporter().export([blind])


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_id", "different-case"),
        ("stock_code", "9999.HK"),
        ("cohort_year", 2022),
        ("listing_date", date(2023, 2, 1)),
        ("dataset_split", MarketDatasetSplit.VALIDATION),
    ],
)
def test_document_market_join_mismatches_are_rejected(field: str, value) -> None:
    changed_label = label(2023).model_copy(update={field: value})
    with pytest.raises(ModelingDatasetJoinError, match=field):
        V04ModelingDatasetBuilder().join(snapshot(2023), changed_label)


def test_label_and_all_version_provenance_are_preserved() -> None:
    record = V04ModelingDatasetBuilder().join(snapshot(2023), label(2023))
    assert record.document_pipeline_version == "v03_enhanced_v2"
    assert record.document_pipeline_commit == "c" * 40
    assert record.workflow_version == "enhanced_v2"
    assert record.schema_version == "1.0"
    assert record.feature_schema_version == "v04_document_features_v1"
    assert record.market_label_policy_version == "v04_market_label_policy_v1"
    assert record.market_split_policy_version == "v04_chronological_split_v1"
    assert record.dataset_version == "v04_modeling_dataset_v1"


def test_modeling_dataset_rows_and_serialization_are_deterministic() -> None:
    pairs = [
        (snapshot(2023, "0002.HK"), label(2023, "0002.HK")),
        (snapshot(2023, "0001.HK"), label(2023, "0001.HK")),
    ]
    builder = V04ModelingDatasetBuilder()
    first = builder.build_development(pairs)
    second = builder.build_development(reversed(pairs))
    assert [row.case_id for row in first.records] == sorted(
        row.case_id for row in first.records
    )
    assert first.canonical_json() == second.canonical_json()
